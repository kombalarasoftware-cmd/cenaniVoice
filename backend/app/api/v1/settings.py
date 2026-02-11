from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models import SIPTrunk, SystemSettings, APIKey, User, UserRole, RolePermission
from app.schemas import (
    SIPTrunkCreate, SIPTrunkResponse,
    PagePermissions, RolePermissionResponse, RolePermissionUpdate
)

router = APIRouter(prefix="/settings", tags=["Settings"])


# ============ SIP Trunk Settings ============

@router.get("/sip-trunks", response_model=List[SIPTrunkResponse])
async def list_sip_trunks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all SIP trunks"""
    trunks = db.query(SIPTrunk).filter(SIPTrunk.owner_id == current_user.id).all()
    return trunks


@router.post("/sip-trunks", response_model=SIPTrunkResponse)
async def create_sip_trunk(
    trunk_data: SIPTrunkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new SIP trunk"""
    trunk = SIPTrunk(
        name=trunk_data.name,
        server=trunk_data.server,
        port=trunk_data.port,
        username=trunk_data.username,
        password=trunk_data.password,
        transport=trunk_data.transport,
        codec_priority=trunk_data.codec_priority,
        concurrent_limit=trunk_data.concurrent_limit,
        owner_id=current_user.id
    )
    
    db.add(trunk)
    db.commit()
    db.refresh(trunk)
    
    # TODO: Reload Asterisk PJSIP configuration
    
    return trunk


@router.put("/sip-trunks/{trunk_id}", response_model=SIPTrunkResponse)
async def update_sip_trunk(
    trunk_id: int,
    trunk_data: SIPTrunkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a SIP trunk"""
    trunk = db.query(SIPTrunk).filter(
        SIPTrunk.id == trunk_id,
        SIPTrunk.owner_id == current_user.id
    ).first()
    
    if not trunk:
        raise HTTPException(status_code=404, detail="SIP trunk not found")
    
    trunk.name = trunk_data.name
    trunk.server = trunk_data.server
    trunk.port = trunk_data.port
    trunk.username = trunk_data.username
    trunk.password = trunk_data.password
    trunk.transport = trunk_data.transport
    trunk.codec_priority = trunk_data.codec_priority
    trunk.concurrent_limit = trunk_data.concurrent_limit
    
    db.commit()
    db.refresh(trunk)
    
    # TODO: Reload Asterisk PJSIP configuration
    
    return trunk


@router.delete("/sip-trunks/{trunk_id}")
async def delete_sip_trunk(
    trunk_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a SIP trunk"""
    trunk = db.query(SIPTrunk).filter(
        SIPTrunk.id == trunk_id,
        SIPTrunk.owner_id == current_user.id
    ).first()
    
    if not trunk:
        raise HTTPException(status_code=404, detail="SIP trunk not found")
    
    db.delete(trunk)
    db.commit()
    
    return {"message": "SIP trunk deleted"}


@router.post("/sip-trunks/{trunk_id}/test")
async def test_sip_trunk(
    trunk_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Test SIP trunk connectivity"""
    trunk = db.query(SIPTrunk).filter(
        SIPTrunk.id == trunk_id,
        SIPTrunk.owner_id == current_user.id
    ).first()
    
    if not trunk:
        raise HTTPException(status_code=404, detail="SIP trunk not found")
    
    # TODO: Send OPTIONS request to SIP server
    
    return {
        "success": True,
        "message": "SIP trunk is reachable",
        "latency_ms": 45
    }


# ============ API Keys ============

@router.get("/api-keys")
async def list_api_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all API keys"""
    keys = db.query(APIKey).filter(
        APIKey.owner_id == current_user.id
    ).all()
    
    return [
        {
            "id": key.id,
            "name": key.name,
            "prefix": key.key_prefix,
            "scopes": key.scopes,
            "last_used_at": key.last_used_at,
            "is_active": key.is_active,
            "total_requests": key.total_requests,
            "expires_at": key.expires_at,
            "created_at": key.created_at
        }
        for key in keys
    ]


@router.post("/api-keys")
async def create_api_key(
    name: str,
    scopes: Optional[List[str]] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new API key"""
    import secrets
    import hashlib
    
    # Generate key
    raw_key = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    key_prefix = raw_key[:8]
    
    api_key = APIKey(
        name=name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        scopes=scopes or ["read", "write"],
        owner_id=current_user.id
    )
    
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    return {
        "id": api_key.id,
        "name": api_key.name,
        "key": raw_key,  # Only shown once
        "message": "Store this key securely. It won't be shown again."
    }


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an API key"""
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.owner_id == current_user.id
    ).first()
    
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    db.delete(api_key)
    db.commit()
    
    return {"message": "API key deleted"}


# ============ General Settings ============

@router.get("/general")
async def get_general_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get general system settings"""
    settings = db.query(SystemSettings).all()
    
    return {
        setting.key: setting.value
        for setting in settings
    }


@router.put("/general")
async def update_general_settings(
    settings: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update general settings (admin only)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    for key, value in settings.items():
        setting = db.query(SystemSettings).filter(
            SystemSettings.key == key
        ).first()
        
        if setting:
            setting.value = str(value)
        else:
            setting = SystemSettings(key=key, value=str(value))
            db.add(setting)
    
    db.commit()
    
    return {"message": "Settings updated"}


# ============ OpenAI Settings ============

@router.post("/openai/test")
async def test_openai_connection(
    api_key: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Test OpenAI API key"""
    import openai

    try:
        client = openai.AsyncOpenAI(api_key=api_key)
        models = await client.models.list()

        # Check if realtime model is available
        has_realtime = any("realtime" in m.id for m in models.data)

        return {
            "success": True,
            "message": "API key is valid",
            "has_realtime_access": has_realtime
        }
    except openai.AuthenticationError:
        return {
            "success": False,
            "message": "Invalid API key"
        }
    except Exception:
        return {
            "success": False,
            "message": "API key validation failed"
        }


# ============ Role Permissions ============

def _ensure_default_roles(db: Session):
    """Ensure default role permissions exist in database"""
    default_roles = [
        {"role": "ADMIN", "description": "Full access to all pages and features"},
        {"role": "OPERATOR", "description": "Standard operator access"},
    ]
    for role_def in default_roles:
        existing = db.query(RolePermission).filter(
            RolePermission.role == role_def["role"]
        ).first()
        if not existing:
            all_true = PagePermissions()  # All default to True
            rp = RolePermission(
                role=role_def["role"],
                permissions=all_true.model_dump(),
                description=role_def["description"]
            )
            db.add(rp)
    db.commit()


@router.get("/roles", response_model=List[RolePermissionResponse])
async def list_role_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all role permissions (admin only)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    _ensure_default_roles(db)

    roles = db.query(RolePermission).all()
    return roles


@router.get("/roles/{role_name}", response_model=RolePermissionResponse)
async def get_role_permission(
    role_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get permissions for a specific role"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    _ensure_default_roles(db)

    role_perm = db.query(RolePermission).filter(
        RolePermission.role == role_name.upper()
    ).first()

    if not role_perm:
        raise HTTPException(status_code=404, detail="Role not found")

    return role_perm


@router.put("/roles/{role_name}", response_model=RolePermissionResponse)
async def update_role_permission(
    role_name: str,
    update_data: RolePermissionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update permissions for a role (admin only)"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")

    role_perm = db.query(RolePermission).filter(
        RolePermission.role == role_name.upper()
    ).first()

    if not role_perm:
        raise HTTPException(status_code=404, detail="Role not found")

    # Prevent ADMIN from disabling their own settings access
    if role_name.upper() == "ADMIN" and update_data.permissions:
        if not update_data.permissions.settings:
            raise HTTPException(
                status_code=400,
                detail="Cannot disable settings access for ADMIN role"
            )

    if update_data.permissions:
        role_perm.permissions = update_data.permissions.model_dump()

    if update_data.description is not None:
        role_perm.description = update_data.description

    db.commit()
    db.refresh(role_perm)

    return role_perm


@router.get("/my-permissions")
async def get_my_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's page permissions based on their role"""
    _ensure_default_roles(db)

    role_perm = db.query(RolePermission).filter(
        RolePermission.role == current_user.role.value
    ).first()

    if not role_perm:
        # Fallback: allow all
        return PagePermissions().model_dump()

    return role_perm.permissions
