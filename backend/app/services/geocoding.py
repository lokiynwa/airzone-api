import json

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.geocode_cache import LocationSearchCache
from app.schemas.location import GeocodeResult


def _normalize_query(query: str) -> str:
    return " ".join(query.strip().lower().split())


def _serialize_results(results: list[GeocodeResult]) -> str:
    return json.dumps([result.model_dump() for result in results])


def _deserialize_results(payload: str) -> list[GeocodeResult]:
    data = json.loads(payload)
    return [GeocodeResult.model_validate(item) for item in data]


async def _fetch_from_nominatim(settings: Settings, query: str) -> list[GeocodeResult]:
    async with httpx.AsyncClient(
        base_url=settings.nominatim_base_url,
        headers={"User-Agent": settings.nominatim_user_agent},
        timeout=settings.http_timeout_seconds,
    ) as client:
        response = await client.get(
            "/search",
            params={
                "q": query,
                "format": "jsonv2",
                "addressdetails": 0,
                "limit": 5,
            },
        )
        response.raise_for_status()

    payload = response.json()
    return [
        GeocodeResult(
            label=item["display_name"],
            lat=float(item["lat"]),
            lon=float(item["lon"]),
        )
        for item in payload
    ]


async def geocode_query(db: Session, *, settings: Settings, query: str) -> list[GeocodeResult]:
    normalized_query = _normalize_query(query)
    cache_query = select(LocationSearchCache).where(LocationSearchCache.query == normalized_query)
    cached = db.scalar(cache_query)
    if cached:
        return _deserialize_results(cached.results_json)

    results = await _fetch_from_nominatim(settings, normalized_query)
    cache_entry = LocationSearchCache(
        query=normalized_query,
        results_json=_serialize_results(results),
    )
    db.add(cache_entry)
    db.commit()
    return results
