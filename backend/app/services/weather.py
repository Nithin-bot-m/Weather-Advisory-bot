import httpx

FORECAST_API_URL = "https://api.open-meteo.com/v1/forecast"


async def fetch_weather_forecast(latitude: float, longitude: float) -> dict:
    """
    Fetch current weather forecast from Open-Meteo API.
    Required current weather fields (comma-separated):
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
    async with httpx.AsyncClient() as client:
        response = await client.get(FORECAST_API_URL, params=params)
        response.raise_for_status()
        return response.json()
