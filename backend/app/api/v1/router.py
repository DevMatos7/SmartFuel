from fastapi import APIRouter

from app.api.v1 import audit_logs, auth, health, organizations, stations, users

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router)
api_router.include_router(organizations.router)
api_router.include_router(stations.router)
api_router.include_router(users.router)
api_router.include_router(audit_logs.router)
