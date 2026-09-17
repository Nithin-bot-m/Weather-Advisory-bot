"""
LangGraph workflow topology for Weather Advisory Support Bot.
"""
from langgraph.graph import StateGraph, START, END
from backend.app.state import GraphState
from backend.app.nodes.understand import understand_question
from backend.app.nodes.location import resolve_location, route_after_location
from backend.app.nodes.weather import fetch_weather, route_after_weather
from backend.app.nodes.sop_matcher import match_sops, route_after_sop
from backend.app.nodes.response import compose_response, no_guidance, error_response


def build_graph():
    """
    Construct and compile the Weather Advisory StateGraph.
    """
    workflow = StateGraph(GraphState)

    # 1. Add Graph Nodes
    workflow.add_node("understand_question", understand_question)
    workflow.add_node("resolve_location", resolve_location)
    workflow.add_node("fetch_weather", fetch_weather)
    workflow.add_node("match_sops", match_sops)
    workflow.add_node("compose_response", compose_response)
    workflow.add_node("no_guidance", no_guidance)
    workflow.add_node("error_response", error_response)

    # 2. Add Direct Edges
    workflow.add_edge(START, "understand_question")
    workflow.add_edge("understand_question", "resolve_location")

    # 3. Add Conditional Edges
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
            "success": "match_sops",
        },
    )

    workflow.add_conditional_edges(
        "match_sops",
        route_after_sop,
        {
            "no_match": "no_guidance",
            "matched": "compose_response",
        },
    )

    # 4. Terminal Edges to END
    workflow.add_edge("error_response", END)
    workflow.add_edge("no_guidance", END)
    workflow.add_edge("compose_response", END)

    return workflow.compile()


# Export compiled graph instance (compilation only, no execution at import time)
graph = build_graph()

