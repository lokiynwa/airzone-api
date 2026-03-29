from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.dependencies import AuthenticatedUser
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.schemas.location import GeocodeResponse
from app.services.geocoding import geocode_query

router = APIRouter(prefix="/locations", tags=["locations"])
DBSession = Annotated[Session, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


@router.get("/geocode", response_model=GeocodeResponse)
async def geocode_location(
    q: Annotated[str, Query(min_length=2, max_length=255)],
    db: DBSession,
    settings: AppSettings,
    _: AuthenticatedUser,
) -> GeocodeResponse:
    trimmed_query = q.strip()
    if len(trimmed_query) < 2:
        raise HTTPException(status_code=422, detail="Query must be at least 2 characters long.")

    results = await geocode_query(db, settings=settings, query=trimmed_query)
    return GeocodeResponse(query=trimmed_query, results=results)
