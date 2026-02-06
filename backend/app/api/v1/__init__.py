from fastapi import APIRouter

from app.api.v1 import (
    auth,
    agents,
    campaigns,
    numbers,
    calls,
    recordings,
    settings,
    reports,
    webhooks,
)

api_router = APIRouter()

# Include all routers
api_router.include_router(auth.router)
api_router.include_router(agents.router)
api_router.include_router(campaigns.router)
api_router.include_router(numbers.router)
api_router.include_router(calls.router)
api_router.include_router(recordings.router)
api_router.include_router(settings.router)
api_router.include_router(reports.router)
api_router.include_router(webhooks.router)
