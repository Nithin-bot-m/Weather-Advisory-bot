import httpx
from backend.app.models.location import LocationData

GEOCODING_API_URL = "https://geocoding-api.open-meteo.com/v1/search"


class LocationNotFoundError(Exception):
    """Raised when the requested city or location cannot be resolved."""
    pass


async def search_location(city_name: str) -> LocationData:
    """
    Search for location coordinates using Open-Meteo Geocoding API.
    Returns structured LocationData or raises LocationNotFoundError.
    """
    if not city_name or not city_name.strip():
        raise LocationNotFoundError("Location query cannot be empty.")

    params = {"name": city_name.strip(), "count": 1, "language": "en", "format": "json"}
    async with httpx.AsyncClient() as client:
        response = await client.get(GEOCODING_API_URL, params=params)
        response.raise_for_status()
        data = response.json()

    results = data.get("results")
    if not results or len(results) == 0:
        raise LocationNotFoundError(f"Location '{city_name}' could not be resolved.")

    first = results[0]
    return LocationData(
        name=first["name"],
        latitude=float(first["latitude"]),
        longitude=float(first["longitude"]),
        country=first.get("country"),
    )
