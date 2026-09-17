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
    Compose natural language advisory strictly using trusted weather facts and authoritative SOP.
    Handles both hazard warnings (selected_sop) and safe weather evaluation (evaluated_sop).
    """
    user_question = state.get("user_question", "")
    weather = state.get("weather", {})
    location = state.get("resolved_location", {})
    selected_sop = state.get("selected_sop")
    evaluated_sop = state.get("evaluated_sop")

    if selected_sop:
        system_prompt = RESPONSE_SYSTEM_PROMPT
        context_prompt = f"""TRUSTED LOCATION:
{json.dumps(location, indent=2)}

TRUSTED WEATHER:
{json.dumps(weather, indent=2)}

TRUSTED SOP (WARNING TRIGGERED):
{json.dumps(selected_sop, indent=2)}

USER QUESTION:
{user_question}"""
    else:
        system_prompt = """You are a response-composition component in a policy-controlled weather advisory system.

An applicable SOP policy exists for this activity, but current weather conditions do NOT exceed or breach any configured warning thresholds in the SOP (weather conditions are safe / within normal limits).

You may only communicate:
1. factual weather values supplied in the trusted weather data (e.g., temperature, wind speed, precipitation)
2. state clearly that the weather conditions were evaluated against the SOP (always identify the SOP ID and SOP name) and are within safe parameters according to configured thresholds.

Do not create policies.
Do not override policies.
Do not invent weather.
Do not estimate weather.

Always identify the SOP ID and SOP name.
If a fact is not present in the supplied data, do not claim it."""
        context_prompt = f"""TRUSTED LOCATION:
{json.dumps(location, indent=2)}

TRUSTED WEATHER:
{json.dumps(weather, indent=2)}

TRUSTED EVALUATED SOP (CONDITIONS SAFE / BELOW THRESHOLDS):
{json.dumps(evaluated_sop, indent=2)}

USER QUESTION:
{user_question}"""

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        if selected_sop:
            sop_id = selected_sop.get("id", "N/A")
            sop_name = selected_sop.get("name", "N/A")
            advice = selected_sop.get("advice", "")
            return {
                "response": f"[{sop_id}: {sop_name}] {advice.strip()}"
            }
        elif evaluated_sop:
            sop_id = evaluated_sop.get("id", "N/A")
            sop_name = evaluated_sop.get("name", "N/A")
            return {
                "response": f"[{sop_id}: {sop_name}] Evaluated weather conditions in {location.get('name', 'the location')}. Live weather parameters are within safe limits according to policy thresholds."
            }
        else:
            return {"response": "No applicable SOP policy found."}

    try:
        model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        llm = ChatOpenAI(model=model_name, temperature=0, api_key=api_key)
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=context_prompt),
        ]
        res = await llm.ainvoke(messages)
        return {
            "response": res.content,
        }
    except Exception as exc:
        target_sop = selected_sop or evaluated_sop or {}
        sop_id = target_sop.get("id", "N/A")
        sop_name = target_sop.get("name", "N/A")
        advice = target_sop.get("advice", "Weather evaluated against policy.")
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

