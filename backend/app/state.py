"""
LangGraph state definitions for Weather Advisory Support Bot.
"""
from typing import TypedDict, List, Optional, Dict, Any


class GraphState(TypedDict, total=False):
    # USER INPUT
    user_question: str
    messages: List[Dict[str, Any]]

    # EXTRACTED INTENT
    intent: Optional[str]
    activity: Optional[str]
    location: Optional[str]
    time_context: Optional[str]

    # EXTERNAL FACTS
    resolved_location: Optional[Dict[str, Any]]
    weather: Optional[Dict[str, Any]]

    # POLICY DECISION
    matching_sops: Optional[List[Dict[str, Any]]]
    selected_sop: Optional[Dict[str, Any]]
    evaluated_sop: Optional[Dict[str, Any]]

    # OUTPUT
    response: Optional[str]
    error: Optional[str]

