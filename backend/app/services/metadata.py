from __future__ import annotations

import asyncio
import math
import time
from dataclasses import dataclass

import httpx

from app.config import Settings
from app.models import Stats


@dataclass(slots=True)
class MetadataResult:
    location: str
    stats: Stats
    found: bool


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def climate_estimate(latitude: float) -> str:
    latitude = abs(latitude)
    if latitude >= 50:
        return "Approx. -15°C winter / +28°C summer"
    if latitude >= 40:
        return "Approx. -5°C winter / +27°C summer"
    if latitude >= 25:
        return "Approx. +6°C winter / +31°C summer"
    return "Approx. +18°C winter / +32°C summer"


def living_cost_estimate(country_code: str) -> str:
    ranges = {
        "kz": "$350–$500 / month",
        "ru": "$450–$750 / month",
        "us": "$1,400–$2,400 / month",
        "gb": "$1,100–$1,800 / month",
        "ca": "$1,200–$2,000 / month",
        "au": "$1,300–$2,100 / month",
        "de": "$900–$1,400 / month",
        "fr": "$950–$1,500 / month",
    }
    return f"Approx. {ranges.get(country_code.lower(), '$700–$1,200 / month')}"


class NominatimClient:
    """Rate-limited and cached client for the public Nominatim service."""

    def __init__(self, settings: Settings, client: httpx.AsyncClient) -> None:
        self.settings = settings
        self.client = client
        self._lock = asyncio.Lock()
        self._last_request = 0.0
        self._cache: dict[str, list[dict]] = {}

    async def search(self, query: str) -> list[dict]:
        cache_key = query.casefold()
        if cache_key in self._cache:
            return self._cache[cache_key]
        async with self._lock:
            cached = self._cache.get(cache_key)
            if cached is not None:
                return cached
            elapsed = time.monotonic() - self._last_request
            if elapsed < 1.05:
                await asyncio.sleep(1.05 - elapsed)
            response = await self.client.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "q": query,
                    "format": "jsonv2",
                    "limit": "1",
                    "addressdetails": "1",
                    "accept-language": "en",
                },
                headers={"User-Agent": self.settings.nominatim_user_agent},
                timeout=6.0,
            )
            self._last_request = time.monotonic()
            response.raise_for_status()
            payload = response.json()
            result = payload if isinstance(payload, list) else []
            self._cache[cache_key] = result
            return result


class MetadataPipeline:
    def __init__(self, nominatim: NominatimClient) -> None:
        self.nominatim = nominatim

    async def run(self, university_name: str) -> MetadataResult:
        university_results = await self.nominatim.search(university_name)
        if not university_results:
            return MetadataResult(
                location="Location unavailable",
                stats=Stats(
                    distance_to_city_center="Unavailable",
                    climate="Unavailable",
                    avg_living_cost="Unavailable",
                ),
                found=False,
            )
        place = university_results[0]
        address = place.get("address", {}) if isinstance(place.get("address"), dict) else {}
        city = next(
            (
                address.get(key)
                for key in ("city", "town", "municipality", "village", "county")
                if address.get(key)
            ),
            "Unknown city",
        )
        country = address.get("country") or "Unknown country"
        country_code = address.get("country_code") or ""
        latitude = float(place["lat"])
        longitude = float(place["lon"])

        distance = "Unavailable"
        city_results = await self.nominatim.search(f"{city}, {country}")
        if city_results:
            center = city_results[0]
            kilometers = haversine_km(
                latitude, longitude, float(center["lat"]), float(center["lon"])
            )
            distance = f"{kilometers:.1f} km"

        return MetadataResult(
            location=f"{city}, {country}",
            stats=Stats(
                distance_to_city_center=distance,
                climate=climate_estimate(latitude),
                avg_living_cost=living_cost_estimate(country_code),
            ),
            found=True,
        )
