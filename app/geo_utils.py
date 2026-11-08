"""
Geographical helpers and indicator generators.

City → coordinates: built-in dict + Nominatim fallback.
Indicators: deterministic, region-aware heuristics (demo-ready).
"""

from __future__ import annotations

import math
from functools import lru_cache
from typing import Optional, Tuple, Dict, Any
import numpy as np

# Fallback city coordinates (lat, lon)
CITY_COORDS: Dict[str, Tuple[float, float]] = {
    "moscow": (55.7558, 37.6173),
    "москва": (55.7558, 37.6173),
    "saint petersburg": (59.9343, 30.3351),
    "санкт-петербург": (59.9343, 30.3351),
    "spb": (59.9343, 30.3351),
    "novosibirsk": (55.0084, 82.9357),
    "новосибирск": (55.0084, 82.9357),
    "yekaterinburg": (56.8389, 60.6057),
    "екатеринбург": (56.8389, 60.6057),
    "kazan": (55.7961, 49.1064),
    "казань": (55.7961, 49.1064),
    "nizhny novgorod": (56.2965, 43.9361),
    "нижний новгород": (56.2965, 43.9361),
    "samara": (53.2415, 50.2212),
    "самара": (53.2415, 50.2212),
    "omsk": (54.9885, 73.3242),
    "омск": (54.9885, 73.3242),
    "chelyabinsk": (55.1644, 61.4368),
    "челябинск": (55.1644, 61.4368),
    "rostov-on-don": (47.2357, 39.7015),
    "ростов-на-дону": (47.2357, 39.7015),
    "ufa": (54.7388, 55.9721),
    "уфа": (54.7388, 55.9721),
    "krasnoyarsk": (56.0153, 92.8932),
    "красноярск": (56.0153, 92.8932),
    "voronezh": (51.6720, 39.1843),
    "воронеж": (51.6720, 39.1843),
    "perm": (58.0105, 56.2502),
    "пермь": (58.0105, 56.2502),
    "volgograd": (48.7080, 44.5133),
    "волгоград": (48.7080, 44.5133),
    "krasnodar": (45.0355, 38.9753),
    "краснодар": (45.0355, 38.9753),
    "saratov": (51.5336, 46.0343),
    "саратов": (51.5336, 46.0343),
    "tyumen": (57.1522, 65.5272),
    "тюмень": (57.1522, 65.5272),
    "togliatti": (53.5303, 49.3461),
    "тольятти": (53.5303, 49.3461),
    "izhevsk": (56.8527, 53.2115),
    "ижевск": (56.8527, 53.2115),
    "barnaul": (53.3548, 83.7698),
    "барнаул": (53.3548, 83.7698),
    "ulyanovsk": (54.3142, 48.4031),
    "ульяновск": (54.3142, 48.4031),
    "irkutsk": (52.2869, 104.3050),
    "иркутск": (52.2869, 104.3050),
    "khabarovsk": (48.4827, 135.0838),
    "хабаровск": (48.4827, 135.0838),
    "yaroslavl": (57.6261, 39.8845),
    "ярославль": (57.6261, 39.8845),
    "vladivostok": (43.1155, 131.8855),
    "владивосток": (43.1155, 131.8855),
    "makhachkala": (42.9849, 47.5047),
    "махачкала": (42.9849, 47.5047),
    "tomsk": (56.4846, 84.9476),
    "томск": (56.4846, 84.9476),
    "orenburg": (51.7727, 55.0988),
    "оренбург": (51.7727, 55.0988),
    "kemerovo": (55.3549, 86.0873),
    "кемерово": (55.3549, 86.0873),
    "novokuznetsk": (53.7596, 87.1216),
    "новокузнецк": (53.7596, 87.1216),
    "ryazan": (54.6269, 39.6916),
    "рязань": (54.6269, 39.6916),
    "astrakhan": (46.3497, 48.0408),
    "астрахань": (46.3497, 48.0408),
    "naberezhnye chelny": (55.7436, 52.3958),
    "набережные челны": (55.7436, 52.3958),
    "penza": (53.2001, 45.0000),
    "пенза": (53.2001, 45.0000),
    "lipetsk": (52.6031, 39.5708),
    "липецк": (52.6031, 39.5708),
    "kirov": (58.6035, 49.6680),
    "киров": (58.6035, 49.6680),
    "cheboksary": (56.1439, 47.2489),
    "чебоксары": (56.1439, 47.2489),
    "kaliningrad": (54.7104, 20.4522),
    "калининград": (54.7104, 20.4522),
    "tula": (54.1931, 37.6173),
    "тула": (54.1931, 37.6173),
    "kursk": (51.7373, 36.1873),
    "курск": (51.7373, 36.1873),
    "stavropol": (45.0445, 41.9691),
    "ставрополь": (45.0445, 41.9691),
    "ulan-ude": (51.8335, 107.5841),
    "улан-удэ": (51.8335, 107.5841),
    "tver": (56.8587, 35.9176),
    "тверь": (56.8587, 35.9176),
    "magnitogorsk": (53.4186, 58.9795),
    "магнитогорск": (53.4186, 58.9795),
    "ivanovo": (56.9991, 40.9728),
    "иваново": (56.9991, 40.9728),
    "bryansk": (53.2521, 34.3717),
    "брянск": (53.2521, 34.3717),
    "belgorod": (50.5954, 36.5873),
    "белгород": (50.5954, 36.5873),
    "sochi": (43.6028, 39.7342),
    "сочи": (43.6028, 39.7342),
    "london": (51.5074, -0.1278),
    "лондон": (51.5074, -0.1278),
    "new york": (40.7128, -74.0060),
    "нью-йорк": (40.7128, -74.0060),
    "paris": (48.8566, 2.3522),
    "париж": (48.8566, 2.3522),
    "berlin": (52.5200, 13.4050),
    "берлин": (52.5200, 13.4050),
    "tokyo": (35.6762, 139.6503),
    "токио": (35.6762, 139.6503),
    "beijing": (39.9042, 116.4074),
    "пекин": (39.9042, 116.4074),
    "istanbul": (41.0082, 28.9784),
    "стамбул": (41.0082, 28.9784),
    "dubai": (25.2048, 55.2708),
    "дубай": (25.2048, 55.2708),
    "singapore": (1.3521, 103.8198),
    "сингапур": (1.3521, 103.8198),
    "seoul": (37.5665, 126.9780),
    "сеул": (37.5665, 126.9780),
    "sydney": (-33.8688, 151.2093),
    "сидней": (-33.8688, 151.2093),
    "toronto": (43.6532, -79.3832),
    "торонто": (43.6532, -79.3832),
    "los angeles": (34.0522, -118.2437),
    "лос-анджелес": (34.0522, -118.2437),
    "mumbai": (19.0760, 72.8777),
    "мумбаи": (19.0760, 72.8777),
    "sao paulo": (-23.5505, -46.6333),
    "сан-паулу": (-23.5505, -46.6333),
    "cairo": (30.0444, 31.2357),
    "каир": (30.0444, 31.2357),
}




def _load_city_coords() -> Dict[str, Tuple[float, float]]:
    """Подгрузить города из data/cities.json (если файл есть)."""
    import json
    from pathlib import Path
    json_path = Path(__file__).resolve().parent.parent / "data" / "cities.json"
    coords = dict(CITY_COORDS)
    if json_path.exists():
        try:
            with open(json_path, encoding="utf-8") as f:
                items = json.load(f)
            for item in items:
                name = str(item.get("name", "")).strip().lower()
                if name:
                    coords[name] = (float(item["lat"]), float(item["lon"]))
        except Exception:
            pass
    return coords


# Актуальный справочник: встроенный dict + data/cities.json
CITY_COORDS = _load_city_coords()


# Major metro areas: slight boost to density / infra / economy
METRO_HUBS = [
    # (lat, lon, radius_km, density_boost, infra_boost, econ_boost)
    (55.75, 37.62, 40, 1.35, 1.25, 1.30),   # Moscow
    (59.93, 30.34, 30, 1.25, 1.20, 1.22),   # SPb
    (40.71, -74.01, 35, 1.40, 1.30, 1.35),  # NYC
    (51.51, -0.13, 30, 1.30, 1.28, 1.30),   # London
    (35.68, 139.69, 35, 1.40, 1.32, 1.30),  # Tokyo
    (48.86, 2.35, 25, 1.25, 1.25, 1.25),    # Paris
    (1.35, 103.82, 20, 1.35, 1.35, 1.40),   # Singapore
    (25.20, 55.27, 25, 1.20, 1.30, 1.35),   # Dubai
    (37.57, 126.98, 30, 1.30, 1.28, 1.25),  # Seoul
    (39.90, 116.41, 40, 1.35, 1.25, 1.28),  # Beijing
    (43.60, 39.73, 20, 1.10, 1.15, 1.20),   # Sochi (tourism)
]


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in km between two points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


@lru_cache(maxsize=256)
def geocode_city(city: str) -> Optional[Tuple[float, float]]:
    """Resolve city name to (lat, lon). Tries built-in dict first, then Nominatim."""
    key = city.strip().lower()
    if key in CITY_COORDS:
        return CITY_COORDS[key]

    try:
        from geopy.geocoders import Nominatim
        geolocator = Nominatim(user_agent="geo_intelligence_api_v2")
        location = geolocator.geocode(city, timeout=6)
        if location:
            return (location.latitude, location.longitude)
    except Exception:
        pass

    return None


def _metro_boosts(lat: float, lon: float) -> Tuple[float, float, float]:
    """Return (density, infra, econ) multipliers based on proximity to major hubs."""
    dens_b, infra_b, econ_b = 1.0, 1.0, 1.0
    for mlat, mlon, radius, db, ib, eb in METRO_HUBS:
        dist = haversine(lat, lon, mlat, mlon)
        if dist < radius:
            # linear falloff
            t = 1.0 - dist / radius
            dens_b = max(dens_b, 1.0 + (db - 1.0) * t)
            infra_b = max(infra_b, 1.0 + (ib - 1.0) * t)
            econ_b = max(econ_b, 1.0 + (eb - 1.0) * t)
    return dens_b, infra_b, econ_b


def generate_indicators(lat: float, lon: float) -> Dict[str, float]:
    """
    Более реалистичные индикаторы по координатам (демо).

    Плотность населения:
    - вдали от метро: чаще 50–1500 чел/км²
    - пригороды: 1500–5000
    - ядро крупного города: 5000–18000
    Не каждый запрос даёт 4000+.
    """
    seed = int(abs(lat * 1e6) + abs(lon * 1e6)) % (2**32 - 1)
    rng = np.random.RandomState(seed)

    abs_lat = abs(lat)

    # Ближайший метро-хаб
    min_dist = 1e9
    nearest_radius = 40.0
    for mlat, mlon, radius, db, ib, eb in METRO_HUBS:
        d = haversine(lat, lon, mlat, mlon)
        if d < min_dist:
            min_dist = d
            nearest_radius = float(radius)

    # Профиль плотности по удалению от хаба
    if min_dist <= 3:
        # исторический/деловой центр
        base_lo, base_hi = 7000, 16000
        urban = 1.0
    elif min_dist <= 10:
        base_lo, base_hi = 3500, 9000
        urban = 0.85
    elif min_dist <= nearest_radius:
        # пригород / спальный район
        t = min_dist / nearest_radius
        base_lo = 800 + (1 - t) * 2000
        base_hi = 2500 + (1 - t) * 3500
        urban = 0.55 * (1 - t) + 0.25
    elif min_dist <= nearest_radius * 3:
        base_lo, base_hi = 80, 1200
        urban = 0.2
    else:
        # периферия / сельская местность
        base_lo, base_hi = 15, 400
        urban = 0.08

    # Лог-равномерное распределение внутри диапазона (больше «низких» значений)
    u = rng.uniform(0.0, 1.0)
    log_lo, log_hi = np.log(max(base_lo, 5)), np.log(max(base_hi, 10))
    population_density = float(np.exp(log_lo + u * (log_hi - log_lo)))
    # чуть шума
    population_density *= float(rng.uniform(0.92, 1.08))
    population_density = float(np.clip(population_density, 5, 22000))

    # Зелень: в центре меньше, на окраине больше
    green_base = 0.08 + (1.0 - urban) * 0.28 + rng.uniform(-0.03, 0.05)
    if abs_lat > 55:
        green_base *= 0.9
    elif abs_lat < 20:
        green_base *= 1.05
    green_space_ratio = float(np.clip(green_base, 0.02, 0.55))

    # Инфраструктура / транспорт / экономика — связаны с «городскостью»
    infrastructure_index = float(np.clip(
        0.15 + urban * 0.55 + rng.uniform(0, 0.2) + (0.08 if min_dist < 15 else 0),
        0.08, 0.98,
    ))
    transport_access = float(np.clip(
        0.1 + urban * 0.6 + rng.uniform(0, 0.18) + (0.1 if min_dist < 8 else 0),
        0.05, 0.98,
    ))
    economic_activity = float(np.clip(
        0.12 + urban * 0.55 + rng.uniform(0, 0.2) + (0.1 if min_dist < 12 else 0),
        0.08, 0.98,
    ))

    return {
        "population_density": round(population_density, 1),
        "green_space_ratio": round(green_space_ratio, 3),
        "infrastructure_index": round(infrastructure_index, 3),
        "transport_access": round(transport_access, 3),
        "economic_activity": round(economic_activity, 3),
    }


def classify_development(score: float) -> str:
    if score >= 80:
        return "highly_developed"
    if score >= 60:
        return "developed"
    if score >= 40:
        return "moderately_developed"
    if score >= 20:
        return "developing"
    return "underdeveloped"


def development_label_ru(level: str) -> str:
    return {
        "highly_developed": "Высоко развитый",
        "developed": "Развитый",
        "moderately_developed": "Умеренно развитый",
        "developing": "Развивающийся",
        "underdeveloped": "Слабо развитый",
    }.get(level, level)
