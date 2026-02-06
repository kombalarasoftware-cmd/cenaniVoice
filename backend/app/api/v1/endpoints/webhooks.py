"""Webhooks endpoints"""
from fastapi import APIRouter
router = APIRouter()

@router.get("")
async def list_webhooks():
    return {"message": "List webhooks"}

@router.post("")
async def create_webhook():
    return {"message": "Create webhook"}

@router.put("/{webhook_id}")
async def update_webhook(webhook_id: str):
    return {"message": f"Update webhook {webhook_id}"}

@router.delete("/{webhook_id}")
async def delete_webhook(webhook_id: str):
    return {"message": f"Delete webhook {webhook_id}"}

@router.post("/{webhook_id}/test")
async def test_webhook(webhook_id: str):
    return {"message": f"Test webhook {webhook_id}"}
