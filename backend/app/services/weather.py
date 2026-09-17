import asyncio
import time
import httpx
from typing import Dict, Tuple
from backend.app.models.weather import WeatherData

FORECAST_API_URL = "https://api.open-meteo.com/v1/forecast"

# In-memory weather cache: (lat_rounded, lon_rounded) -> (timestamp, WeatherData)
_WEATHER_CACHE: Dict[Tuple[float, float], Tuple[float, WeatherData]] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes TTL cache


class WeatherFetchError(Exception):
    """Raised when weather forecast data cannot be fetched or parsed."""
    pass


async def fetch_weather_forecast(latitude: float, longitude: float) -> WeatherData:
    """
    Fetch current weather forecast from Open-Meteo API with retry fallback and 5-minute in-memory caching.
    Required current weather fields:
    - temperature_2m
    - wind_speed_10m
    - precipitation
    - precipitation_probability
    - uv_index
    """
    cache_key = (round(latitude, 2), round(longitude, 2))
    now = time.time()

    # 1. Return cached weather data if valid
    if cache_key in _WEATHER_CACHE:
        cached_time, cached_weather = _WEATHER_CACHE[cache_key]
        if now - cached_time < CACHE_TTL_SECONDS:
            return cached_weather

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,wind_speed_10m,precipitation,precipitation_probability,uv_index",
    }
    headers = {"User-Agent": "WeatherAdvisoryBot/1.0"}
    
    data = None
    for attempt in range(4):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(FORECAST_API_URL, params=params, headers=headers)
                if response.status_code == 429 and attempt < 3:
                    await asyncio.sleep(2.0 * (attempt + 1))
                    continue
                response.raise_for_status()
                data = response.json()
                break
        except Exception as exc:
            if attempt < 3:
                await asyncio.sleep(1.5)
                continue
            raise WeatherFetchError(f"Failed to fetch weather data for coordinates ({latitude}, {longitude}): {exc}") from exc

    if not data or not data.get("current"):
        raise WeatherFetchError("Open-Meteo response did not contain 'current' weather data.")

    current = data["current"]

    try:
        weather_obj = WeatherData(
            temperature_2m=float(current["temperature_2m"]),
            wind_speed_10m=float(current["wind_speed_10m"]),
            precipitation=float(current.get("precipitation", 0.0)),
            precipitation_probability=float(current.get("precipitation_probability", 0.0)),
            uv_index=float(current.get("uv_index", 0.0)),
        )
        # Store in cache
        _WEATHER_CACHE[cache_key] = (now, weather_obj)
        return weather_obj
    except KeyError as missing_key:
        raise WeatherFetchError(f"Missing required weather field in Open-Meteo response: {missing_key}") from missing_key
