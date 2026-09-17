import httpx

GEOCODING_API_URL = "https://geocoding-api.open-meteo.com/v1/search"


async def search_location(city_name: str) -> dict:
    """
    Search for location coordinates using Open-Meteo Geocoding API.
    """
    params = {"name": city_name, "count": 1, "language": "en", "format": "json"}
    async with httpx.AsyncClient() as client:
        response = await client.get(GEOCODING_API_URL, params=params)
        response.raise_for_status()
        return response.json()
