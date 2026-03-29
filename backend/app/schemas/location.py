from pydantic import BaseModel, ConfigDict


class GeocodeResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    label: str
    lat: float
    lon: float


class GeocodeResponse(BaseModel):
    query: str
    results: list[GeocodeResult]

