from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.api.v1.auth import get_current_user
from app.models import WebhookEndpoint, User
from app.schemas import WebhookCreate, WebhookResponse

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

# Available webhook events
WEBHOOK_EVENTS = [
    "call.started",
    "call.connected",
    "call.completed",
    "call.failed",
    "call.transferred",
    "campaign.started",
    "campaign.completed",
    "campaign.paused",
    "recording.ready",
    "transcription.ready",
]


@router.get("/events")
async def list_webhook_events():
    """List all available webhook events"""
    return WEBHOOK_EVENTS


@router.get("", response_model=List[WebhookResponse])
async def list_webhooks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all webhooks"""
    webhooks = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.owner_id == current_user.id
    ).all()
    return webhooks


@router.post("", response_model=WebhookResponse)
async def create_webhook(
    webhook_data: WebhookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new webhook endpoint"""
    import secrets
    
    # Validate events
    invalid_events = [e for e in webhook_data.events if e not in WEBHOOK_EVENTS]
    if invalid_events:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid events: {invalid_events}"
        )
    
    webhook = WebhookEndpoint(
        url=webhook_data.url,
        events=webhook_data.events,
        secret=secrets.token_urlsafe(32),
        owner_id=current_user.id
    )
    
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    
    return webhook


@router.get("/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    webhook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get webhook details"""
    webhook = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.id == webhook_id,
        WebhookEndpoint.owner_id == current_user.id
    ).first()
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return webhook


@router.put("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: int,
    webhook_data: WebhookCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a webhook"""
    webhook = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.id == webhook_id,
        WebhookEndpoint.owner_id == current_user.id
    ).first()
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    # Validate events
    invalid_events = [e for e in webhook_data.events if e not in WEBHOOK_EVENTS]
    if invalid_events:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid events: {invalid_events}"
        )
    
    webhook.url = webhook_data.url
    webhook.events = webhook_data.events
    
    db.commit()
    db.refresh(webhook)
    
    return webhook


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a webhook"""
    webhook = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.id == webhook_id,
        WebhookEndpoint.owner_id == current_user.id
    ).first()
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    db.delete(webhook)
    db.commit()
    
    return {"message": "Webhook deleted"}


@router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Send a test event to webhook"""
    import httpx
    import hmac
    import hashlib
    import json
    from datetime import datetime
    
    webhook = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.id == webhook_id,
        WebhookEndpoint.owner_id == current_user.id
    ).first()
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    # Create test payload
    payload = {
        "event": "test",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {
            "message": "This is a test webhook delivery"
        }
    }
    
    # Create signature
    payload_str = json.dumps(payload)
    secret_key = webhook.secret or ""
    signature = hmac.new(
        secret_key.encode(),
        payload_str.encode(),
        hashlib.sha256
    ).hexdigest()
    
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Signature": signature,
        "X-Webhook-Event": "test"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook.url,
                json=payload,
                headers=headers,
                timeout=10
            )
        
        return {
            "success": response.status_code < 400,
            "status_code": response.status_code,
            "response": response.text[:500]
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/{webhook_id}/toggle")
async def toggle_webhook(
    webhook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Enable/disable a webhook"""
    webhook = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.id == webhook_id,
        WebhookEndpoint.owner_id == current_user.id
    ).first()
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    webhook.is_active = not webhook.is_active
    db.commit()
    
    return {
        "message": f"Webhook {'enabled' if webhook.is_active else 'disabled'}",
        "is_active": webhook.is_active
    }


@router.get("/{webhook_id}/secret")
async def get_webhook_secret(
    webhook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get webhook signing secret"""
    webhook = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.id == webhook_id,
        WebhookEndpoint.owner_id == current_user.id
    ).first()
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    return {"secret": webhook.secret}


@router.post("/{webhook_id}/rotate-secret")
async def rotate_webhook_secret(
    webhook_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Rotate webhook signing secret"""
    import secrets
    
    webhook = db.query(WebhookEndpoint).filter(
        WebhookEndpoint.id == webhook_id,
        WebhookEndpoint.owner_id == current_user.id
    ).first()
    
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    
    webhook.secret = secrets.token_urlsafe(32)
    db.commit()
    
    return {
        "message": "Secret rotated",
        "secret": webhook.secret
    }
