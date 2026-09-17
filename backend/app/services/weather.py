import asyncio
import httpx
from backend.app.models.weather import WeatherData

FORECAST_API_URL = "https://api.open-meteo.com/v1/forecast"


class WeatherFetchError(Exception):
    """Raised when weather forecast data cannot be fetched or parsed."""
    pass


async def fetch_weather_forecast(latitude: float, longitude: float) -> WeatherData:
    """
    Fetch current weather forecast from Open-Meteo API with retry fallback.
    Required current weather fields:
    - temperature_2m
    - wind_speed_10m
    - precipitation
    - precipitation_probability
    - uv_index
    """
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,wind_speed_10m,precipitation,precipitation_probability,uv_index",
    }
    headers = {"User-Agent": "WeatherAdvisoryBot/1.0"}
    
    last_exc = None
    data = None
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(FORECAST_API_URL, params=params, headers=headers)
                if response.status_code == 429 and attempt < 2:
                    await asyncio.sleep(1.5 * (attempt + 1))
                    continue
                response.raise_for_status()
                data = response.json()
                break
        except Exception as exc:
            last_exc = exc
            if attempt < 2:
                await asyncio.sleep(1.0)
                continue
            raise WeatherFetchError(f"Failed to fetch weather data for coordinates ({latitude}, {longitude}): {exc}") from exc

    if not data or not data.get("current"):
        raise WeatherFetchError("Open-Meteo response did not contain 'current' weather data.")

    current = data["current"]

    try:
        return WeatherData(
            temperature_2m=float(current["temperature_2m"]),
            wind_speed_10m=float(current["wind_speed_10m"]),
            precipitation=float(current.get("precipitation", 0.0)),
            precipitation_probability=float(current.get("precipitation_probability", 0.0)),
            uv_index=float(current.get("uv_index", 0.0)),
        )
    except KeyError as missing_key:
        raise WeatherFetchError(f"Missing required weather field in Open-Meteo response: {missing_key}") from missing_key
