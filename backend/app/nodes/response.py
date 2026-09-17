"""
Response generation nodes for Weather Advisory Support Bot.
"""
import os
import json
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from backend.app.state import GraphState

RESPONSE_SYSTEM_PROMPT = """You are a response-composition component in a policy-controlled weather advisory system.

The selected SOP is authoritative.

You may only communicate:
1. factual weather values supplied in the trusted weather data
2. advice supplied by the selected SOP

Do not create policies.
Do not modify policies.
Do not override policies.
Do not invent weather.
Do not estimate weather.
Do not change numerical values.

Always identify the SOP ID and SOP name.

If a fact is not present in the supplied data, do not claim it."""


async def compose_response(state: GraphState) -> Dict[str, Any]:
    """
    Compose natural language advisory strictly using trusted weather facts and authoritative selected SOP.
    """
    user_question = state.get("user_question", "")
    weather = state.get("weather", {})
    location = state.get("resolved_location", {})
    selected_sop = state.get("selected_sop", {})

    context_prompt = f"""TRUSTED LOCATION:
{json.dumps(location, indent=2)}

TRUSTED WEATHER:
{json.dumps(weather, indent=2)}

TRUSTED SOP:
{json.dumps(selected_sop, indent=2)}

USER QUESTION:
{user_question}"""

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # Fallback formatting when OPENAI_API_KEY is not set
        sop_id = selected_sop.get("id", "N/A")
        sop_name = selected_sop.get("name", "N/A")
        advice = selected_sop.get("advice", "")
        return {
            "response": f"[{sop_id}: {sop_name}] {advice.strip()}"
        }

    try:
        model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        llm = ChatOpenAI(model=model_name, temperature=0, api_key=api_key)
        messages = [
            SystemMessage(content=RESPONSE_SYSTEM_PROMPT),
            HumanMessage(content=context_prompt),
        ]
        res = await llm.ainvoke(messages)
        return {
            "response": res.content,
        }
    except Exception as exc:
        # Fallback if LLM call encounters error
        sop_id = selected_sop.get("id", "N/A")
        sop_name = selected_sop.get("name", "N/A")
        advice = selected_sop.get("advice", "")
        return {
            "response": f"[{sop_id}: {sop_name}] {advice.strip()} (Response generation fallback: {exc})"
        }


async def no_guidance(state: GraphState) -> Dict[str, Any]:
    """
    Return standard no-guidance message when no SOP policy matches.
    Does NOT call LLM to invent generic advice.
    """
    return {
        "response": "I don't have an applicable SOP for this activity and the available weather conditions, so I can't provide weather-based guidance.",
        "selected_sop": None,
    }


async def error_response(state: GraphState) -> Dict[str, Any]:
    """
    Return explicit error response when a upstream node fails.
    """
    error_msg = state.get("error", "An error occurred during processing.")
    return {
        "response": f"Unable to process weather advisory request: {error_msg}",
    }

