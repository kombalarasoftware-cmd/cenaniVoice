"""
Email service for sending admin approval notifications.
Uses Python's built-in smtplib - no external dependencies needed.
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone
from jose import jwt

from app.core.config import settings

logger = logging.getLogger(__name__)

# Token expiry for approval links
APPROVAL_TOKEN_EXPIRE_DAYS = 7


def create_approval_token(user_id: int) -> str:
    """Create a JWT token for user approval link."""
    expire = datetime.now(timezone.utc) + timedelta(days=APPROVAL_TOKEN_EXPIRE_DAYS)
    payload = {
        "action": "approve_user",
        "user_id": user_id,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_approval_token(token: str) -> int | None:
    """Verify approval token and return user_id, or None if invalid."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("action") != "approve_user":
            return None
        return payload.get("user_id")
    except Exception as e:
        logger.warning(f"Invalid approval token: {e}")
        return None


def _build_approval_email(user_email: str, user_name: str, approve_url: str) -> MIMEMultipart:
    """Build the HTML approval email."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🔔 New User Pending Approval - {user_email}"
    msg["From"] = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
    msg["To"] = settings.ADMIN_APPROVAL_EMAIL

    text_body = f"""
New User Registration Approval

The following user has registered on the VoiceAI platform and is awaiting your approval:

Name: {user_name or 'Not specified'}
Email: {user_email}
Registration Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}

Click the link below to approve:
{approve_url}

This link is valid for {APPROVAL_TOKEN_EXPIRE_DAYS} days.

---
VoiceAI Platform - Automated Notification
"""

    html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background-color:#f4f4f5;">
    <div style="max-width:600px;margin:40px auto;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 6px rgba(0,0,0,0.07);">
        <!-- Header -->
        <div style="background:linear-gradient(135deg,#6366f1,#8b5cf6);padding:32px;text-align:center;">
            <h1 style="color:#ffffff;margin:0;font-size:24px;">🔔 New User Approval</h1>
            <p style="color:rgba(255,255,255,0.85);margin:8px 0 0;font-size:14px;">VoiceAI Platform</p>
        </div>

        <!-- Content -->
        <div style="padding:32px;">
            <p style="color:#374151;font-size:16px;margin:0 0 24px;">
                The following user has registered on the platform and is awaiting your approval:
            </p>

            <!-- User Info Card -->
            <div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:12px;padding:20px;margin:0 0 24px;">
                <table style="width:100%;border-collapse:collapse;">
                    <tr>
                        <td style="padding:8px 0;color:#6b7280;font-size:14px;width:100px;">Name:</td>
                        <td style="padding:8px 0;color:#111827;font-size:14px;font-weight:600;">{user_name or 'Not specified'}</td>
                    </tr>
                    <tr>
                        <td style="padding:8px 0;color:#6b7280;font-size:14px;">Email:</td>
                        <td style="padding:8px 0;color:#111827;font-size:14px;font-weight:600;">{user_email}</td>
                    </tr>
                    <tr>
                        <td style="padding:8px 0;color:#6b7280;font-size:14px;">Date:</td>
                        <td style="padding:8px 0;color:#111827;font-size:14px;">{datetime.now().strftime('%Y-%m-%d %H:%M')}</td>
                    </tr>
                </table>
            </div>

            <!-- Approve Button -->
            <div style="text-align:center;margin:32px 0;">
                <a href="{approve_url}"
                   style="display:inline-block;background:linear-gradient(135deg,#22c55e,#16a34a);color:#ffffff;text-decoration:none;padding:14px 48px;border-radius:12px;font-size:16px;font-weight:600;box-shadow:0 4px 12px rgba(34,197,94,0.4);">
                    ✅ Approve User
                </a>
            </div>

            <p style="color:#9ca3af;font-size:12px;text-align:center;margin:24px 0 0;">
                This link is valid for {APPROVAL_TOKEN_EXPIRE_DAYS} days. Unapproved users cannot sign in.
            </p>
        </div>

        <!-- Footer -->
        <div style="background:#f9fafb;padding:16px 32px;text-align:center;border-top:1px solid #e5e7eb;">
            <p style="color:#9ca3af;font-size:12px;margin:0;">
                VoiceAI Platform &mdash; Automated Notification
            </p>
        </div>
    </div>
</body>
</html>
"""

    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    return msg


def send_approval_email(user_id: int, user_email: str, user_name: str | None = None) -> bool:
    """
    Send approval email to admin for a newly registered user.
    Returns True if email sent successfully, False otherwise.
    """
    if not settings.ADMIN_APPROVAL_EMAIL:
        logger.error("ADMIN_APPROVAL_EMAIL is not configured. Cannot send approval email.")
        return False

    if not settings.SMTP_HOST:
        logger.error("SMTP_HOST is not configured. Cannot send approval email.")
        return False

    # Generate approval token and URL
    token = create_approval_token(user_id)
    approve_url = f"{settings.APP_BASE_URL}/api/v1/auth/approve?token={token}"

    try:
        msg = _build_approval_email(user_email, user_name or "", approve_url)

        if settings.SMTP_USE_TLS:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30)
            server.ehlo()
            server.starttls()
            server.ehlo()
        else:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=30)

        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

        server.sendmail(
            settings.SMTP_FROM_EMAIL or settings.SMTP_USER,
            settings.ADMIN_APPROVAL_EMAIL,
            msg.as_string(),
        )
        server.quit()

        logger.info(f"Approval email sent to {settings.ADMIN_APPROVAL_EMAIL} for user {user_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send approval email for {user_email}: {e}")
        return False
