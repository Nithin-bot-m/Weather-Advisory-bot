"""
LangGraph state definitions (Placeholder for Step 2+).
"""
from typing import TypedDict, List, Optional, Dict, Any


class GraphState(TypedDict, total=False):
    messages: List[Dict[str, Any]]
    query: str
    location: Optional[str]
    coordinates: Optional[Dict[str, float]]
    weather_data: Optional[Dict[str, Any]]
    sop_matched: Optional[Dict[str, Any]]
    response: Optional[str]
