import re
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from app.core.config import Settings
from app.services.cache import TTLMemoryCache
from app.services.geo import BoundingBox

_CALLSIGN_PATTERN = re.compile(r"^(?P<prefix>[A-Z]{3})(?P<number>\d{1,4}[A-Z]?)$")
_DISALLOWED_CATEGORIES = {0, 1, 11, 13, 14, 15, 16, 17, 18, 19, 20}


@dataclass(frozen=True)
class OpenSkyAircraftState:
    icao24: str
    callsign: str
    latitude: float
    longitude: float
    altitude_m: float | None
    heading_deg: float | None
    speed_kph: float | None
    last_seen_at: datetime | None
    on_ground: bool
    category: int | None
    flight_number: str | None
    flight_icao: str | None


class OpenSkyClientError(Exception):
    pass


class OpenSkyClient:
    _token_cache = TTLMemoryCache[str](ttl_seconds=300)

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def _get_access_token(self) -> str | None:
        client_id = self.settings.opensky_client_id
        client_secret = self.settings.opensky_client_secret
        if not client_id or not client_secret:
            return None

        cache_key = f"{client_id}:token"
        cached_token = type(self)._token_cache.get(cache_key)
        if cached_token:
            return cached_token

        async with httpx.AsyncClient(timeout=self.settings.http_timeout_seconds) as client:
            response = await client.post(
                self.settings.opensky_auth_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
            )
            response.raise_for_status()

        payload = response.json()
        token = payload["access_token"]
        expires_in = max(60, int(payload.get("expires_in", 300)) - 30)
        type(self)._token_cache = TTLMemoryCache[str](ttl_seconds=expires_in)
        type(self)._token_cache.set(cache_key, token)
        return token

    async def fetch_states(self, bbox: BoundingBox) -> list[OpenSkyAircraftState]:
        headers = {}
        token = await self._get_access_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            async with httpx.AsyncClient(
                base_url=self.settings.opensky_base_url,
                headers=headers,
                timeout=self.settings.http_timeout_seconds,
            ) as client:
                response = await client.get(
                    "/api/states/all",
                    params={
                        "lamin": bbox.lamin,
                        "lomin": bbox.lomin,
                        "lamax": bbox.lamax,
                        "lomax": bbox.lomax,
                        "extended": 1,
                    },
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise OpenSkyClientError("OpenSky request failed.") from exc

        payload = response.json()
        states = payload.get("states") or []
        normalized_states: list[OpenSkyAircraftState] = []
        for state in states:
            parsed_state = self._parse_state(state)
            if parsed_state:
                normalized_states.append(parsed_state)

        return normalized_states

    def _parse_state(self, raw_state: list[object]) -> OpenSkyAircraftState | None:
        if len(raw_state) <= 17:
            return None

        callsign = str(raw_state[1] or "").strip().upper()
        latitude = raw_state[6]
        longitude = raw_state[5]
        on_ground = bool(raw_state[8])
        category = raw_state[17]

        if not callsign or latitude is None or longitude is None or on_ground:
            return None
        if category in _DISALLOWED_CATEGORIES:
            return None

        flight_match = _CALLSIGN_PATTERN.match(callsign)
        flight_number = flight_match.group("number") if flight_match else None
        flight_icao = callsign if flight_match else None
        altitude_m = raw_state[13] if raw_state[13] is not None else raw_state[7]
        velocity = raw_state[9]
        last_contact = raw_state[4]

        return OpenSkyAircraftState(
            icao24=str(raw_state[0]),
            callsign=callsign,
            latitude=float(latitude),
            longitude=float(longitude),
            altitude_m=float(altitude_m) if altitude_m is not None else None,
            heading_deg=float(raw_state[10]) if raw_state[10] is not None else None,
            speed_kph=round(float(velocity) * 3.6, 2) if velocity is not None else None,
            last_seen_at=(
                datetime.fromtimestamp(int(last_contact), UTC) if last_contact is not None else None
            ),
            on_ground=on_ground,
            category=int(category) if category is not None else None,
            flight_number=flight_number,
            flight_icao=flight_icao,
        )
