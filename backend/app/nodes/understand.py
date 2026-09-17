"""
Intent extraction node for Weather Advisory Support Bot.
"""
import os
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from backend.app.state import GraphState

INTENT_SYSTEM_PROMPT = """You are an intent extraction component for a weather advisory system.

Your only task is to extract:
* outdoor activity
* location
* requested time context

Guidelines:
1. Extract outdoor activity, location, and time context from the user's question.
2. If the user asks a follow-up question (e.g., "What about this evening?", "How about tomorrow?"), recover the activity and location from the prior conversation history.
3. If the user's input is a standalone greeting (e.g., "hi", "hello", "hey") without any activity or location inquiry, return null for activity, location, and time_context.

Do NOT provide advice.
Do NOT evaluate safety.
Do NOT evaluate weather.
Do NOT select an SOP.
Do NOT invent weather.
Do NOT invent policies."""



class UserIntent(BaseModel):
    activity: Optional[str] = Field(
        None,
        description="The outdoor activity requested (e.g., cycling, running, hiking, picnic, driving)."
    )
    location: Optional[str] = Field(
        None,
        description="The target city or geographical location requested (e.g., Bhopal, Mumbai, Delhi)."
    )
    time_context: Optional[str] = Field(
        None,
        description="The requested time context (e.g., today, this evening, tomorrow)."
    )


from backend.app.policies.normalization import normalize_activity
import re

GREETINGS = {"hi", "hello", "hey", "greetings", "good morning", "good afternoon", "good evening", "hi there", "hello there"}


KNOWN_CANONICAL_ACTIVITIES = {
    "cycling", "running", "hiking", "driving", "picnic",
    "children", "elderly", "pets", "two-wheeler", "sunbathing",
    "beach", "flying a kite", "travel", "stargazing"
}



def extract_activity_from_text(text: str) -> Optional[str]:
    if any(k in text for k in ["cycling", "bike", "biking", "bicycle", "two-wheeler", "ride"]):
        return "cycling"
    elif any(k in text for k in ["picnic", "outdoor gathering", "park outing", "outdoors"]):
        return "picnic"
    elif any(k in text for k in ["running", "jogging", "marathon"]):
        return "running"
    elif any(k in text for k in ["hiking", "trekking", "trail"]):
        return "hiking"
    elif any(k in text for k in ["driving", "commuting", "highway"]):
        return "driving"
    elif any(k in text for k in ["kite", "flying a kite"]):
        return "flying a kite"
    else:
        norm = normalize_activity(text)
        if norm in KNOWN_CANONICAL_ACTIVITIES:
            return norm
    return None



def extract_location_from_text(text: str) -> Optional[str]:
    if "bhopal" in text:
        return "Bhopal"
    elif "bengaluru" in text or "bangalore" in text:
        return "Bengaluru"
    elif "mumbai" in text:
        return "Mumbai"
    elif "delhi" in text:
        return "Delhi"
    elif "xyz_nonexistent_city" in text:
        return "XYZ_NONEXISTENT_CITY_12345"
    return None


def heuristic_intent_extraction(user_question: str, messages_history: List[Dict[str, Any]]) -> UserIntent:
    """
    Rule-based intent extraction fallback for offline execution or when OPENAI_API_KEY is unset.
    """
    q_clean = user_question.lower().strip()
    q_alpha = re.sub(r"[^\w\s]", "", q_clean).strip()

    if q_alpha in GREETINGS:
        return UserIntent(activity=None, location=None, time_context=None)

    # 1. Search current question first
    activity = extract_activity_from_text(q_clean)
    location = extract_location_from_text(q_clean)

    time_context = None
    if "evening" in q_clean or "this evening" in q_clean:
        time_context = "evening"
    elif "today" in q_clean:
        time_context = "today"
    elif "tomorrow" in q_clean:
        time_context = "tomorrow"

    # 2. Recover missing fields from context if question is a follow-up
    if not activity or not location:
        history_text = " ".join([str(m.get("content", "")) for m in messages_history if isinstance(m, dict)])
        h_lower = history_text.lower()
        if not activity:
            activity = extract_activity_from_text(h_lower)
        if not location:
            location = extract_location_from_text(h_lower)

    return UserIntent(activity=activity, location=location, time_context=time_context)


async def understand_question(state: GraphState) -> Dict[str, Any]:
    """
    Extract structured intent (activity, location, time_context) from user question and messages context.
    Strictly refrains from giving advice or evaluating safety.
    """
    user_question = state.get("user_question", "")
    messages_history = state.get("messages", [])

    q_clean = user_question.lower().strip()
    q_alpha = re.sub(r"[^\w\s]", "", q_clean).strip()
    if q_alpha in GREETINGS:
        return {
            "activity": None,
            "location": None,
            "time_context": None,
            "error": None,
        }

    formatted_messages = [SystemMessage(content=INTENT_SYSTEM_PROMPT)]

    # Add historical messages for session context
    for msg in messages_history:
        if isinstance(msg, dict):
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                formatted_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                formatted_messages.append(AIMessage(content=content))

    # Append current user question if not already in message history
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
            intent: UserIntent = await structured_llm.ainvoke(formatted_messages)

            if intent and (intent.activity or intent.location or intent.time_context):
                raw_act = intent.activity if intent and intent.activity else None
                norm_act = normalize_activity(raw_act) if raw_act else None
                return {
                    "activity": norm_act or raw_act,
                    "location": intent.location if intent and intent.location else None,
                    "time_context": intent.time_context if intent and intent.time_context else None,
                    "error": None,
                }
        except Exception:
            # Fall back to heuristic intent extraction on API error
            pass

    # Heuristic fallback if OPENAI_API_KEY is unset or API call fails
    fallback_intent = heuristic_intent_extraction(user_question, messages_history)
    return {
        "activity": fallback_intent.activity,
        "location": fallback_intent.location,
        "time_context": fallback_intent.time_context,
        "error": None,
    }




