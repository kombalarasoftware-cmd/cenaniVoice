"""Reports endpoints"""
from fastapi import APIRouter
router = APIRouter()

@router.get("/dashboard")
async def get_dashboard_stats():
    return {"message": "Dashboard stats"}

@router.get("/campaigns/{campaign_id}")
async def get_campaign_report(campaign_id: str):
    return {"message": f"Campaign report {campaign_id}"}

@router.get("/agents/{agent_id}")
async def get_agent_performance(agent_id: str):
    return {"message": f"Agent performance {agent_id}"}

@router.get("/export")
async def export_report():
    return {"message": "Export report"}
