"""
Weather data retrieval node for Weather Advisory Support Bot.
"""
from typing import Dict, Any
from backend.app.state import GraphState
from backend.app.services.weather import fetch_weather_forecast, WeatherFetchError


async def fetch_weather(state: GraphState) -> Dict[str, Any]:
    """
    Fetch live current weather forecast from Open-Meteo API using resolved coordinates.
    """
    resolved_loc = state.get("resolved_location")
    if not resolved_loc or "latitude" not in resolved_loc or "longitude" not in resolved_loc:
        return {
            "error": "Cannot fetch weather: Valid location coordinates are missing.",
            "weather": None,
        }

    try:
        lat = float(resolved_loc["latitude"])
        lon = float(resolved_loc["longitude"])
        weather_data = await fetch_weather_forecast(latitude=lat, longitude=lon)
        return {
            "weather": weather_data.model_dump(),
            "error": None,
        }
    except WeatherFetchError as exc:
        return {
            "error": f"Weather retrieval failed: {str(exc)}",
            "weather": None,
        }
    except Exception as exc:
        return {
            "error": f"Weather service exception: {str(exc)}",
            "weather": None,
        }


def route_after_weather(state: GraphState) -> str:
    """
    Conditional router after weather retrieval.
    Returns 'error' if error is present, otherwise 'success'.
    """
    if state.get("error"):
        return "error"
    return "success"

