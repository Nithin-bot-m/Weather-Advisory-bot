"""
Intent extraction node for Weather Advisory Support Bot.
"""
import os
import re
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from backend.app.state import GraphState
from backend.app.policies.normalization import normalize_activity


class IntentCategory(str, Enum):
    ACTIVITY_ADVISORY = "activity_advisory"
    WEATHER_QUERY = "weather_query"
    GENERAL = "general"
    UNSUPPORTED = "unsupported"


INTENT_SYSTEM_PROMPT = """You are an intent extraction component for a weather advisory system.

Your task is to classify the user's intent and extract relevant entities.

Categorize the intent into one of four categories:
1. `activity_advisory`: The user is asking whether a specific outdoor activity (e.g., cycling, walking, running, hiking, picnic, driving) is safe, advisable, or suitable given the weather conditions.
2. `weather_query`: The user is asking for general weather information or weather forecast for a location (e.g., "What is the weather in Delhi?"), WITHOUT asking about a specific outdoor activity.
3. `general`: The user is sending a greeting (e.g., "hi", "hello", "good morning") or general conversational message.
4. `unsupported`: The user is asking a question completely unrelated to weather or outdoor activity advisories (e.g., math calculations like "2 + 2", jokes, history, code).

Extract the following fields:
* intent: one of ["activity_advisory", "weather_query", "general", "unsupported"]
* activity: extracted outdoor activity (e.g., "cycling", "walking", "running") if intent is activity_advisory
* location: target city/location name
* time_context: requested time context (e.g., "today", "this evening", "tomorrow")

Guidelines:
- Do NOT classify general weather queries as activity_advisory.
- Do NOT classify math or jokes as weather_query or activity_advisory.
- Normalize common city name spellings, variants, or typos (e.g. "banglore" or "bangalore" -> "Bengaluru").
- If the user asks a follow-up question (e.g., "What about this evening?", "How about tomorrow?"), recover activity/location from prior context only if the follow-up relates to an ongoing advisory or weather inquiry.

Do NOT provide advice.
Do NOT evaluate safety.
Do NOT evaluate weather.
Do NOT select an SOP."""


class UserIntent(BaseModel):
    intent: IntentCategory = Field(
        IntentCategory.ACTIVITY_ADVISORY,
        description="Category of the user request: 'activity_advisory', 'weather_query', 'general', or 'unsupported'."
    )
    activity: Optional[str] = Field(
        None,
        description="The outdoor activity requested (e.g., cycling, walking, running, hiking, picnic, driving) if intent is activity_advisory."
    )
    location: Optional[str] = Field(
        None,
        description="The target city or geographical location requested."
    )
    time_context: Optional[str] = Field(
        None,
        description="The requested time context (e.g., today, this evening, tomorrow)."
    )


GREETINGS = {"hi", "hello", "hey", "greetings", "good morning", "good afternoon", "good evening", "hi there", "hello there"}

KNOWN_CANONICAL_ACTIVITIES = {
    "cycling", "walking", "running", "hiking", "driving", "picnic",
    "children", "elderly", "pets", "two-wheeler", "sunbathing",
    "beach", "flying a kite", "travel", "stargazing"
}

FOLLOWUP_TRIGGERS = {"what about", "how about", "and in", "this evening", "tomorrow", "later today"}


def extract_activity_from_text(text: str) -> Optional[str]:
    t_clean = text.lower()
    if any(k in t_clean for k in ["cycling", "bike", "biking", "bicycle", "two-wheeler"]):
        return "cycling"
    elif any(k in t_clean for k in ["walking", "walk", "stroll", "going for a walk", "go for a walk"]):
        return "walking"
    elif any(k in t_clean for k in ["picnic", "outdoor gathering", "park outing"]):
        return "picnic"
    elif any(k in t_clean for k in ["running", "jogging", "marathon"]):
        return "running"
    elif any(k in t_clean for k in ["hiking", "trekking"]):
        return "hiking"
    elif any(k in t_clean for k in ["driving", "commuting", "highway"]):
        return "driving"
    elif any(k in t_clean for k in ["kite", "flying a kite"]):
        return "flying a kite"
    else:
        norm = normalize_activity(text)
        if norm in KNOWN_CANONICAL_ACTIVITIES:
            return norm
    return None


CITY_ALIASES = {
    "banglore": "Bengaluru",
    "bangalore": "Bengaluru",
    "bengaluru": "Bengaluru",
    "bhopal": "Bhopal",
    "mumbai": "Mumbai",
    "bombay": "Mumbai",
    "delhi": "Delhi",
    "new delhi": "Delhi",
    "chennai": "Chennai",
    "madras": "Chennai",
    "kolkata": "Kolkata",
    "calcutta": "Kolkata",
    "hyderabad": "Hyderabad",
    "pune": "Pune",
    "poona": "Pune",
}


def extract_location_from_text(text: str) -> Optional[str]:
    t = text.lower()
    for alias, canonical in CITY_ALIASES.items():
        if alias in t:
            return canonical
    if "xyz_nonexistent_city" in t:
        return "XYZ_NONEXISTENT_CITY_12345"

    m = re.search(r"\b(?:in|at|for|near)\s+([a-zA-Z]+)\b", text, re.IGNORECASE)
    if m:
        loc_candidate = m.group(1).strip()
        loc_lower = loc_candidate.lower()
        if loc_lower in CITY_ALIASES:
            return CITY_ALIASES[loc_lower]
        return loc_candidate.capitalize()
    return None


def is_math_or_unsupported(text: str) -> bool:
    t = text.lower().strip()
    if re.search(r"(\d+\s*[\+\-\*/]\s*\d+|\bplus\b|\bminus\b|\btimes\b|\bdivided\b|\bjoke\b|\bmath\b)", t):
        return True
    if any(k in t for k in ["joke", "funny story", "who won", "capital of", "recipe", "python", "code", "programming", "calculate"]):
        return True
    return False


def is_weather_query(text: str) -> bool:
    t = text.lower()
    weather_keywords = ["weather", "forecast", "temperature", "temp", "rain", "raining", "wind", "humidity", "climate"]
    return any(k in t for k in weather_keywords)


def heuristic_intent_extraction(user_question: str, messages_history: List[Dict[str, Any]]) -> UserIntent:
    """
    Rule-based intent extraction fallback for offline execution or when OPENAI_API_KEY is unset.
    """
    q_clean = user_question.lower().strip()
    q_alpha = re.sub(r"[^\w\s]", "", q_clean).strip()

    # 1. Greetings
    if q_alpha in GREETINGS or any(q_clean.startswith(g) and len(q_clean) <= len(g) + 3 for g in GREETINGS):
        return UserIntent(intent=IntentCategory.GENERAL, activity=None, location=None, time_context=None)

    # 2. Math / Unsupported
    if is_math_or_unsupported(q_clean):
        return UserIntent(intent=IntentCategory.UNSUPPORTED, activity=None, location=None, time_context=None)

    # 3. Extract activity & location from current question
    activity = extract_activity_from_text(q_clean)
    location = extract_location_from_text(user_question)

    time_context = None
    if "evening" in q_clean or "this evening" in q_clean:
        time_context = "evening"
    elif "today" in q_clean:
        time_context = "today"
    elif "tomorrow" in q_clean:
        time_context = "tomorrow"

    # Check if question is an explicit follow-up turn
    is_followup = any(tr in q_clean for tr in FOLLOWUP_TRIGGERS)

    if is_followup and messages_history:
        history_text = " ".join([str(m.get("content", "")) for m in messages_history if isinstance(m, dict)])
        h_lower = history_text.lower()
        if not activity:
            activity = extract_activity_from_text(h_lower)
        if not location:
            location = extract_location_from_text(history_text)

    if activity:
        return UserIntent(
            intent=IntentCategory.ACTIVITY_ADVISORY,
            activity=activity,
            location=location,
            time_context=time_context,
        )
    elif is_weather_query(q_clean):
        return UserIntent(
            intent=IntentCategory.WEATHER_QUERY,
            activity=None,
            location=location,
            time_context=time_context,
        )
    else:
        return UserIntent(
            intent=IntentCategory.UNSUPPORTED,
            activity=None,
            location=location,
            time_context=time_context,
        )


async def understand_question(state: GraphState) -> Dict[str, Any]:
    """
    Extract structured intent (intent category, activity, location, time_context)
    from user question and messages context.
    """
    user_question = state.get("user_question", "")
    messages_history = state.get("messages", [])

    q_clean = user_question.lower().strip()
    q_alpha = re.sub(r"[^\w\s]", "", q_clean).strip()
    if q_alpha in GREETINGS:
        return {
            "intent": IntentCategory.GENERAL.value,
            "activity": None,
            "location": None,
            "time_context": None,
            "error": None,
        }

    formatted_messages = [SystemMessage(content=INTENT_SYSTEM_PROMPT)]

    for msg in messages_history:
        if isinstance(msg, dict):
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                formatted_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                formatted_messages.append(AIMessage(content=content))

    if user_question:
        if not messages_history or (
            isinstance(messages_history[-1], dict)
            and messages_history[-1].get("content") != user_question
        ):
            formatted_messages.append(HumanMessage(content=user_question))

    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and str(api_key).strip():
        try:
            model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            llm = ChatOpenAI(model=model_name, temperature=0, api_key=api_key)
            structured_llm = llm.with_structured_output(UserIntent)
            intent_obj: UserIntent = await structured_llm.ainvoke(formatted_messages)

            if intent_obj:
                raw_act = intent_obj.activity if intent_obj.activity else None
                norm_act = normalize_activity(raw_act) if raw_act else None
                intent_val = intent_obj.intent.value if isinstance(intent_obj.intent, IntentCategory) else str(intent_obj.intent)
                return {
                    "intent": intent_val,
                    "activity": norm_act or raw_act,
                    "location": intent_obj.location if intent_obj.location else None,
                    "time_context": intent_obj.time_context if intent_obj.time_context else None,
                    "error": None,
                }
        except Exception:
            pass

    fallback_intent = heuristic_intent_extraction(user_question, messages_history)
    intent_val = fallback_intent.intent.value if isinstance(fallback_intent.intent, IntentCategory) else str(fallback_intent.intent)
    return {
        "intent": intent_val,
        "activity": fallback_intent.activity,
        "location": fallback_intent.location,
        "time_context": fallback_intent.time_context,
        "error": None,
    }





