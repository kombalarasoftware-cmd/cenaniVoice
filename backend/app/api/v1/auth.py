from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from typing import Optional
import logging
import redis

from app.core.database import get_db
from app.core.config import settings
from app.models import User
from app.schemas import UserCreate, UserResponse, Token, LoginRequest
from app.services.email_service import send_approval_email, verify_approval_token

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Redis client for token blacklist and account lockout
try:
    _redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    _redis_client.ping()
except Exception:
    _redis_client = None
    logger.warning("Redis not available for token blacklist / account lockout")

# Account lockout settings
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_TTL_SECONDS = 900  # 15 minutes


def _is_token_blacklisted(jti: str) -> bool:
    """Check if a token JTI is in the blacklist."""
    if not _redis_client:
        return False
    try:
        return _redis_client.sismember("token_blacklist", jti)
    except Exception:
        return False


def _blacklist_token(jti: str, ttl: int) -> None:
    """Add a token JTI to the blacklist."""
    if not _redis_client:
        return
    try:
        _redis_client.sadd("token_blacklist", jti)
        # Also set an expiring key so we can auto-clean
        _redis_client.setex(f"token_bl:{jti}", ttl, "1")
    except Exception as e:
        logger.warning(f"Failed to blacklist token: {e}")


def _check_account_lockout(email: str) -> None:
    """Raise 429 if account is locked out due to too many failed attempts."""
    if not _redis_client:
        return
    key = f"login_failures:{email}"
    try:
        attempts = _redis_client.get(key)
        if attempts and int(attempts) >= MAX_FAILED_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Account temporarily locked due to too many failed login attempts. Try again later.",
            )
    except HTTPException:
        raise
    except Exception:
        pass


def _record_failed_login(email: str) -> None:
    """Increment failed login counter with TTL."""
    if not _redis_client:
        return
    key = f"login_failures:{email}"
    try:
        pipe = _redis_client.pipeline()
        pipe.incr(key)
        pipe.expire(key, LOCKOUT_TTL_SECONDS)
        pipe.execute()
    except Exception:
        pass


def _clear_failed_logins(email: str) -> None:
    """Clear failed login counter on successful login."""
    if not _redis_client:
        return
    try:
        _redis_client.delete(f"login_failures:{email}")
    except Exception:
        pass


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    import uuid
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "jti": str(uuid.uuid4())})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        # Check token blacklist
        jti = payload.get("jti")
        if jti and _is_token_blacklisted(jti):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except HTTPException:
        raise
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    db: Session = Depends(get_db),
    token: dict = Depends(verify_token)
) -> User:
    """Get current authenticated user"""
    user_id = token.get("sub")
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    return user


# Optional auth - used for endpoints that work with or without authentication
security_optional = HTTPBearer(auto_error=False)


async def get_current_user_optional(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_optional)
) -> Optional[User]:
    """Get current user if authenticated, otherwise return None (truly optional)."""
    if not credentials:
        return None
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        # Check token blacklist
        jti = payload.get("jti")
        if jti and _is_token_blacklisted(jti):
            return None
        user_id = payload.get("sub")
        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
            if user and user.is_active:
                return user
    except Exception:
        pass
    return None


@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Register a new user (requires admin approval before login)"""
    # Check if email exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user with is_approved=False
    user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password),
        is_approved=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Send approval email to admin in background
    background_tasks.add_task(
        send_approval_email,
        user_id=user.id,
        user_email=user.email,
        user_name=user.full_name,
    )
    
    return user


@router.post("/login", response_model=Token)
async def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user and return JWT token"""
    # Check account lockout before attempting authentication
    _check_account_lockout(credentials.email)

    user = db.query(User).filter(User.email == credentials.email).first()

    if not user or not verify_password(credentials.password, user.hashed_password):
        _record_failed_login(credentials.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    if not user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has not been approved by an administrator yet. Please wait for approval.",
        )

    # Clear failed login counter on success
    _clear_failed_logins(credentials.email)
    access_token = create_access_token(data={"sub": str(user.id)})

    return Token(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info"""
    return current_user


@router.post("/refresh", response_model=Token)
async def refresh_token(current_user: User = Depends(get_current_user)):
    """Refresh access token"""
    access_token = create_access_token(data={"sub": str(current_user.id)})
    return Token(access_token=access_token)


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    token: dict = Depends(verify_token),
):
    """Logout and blacklist the current token"""
    jti = token.get("jti")
    exp = token.get("exp")
    if jti and exp:
        # Blacklist until the token would have expired
        ttl = max(int(exp - datetime.now(timezone.utc).timestamp()), 0)
        _blacklist_token(jti, ttl)
    return {"message": "Successfully logged out"}


@router.get("/approve", response_class=HTMLResponse)
async def approve_user(token: str, db: Session = Depends(get_db)):
    """
    Admin clicks this link from email to approve a new user registration.
    Returns an HTML page with the result.
    """
    user_id = verify_approval_token(token)

    if user_id is None:
        return HTMLResponse(content=_approval_result_page(
            success=False,
            title="Approval Failed",
            message="Invalid or expired approval link.",
        ), status_code=400)

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        return HTMLResponse(content=_approval_result_page(
            success=False,
            title="User Not Found",
            message="No user found for this approval link.",
        ), status_code=404)

    if user.is_approved:
        return HTMLResponse(content=_approval_result_page(
            success=True,
            title="Already Approved",
            message=f"{user.email} has already been approved.",
        ))

    user.is_approved = True
    db.commit()

    logger.info(f"User {user.email} (id={user.id}) approved by admin via email link")

    return HTMLResponse(content=_approval_result_page(
        success=True,
        title="User Approved ✅",
        message=f"{user.email} can now sign in.",
    ))


def _approval_result_page(success: bool, title: str, message: str) -> str:
    """Generate a simple HTML page to show approval result."""
    color = "#22c55e" if success else "#ef4444"
    icon = "✅" if success else "❌"
    return f"""
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - VoiceAI</title>
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f4f4f5;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .card {{
            background: #fff;
            border-radius: 16px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.08);
            padding: 48px;
            max-width: 440px;
            text-align: center;
        }}
        .icon {{ font-size: 48px; margin-bottom: 16px; }}
        h1 {{ color: {color}; font-size: 24px; margin-bottom: 12px; }}
        p {{ color: #6b7280; font-size: 16px; line-height: 1.6; }}
        .footer {{ margin-top: 32px; color: #9ca3af; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">{icon}</div>
        <h1>{title}</h1>
        <p>{message}</p>
        <p class="footer">VoiceAI Platform</p>
    </div>
</body>
</html>
"""
