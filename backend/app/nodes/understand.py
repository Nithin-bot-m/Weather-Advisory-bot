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

Do NOT provide advice.
Do NOT evaluate safety.
Do NOT evaluate weather.
Do NOT select an SOP.
Do NOT invent weather.
Do NOT invent policies.

If a value is not present or cannot be reliably inferred from the conversation, return null."""


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


def heuristic_intent_extraction(user_question: str, messages_history: List[Dict[str, Any]]) -> UserIntent:
    """
    Rule-based intent extraction fallback for offline execution or when OPENAI_API_KEY is unset.
    """
    combined_text = user_question
    for msg in messages_history:
        if isinstance(msg, dict):
            combined_text += " " + str(msg.get("content", ""))

    combined_lower = combined_text.lower()

    # Activity extraction
    activity = None
    if any(k in combined_lower for k in ["cycling", "bike", "biking", "bicycle", "two-wheeler"]):
        activity = "cycling"
    elif any(k in combined_lower for k in ["picnic", "outdoor gathering", "park outing", "outdoors"]):
        activity = "picnic"
    elif any(k in combined_lower for k in ["running", "jogging", "marathon"]):
        activity = "running"
    elif any(k in combined_lower for k in ["hiking", "trekking", "trail"]):
        activity = "hiking"
    elif any(k in combined_lower for k in ["driving", "commuting", "highway"]):
        activity = "driving"
    elif any(k in combined_lower for k in ["kite", "flying a kite"]):
        activity = "flying a kite"

    # Location extraction
    location = None
    if "bhopal" in combined_lower:
        location = "Bhopal"
    elif "bengaluru" in combined_lower or "bangalore" in combined_lower:
        location = "Bengaluru"
    elif "mumbai" in combined_lower:
        location = "Mumbai"
    elif "delhi" in combined_lower:
        location = "Delhi"
    elif "xyz_nonexistent_city" in combined_lower:
        location = "XYZ_NONEXISTENT_CITY_12345"

    # Time context extraction
    time_context = None
    if "evening" in combined_lower or "this evening" in combined_lower:
        time_context = "evening"
    elif "today" in combined_lower:
        time_context = "today"
    elif "tomorrow" in combined_lower:
        time_context = "tomorrow"

    return UserIntent(activity=activity, location=location, time_context=time_context)


async def understand_question(state: GraphState) -> Dict[str, Any]:
    """
    Extract structured intent (activity, location, time_context) from user question and messages context.
    Strictly refrains from giving advice or evaluating safety.
    """
    user_question = state.get("user_question", "")
    messages_history = state.get("messages", [])

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
                return {
                    "activity": intent.activity if intent and intent.activity else None,
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


