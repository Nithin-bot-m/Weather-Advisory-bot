"""
SOP matching node for Weather Advisory Support Bot.
"""
from typing import Dict, Any, List, Optional
import os
from backend.app.state import GraphState
from backend.app.models.weather import WeatherData
from backend.app.policies.loader import SOPLoader
from backend.app.policies.engine import PolicyEngine

# Global or lazy policy engine instance
_POLICY_ENGINE: Optional[PolicyEngine] = None


def get_policy_engine() -> PolicyEngine:
    global _POLICY_ENGINE
    if _POLICY_ENGINE is None:
        yaml_path = os.getenv("SOP_YAML_PATH", "backend/app/policies/sops.yaml")
        sops = SOPLoader.load_from_file(yaml_path)
        _POLICY_ENGINE = PolicyEngine(sops)
    return _POLICY_ENGINE


async def match_sops(state: GraphState) -> Dict[str, Any]:
    """
    Evaluate activity and weather against deterministic SOP policy engine.
    """
    activity = state.get("activity")
    weather_dict = state.get("weather")

    if not activity or not weather_dict:
        return {
            "matching_sops": [],
            "selected_sop": None,
            "evaluated_sop": None,
        }

    try:
        weather_obj = WeatherData(**weather_dict)
        engine = get_policy_engine()
        result = engine.evaluate(activity=activity, weather=weather_obj)

        matching_sops_list = []
        for matched in result.matched_sops:
            matching_sops_list.append({
                "id": matched.sop.id,
                "name": matched.sop.name,
                "category": matched.sop.category,
                "severity": matched.sop.severity.value if hasattr(matched.sop.severity, "value") else str(matched.sop.severity),
                "advice": matched.sop.advice,
                "matched_conditions": matched.matched_conditions,
            })

        selected_sop_dict = None
        if result.selected_sop:
            sel = result.selected_sop
            selected_sop_dict = {
                "id": sel.sop.id,
                "name": sel.sop.name,
                "category": sel.sop.category,
                "severity": sel.sop.severity.value if hasattr(sel.sop.severity, "value") else str(sel.sop.severity),
                "advice": sel.sop.advice,
                "situational_override": getattr(sel.sop, "situational_override", False),
                "matched_conditions": sel.matched_conditions,
            }

        evaluated_sop_dict = None
        if result.evaluated_sop:
            ev = result.evaluated_sop
            evaluated_sop_dict = {
                "id": ev.id,
                "name": ev.name,
                "category": ev.category,
                "severity": ev.severity.value if hasattr(ev.severity, "value") else str(ev.severity),
                "advice": ev.advice,
            }

        return {
            "matching_sops": matching_sops_list,
            "selected_sop": selected_sop_dict,
            "evaluated_sop": evaluated_sop_dict,
        }
    except Exception as exc:
        return {
            "error": f"SOP evaluation failed: {str(exc)}",
            "matching_sops": [],
            "selected_sop": None,
            "evaluated_sop": None,
        }


def route_after_sop(state: GraphState) -> str:
    """
    Conditional router after SOP matching.
    Returns:
    - 'situational_override' if selected_sop is a situational override policy
    - 'matched' if either selected_sop or evaluated_sop is present
    - 'no_match' if no SOP matches
    """
    selected_sop = state.get("selected_sop")
    if selected_sop and (selected_sop.get("situational_override") or selected_sop.get("category") == "situational_weather"):
        return "situational_override"
    if selected_sop or state.get("evaluated_sop"):
        return "matched"
    return "no_match"


