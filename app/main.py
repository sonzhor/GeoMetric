"""
Geo Intelligence API v2.1
-------------------------
Coordinates / city → geo indicators → ML development score.
Web UI with map + compare mode.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Union, List

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import uvicorn

from app.geo_utils import (
    geocode_city,
    generate_indicators,
    classify_development,
)
from app.predictor import predict_development

STATIC_DIR = Path(__file__).parent / "static"

def _load_config() -> dict:
    import json
    cfg_path = Path(__file__).parent.parent / "config.json"
    if cfg_path.exists():
        with open(cfg_path, encoding="utf-8") as f:
            return json.load(f)
    return {"version": "2.1.0", "app_name": "Geo Intelligence API"}


CONFIG = _load_config()
APP_VERSION = str(CONFIG.get("version", "2.1.0"))


app = FastAPI(
    title="Geo Intelligence API",
    description=(
        "Анализирует географические показатели по координатам или названию города "
        "и прогнозирует условный показатель развития района с помощью ML-модели."
    ),
    version=APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ---------- Schemas ----------

class CoordinateRequest(BaseModel):
    lat: float = Field(..., ge=-90, le=90, description="Широта")
    lon: float = Field(..., ge=-180, le=180, description="Долгота")
    radius_km: Optional[float] = Field(5.0, ge=0.5, le=50)


class CityRequest(BaseModel):
    city: str = Field(..., min_length=1, max_length=100)
    radius_km: Optional[float] = Field(5.0, ge=0.5, le=50)


class CompareRequest(BaseModel):
    locations: List[str] = Field(
        ...,
        min_length=2,
        max_length=5,
        description="Список городов или 'lat,lon' строк",
    )
    radius_km: Optional[float] = Field(5.0, ge=0.5, le=50)


class Indicators(BaseModel):
    population_density: float
    green_space_ratio: float
    infrastructure_index: float
    transport_access: float
    economic_activity: float


class PredictionResult(BaseModel):
    development_score: float
    development_level: str
    top_contributing_factors: list


class GeoAnalysisResponse(BaseModel):
    input_type: str
    query: Union[str, dict]
    coordinates: dict
    radius_km: float
    indicators: Indicators
    prediction: PredictionResult
    meta: dict


# ---------- Helpers ----------

def _parse_location(item: str):
    """'Москва' or '55.75,37.62' → (input_type, query, lat, lon)."""
    item = item.strip()
    if "," in item:
        parts = [p.strip() for p in item.split(",")]
        if len(parts) == 2:
            try:
                lat, lon = float(parts[0]), float(parts[1])
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    return "coordinates", {"lat": lat, "lon": lon}, lat, lon
            except ValueError:
                pass
    coords = geocode_city(item)
    if coords is None:
        raise HTTPException(status_code=404, detail=f"Не найдено: '{item}'")
    return "city", item, coords[0], coords[1]


def _build_response(input_type, query, lat, lon, radius_km) -> GeoAnalysisResponse:
    indicators = generate_indicators(lat, lon)
    pred = predict_development(indicators)
    level = classify_development(pred["development_score"])

    return GeoAnalysisResponse(
        input_type=input_type,
        query=query,
        coordinates={"lat": round(lat, 6), "lon": round(lon, 6)},
        radius_km=radius_km,
        indicators=Indicators(**indicators),
        prediction=PredictionResult(
            development_score=pred["development_score"],
            development_level=level,
            top_contributing_factors=pred["top_contributing_factors"],
        ),
        meta={
            "model": "GradientBoostingRegressor (v2)",
            "model_r2": 0.91,
            "features_used": list(indicators.keys()),
            "note": (
                "Индикаторы детерминированы + учитывают близость к крупным метро. "
                "В проде — заменить на OSM / census / remote sensing."
            ),
        },
    )


# ---------- Endpoints ----------

@app.get("/", include_in_schema=False)
def ui():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api", tags=["Info"])
def api_info():
    return {
        "service": "Geo Intelligence API",
        "version": "2.1.0",
        "docs": "/docs",
        "ui": "/",
        "endpoints": {
            "analyze_coords": "POST /analyze/coords",
            "analyze_city": "POST /analyze/city",
            "analyze_get": "GET /analyze",
            "compare": "POST /analyze/compare",
            "health": "GET /health",
        },
    }


@app.get("/health", tags=["Info"])
def health():
    return {"status": "ok", "model_version": APP_VERSION, "app": CONFIG.get("app_name", "Geo Intelligence API")}


@app.get("/cities", tags=["Info"])
def list_cities():
    """Список городов из справочника (data/cities.json)."""
    path = Path(__file__).parent.parent / "data" / "cities.json"
    if not path.exists():
        from app.geo_utils import CITY_COORDS
        return [{"name": k, "lat": v[0], "lon": v[1]} for k, v in list(CITY_COORDS.items())[:50]]
    import json
    with open(path, encoding="utf-8") as f:
        return json.load(f)




@app.post("/analyze/coords", response_model=GeoAnalysisResponse, tags=["Analysis"])
def analyze_by_coords(body: CoordinateRequest):
    return _build_response(
        "coordinates",
        {"lat": body.lat, "lon": body.lon},
        body.lat,
        body.lon,
        body.radius_km or 5.0,
    )


@app.post("/analyze/city", response_model=GeoAnalysisResponse, tags=["Analysis"])
def analyze_by_city(body: CityRequest):
    coords = geocode_city(body.city)
    if coords is None:
        raise HTTPException(status_code=404, detail=f"Не удалось найти: '{body.city}'")
    return _build_response("city", body.city, coords[0], coords[1], body.radius_km or 5.0)


@app.get("/analyze", response_model=GeoAnalysisResponse, tags=["Analysis"])
def analyze_get(
    lat: Optional[float] = Query(None, ge=-90, le=90),
    lon: Optional[float] = Query(None, ge=-180, le=180),
    city: Optional[str] = Query(None, min_length=1, max_length=100),
    radius_km: float = Query(5.0, ge=0.5, le=50),
):
    if city:
        coords = geocode_city(city)
        if coords is None:
            raise HTTPException(status_code=404, detail=f"Не удалось найти: '{city}'")
        return _build_response("city", city, coords[0], coords[1], radius_km)
    if lat is not None and lon is not None:
        return _build_response("coordinates", {"lat": lat, "lon": lon}, lat, lon, radius_km)
    raise HTTPException(status_code=400, detail="Укажите lat+lon или city")


@app.post("/analyze/compare", tags=["Analysis"])
def analyze_compare(body: CompareRequest):
    """Сравнение 2–5 локаций (город или 'lat,lon')."""
    results = []
    for item in body.locations:
        input_type, query, lat, lon = _parse_location(item)
        results.append(
            _build_response(input_type, query, lat, lon, body.radius_km or 5.0).model_dump()
        )

    scores = [r["prediction"]["development_score"] for r in results]
    best_idx = int(max(range(len(scores)), key=lambda i: scores[i]))
    return {
        "count": len(results),
        "results": results,
        "best": {
            "index": best_idx,
            "query": results[best_idx]["query"],
            "score": scores[best_idx],
        },
        "score_delta": round(max(scores) - min(scores), 2),
    }


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
