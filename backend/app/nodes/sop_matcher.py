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
        }

    try:
        weather_obj = WeatherData(**weather_dict)
        engine = get_policy_engine()
        result = engine.evaluate(activity=activity, weather=weather_obj)

        if not result.has_match or not result.selected_sop:
            return {
                "matching_sops": [],
                "selected_sop": None,
            }

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

        sel = result.selected_sop
        selected_sop_dict = {
            "id": sel.sop.id,
            "name": sel.sop.name,
            "category": sel.sop.category,
            "severity": sel.sop.severity.value if hasattr(sel.sop.severity, "value") else str(sel.sop.severity),
            "advice": sel.sop.advice,
            "matched_conditions": sel.matched_conditions,
        }

        return {
            "matching_sops": matching_sops_list,
            "selected_sop": selected_sop_dict,
        }
    except Exception as exc:
        return {
            "error": f"SOP evaluation failed: {str(exc)}",
            "matching_sops": [],
            "selected_sop": None,
        }


def route_after_sop(state: GraphState) -> str:
    """
    Conditional router after SOP matching.
    Returns 'matched' if selected_sop is present, otherwise 'no_match'.
    """
    if state.get("selected_sop"):
        return "matched"
    return "no_match"

