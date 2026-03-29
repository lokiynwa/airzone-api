from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.dependencies import AuthenticatedUser
from app.core.config import Settings, get_settings
from app.schemas.aircraft import AircraftSearchResponse
from app.services.aircraft_search import search_aircraft

router = APIRouter(prefix="/aircraft", tags=["aircraft"])
AppSettings = Annotated[Settings, Depends(get_settings)]


@router.get("/search", response_model=AircraftSearchResponse)
async def search_aircraft_in_radius(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lon: Annotated[float, Query(ge=-180, le=180)],
    radius_km: Annotated[float, Query(gt=0, le=250)],
    settings: AppSettings,
    _: AuthenticatedUser,
    label: Annotated[str | None, Query(max_length=255)] = None,
) -> AircraftSearchResponse:
    return await search_aircraft(
        settings=settings,
        lat=lat,
        lon=lon,
        radius_km=radius_km,
        label=label,
    )
