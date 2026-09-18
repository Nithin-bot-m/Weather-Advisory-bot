"""
LangGraph workflow topology for Weather Advisory Support Bot.
"""
from langgraph.graph import StateGraph, START, END
from backend.app.state import GraphState
from backend.app.nodes.understand import understand_question
from backend.app.nodes.location import resolve_location, route_after_location
from backend.app.nodes.weather import fetch_weather
from backend.app.nodes.sop_matcher import match_sops, route_after_sop
from backend.app.nodes.response import (
    compose_response,
    no_guidance,
    error_response,
    situational_override_response,
    weather_response,
    general_response,
    unsupported_response,
)


def route_after_understand(state: GraphState) -> str:
    """
    Conditional router after intent classification.
    """
    intent = state.get("intent")
    if intent == "general":
        return "general"
    elif intent == "unsupported":
        return "unsupported"
    return "resolve_location"


def route_after_weather(state: GraphState) -> str:
    """
    Conditional router after weather retrieval.
    Routes to weather_response for pure weather queries, or match_sops for activity advisories.
    """
    if state.get("error"):
        return "error"
    if state.get("intent") == "weather_query":
        return "weather_query"
    return "match_sops"


def build_graph():
    """
    Construct and compile the Weather Advisory StateGraph.
    """
    workflow = StateGraph(GraphState)

    # 1. Add Graph Nodes
    workflow.add_node("understand_question", understand_question)
    workflow.add_node("general_response", general_response)
    workflow.add_node("unsupported_response", unsupported_response)
    workflow.add_node("resolve_location", resolve_location)
    workflow.add_node("fetch_weather", fetch_weather)
    workflow.add_node("weather_response", weather_response)
    workflow.add_node("match_sops", match_sops)
    workflow.add_node("situational_override_response", situational_override_response)
    workflow.add_node("compose_response", compose_response)
    workflow.add_node("no_guidance", no_guidance)
    workflow.add_node("error_response", error_response)

    # 2. Add Start Edge
    workflow.add_edge(START, "understand_question")

    # 3. Add Conditional Edges
    workflow.add_conditional_edges(
        "understand_question",
        route_after_understand,
        {
            "general": "general_response",
            "unsupported": "unsupported_response",
            "resolve_location": "resolve_location",
        },
    )

    workflow.add_conditional_edges(
        "resolve_location",
        route_after_location,
        {
            "error": "error_response",
            "success": "fetch_weather",
        },
    )

    workflow.add_conditional_edges(
        "fetch_weather",
        route_after_weather,
        {
            "error": "error_response",
            "weather_query": "weather_response",
            "match_sops": "match_sops",
        },
    )

    workflow.add_conditional_edges(
        "match_sops",
        route_after_sop,
        {
            "situational_override": "situational_override_response",
            "no_match": "no_guidance",
            "matched": "compose_response",
        },
    )

    # 4. Terminal Edges to END
    workflow.add_edge("general_response", END)
    workflow.add_edge("unsupported_response", END)
    workflow.add_edge("weather_response", END)
    workflow.add_edge("error_response", END)
    workflow.add_edge("no_guidance", END)
    workflow.add_edge("compose_response", END)
    workflow.add_edge("situational_override_response", END)

    return workflow.compile()


# Export compiled graph instance
graph = build_graph()


