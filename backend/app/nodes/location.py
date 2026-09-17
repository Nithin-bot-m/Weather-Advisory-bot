"""
Location resolution node for Weather Advisory Support Bot.
"""
from typing import Dict, Any
from backend.app.state import GraphState
from backend.app.services.geocoding import search_location, LocationNotFoundError


async def resolve_location(state: GraphState) -> Dict[str, Any]:
    """
    Resolve location query string into latitude and longitude coordinates using Open-Meteo.
    """
    location_query = state.get("location")
    if not location_query or not str(location_query).strip():
        return {
            "error": "Location was not specified in the query and could not be inferred.",
            "resolved_location": None,
        }

    try:
        location_data = await search_location(location_query)
        return {
            "resolved_location": location_data.model_dump(),
            "error": None,
        }
    except LocationNotFoundError as exc:
        return {
            "error": f"Failed to resolve location: {str(exc)}",
            "resolved_location": None,
        }
    except Exception as exc:
        return {
            "error": f"Geocoding service failure: {str(exc)}",
            "resolved_location": None,
        }


def route_after_location(state: GraphState) -> str:
    """
    Conditional router after location resolution.
    Returns 'error' if error is present, otherwise 'success'.
    """
    if state.get("error"):
        return "error"
    return "success"

