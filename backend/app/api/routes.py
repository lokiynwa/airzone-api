from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.locations import router as locations_router
from app.api.system import router as system_router

router = APIRouter()
router.include_router(system_router)
router.include_router(auth_router)
router.include_router(locations_router)
