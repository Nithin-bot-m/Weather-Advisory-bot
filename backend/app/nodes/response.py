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
    except Exception:
        target_sop = selected_sop or evaluated_sop or {}
        sop_id = target_sop.get("id", "N/A")
        sop_name = target_sop.get("name", "N/A")
        advice = target_sop.get("advice", "")
        if selected_sop:
            return {
                "response": f"[{sop_id}: {sop_name}] {advice.strip()}"
            }
        elif evaluated_sop:
            return {
                "response": f"[{sop_id}: {sop_name}] Evaluated weather conditions in {location.get('name', 'the location')}. Live weather parameters are within safe limits according to policy thresholds."
            }
        else:
            return {"response": "No applicable SOP policy found."}



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


async def situational_override_response(state: GraphState) -> Dict[str, Any]:
    """
    Dedicated node for situational weather override handling.
    Executes when a severe situational weather policy (e.g. SOP-014) breaches and outranks ordinary activity SOPs.
    """
    user_question = state.get("user_question", "")
    weather = state.get("weather", {})
    location = state.get("resolved_location", {})
    selected_sop = state.get("selected_sop") or {}

    system_prompt = """You are a situational-override response component in a policy-controlled weather advisory system.

A severe situational weather policy (SOP-014: Severe Weather System Override) has triggered and takes total precedence over ordinary activity-specific advice.

You must:
1. Lead directly with the severe weather system override warning.
2. State clearly that the situational policy outranks ordinary activity guidance.
3. Cite the SOP ID (SOP-014) and SOP Name (Severe Weather System Override).
4. Rely strictly on the provided factual weather values.

Do not invent weather. Do not estimate weather."""

    context_prompt = f"""TRUSTED LOCATION:
{json.dumps(location, indent=2)}

TRUSTED WEATHER:
{json.dumps(weather, indent=2)}

SITUATIONAL OVERRIDE SOP:
{json.dumps(selected_sop, indent=2)}

USER QUESTION:
{user_question}"""

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        sop_id = selected_sop.get("id", "SOP-014")
        sop_name = selected_sop.get("name", "Severe Weather System Override")
        advice = selected_sop.get("advice", "")
        return {
            "response": f"[{sop_id}: {sop_name}] {advice.strip()}"
        }

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
    except Exception:
        sop_id = selected_sop.get("id", "SOP-014")
        sop_name = selected_sop.get("name", "Severe Weather System Override")
        advice = selected_sop.get("advice", "")
        return {
            "response": f"[{sop_id}: {sop_name}] {advice.strip()}"
        }


async def weather_response(state: GraphState) -> Dict[str, Any]:
    """
    Format natural language weather forecast for general weather queries without evaluating activity SOPs.
    """
    weather = state.get("weather") or {}
    resolved_loc = state.get("resolved_location") or {}
    city_name = resolved_loc.get("name") or state.get("location") or "the requested location"

    temp = weather.get("temperature_2m", "N/A")
    wind = weather.get("wind_speed_10m", "N/A")
    precip = weather.get("precipitation", "N/A")
    precip_prob = weather.get("precipitation_probability", "N/A")
    uv = weather.get("uv_index", "N/A")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {
            "response": f"Current weather forecast for {city_name}: Temperature: {temp}°C, Wind Speed: {wind} km/h, Precipitation: {precip} mm (Probability: {precip_prob}%), UV Index: {uv}.",
            "selected_sop": None,
        }

    try:
        model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        llm = ChatOpenAI(model=model_name, temperature=0, api_key=api_key)
        system_prompt = "You are a weather information assistant. Provide a concise, accurate weather summary strictly using the provided factual weather data."
        user_prompt = f"City: {city_name}\nWeather Data: {json.dumps(weather, indent=2)}"
        res = await llm.ainvoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
        return {
            "response": res.content,
            "selected_sop": None,
        }
    except Exception:
        return {
            "response": f"Current weather forecast for {city_name}: Temperature: {temp}°C, Wind Speed: {wind} km/h, Precipitation: {precip} mm (Probability: {precip_prob}%), UV Index: {uv}.",
            "selected_sop": None,
        }


async def general_response(state: GraphState) -> Dict[str, Any]:
    """
    Handle greetings and general conversational inquiries without invoking weather lookup or policy engine.
    """
    return {
        "response": "Hello! I am your Weather Advisory Support Bot. Ask me about weather conditions in a city or whether an outdoor activity (like walking, cycling, running, or hiking) is safe given current weather.",
        "selected_sop": None,
    }


async def unsupported_response(state: GraphState) -> Dict[str, Any]:
    """
    Handle unrelated or out-of-scope questions without calling weather service or policy engine.
    """
    return {
        "response": "I am designed specifically for weather forecasts and outdoor activity safety advisories. Please ask me about the weather in a city or whether an outdoor activity is safe.",
        "selected_sop": None,
    }


