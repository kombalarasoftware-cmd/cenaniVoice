"""Settings endpoints"""
from fastapi import APIRouter
router = APIRouter()

@router.get("")
async def get_settings():
    return {"message": "Get settings"}

@router.put("")
async def update_settings():
    return {"message": "Update settings"}

@router.get("/sip")
async def get_sip_config():
    return {"message": "Get SIP config"}

@router.put("/sip")
async def update_sip_config():
    return {"message": "Update SIP config"}
