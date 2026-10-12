"""Centralized API router registering sub-routers for BankSim."""

from fastapi import APIRouter

from api.admin import admin_router
from api.auth import auth_router
from api.banking import banking_router
from api.security import security_router
from api.users import users_router

# Root API router for versioned endpoints
api_router = APIRouter(prefix="/api/v1")

# Attach sub-routers
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(admin_router)
api_router.include_router(security_router)
api_router.include_router(banking_router)

