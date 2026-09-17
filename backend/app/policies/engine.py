from typing import List, Optional, Tuple, Dict, Any, Union
from pydantic import BaseModel, Field
from backend.app.models.weather import WeatherData
from backend.app.models.sop import SOP, MatchedSOP, SeverityLevel

SEVERITY_ORDER = {
    SeverityLevel.HIGH: 3,
    SeverityLevel.MEDIUM: 2,
    SeverityLevel.LOW: 1,
}


class PolicyEvaluationResult(BaseModel):
    activity: str = Field(..., description="The query activity evaluated")
    weather: Any = Field(..., description="The weather data used for evaluation")
    matched_sops: List[MatchedSOP] = Field(
        default_factory=list, description="All SOPs that matched activity and weather conditions"
    )
    selected_sop: Optional[MatchedSOP] = Field(
        None, description="The highest severity SOP selected after tie-breaking"
    )

    @property
    def has_match(self) -> bool:
        return self.selected_sop is not None


class PolicyEngine:
    """
    100% Deterministic Policy Evaluation Engine.
    Evaluates live WeatherData against dynamically loaded SOP policies without LLM dependency.
    """

    def __init__(self, sops: Optional[List[SOP]] = None):
        self.sops: List[SOP] = sops if sops is not None else []

    def load_policies(self, sops: List[SOP]) -> None:
        """Dynamically load or replace active SOP policies."""
        self.sops = list(sops)

    def match_activity(self, sop: SOP, activity: str) -> bool:
        """
        Deterministic case-insensitive activity matching.
        Matches if input activity equals or is contained within any configured SOP activity keyword.
        """
        if not activity or not activity.strip():
            return False

        norm_act = activity.lower().strip()
        for target_act in sop.activities:
            target_norm = target_act.lower().strip()
            # Match exact string, or substring match (e.g. "cycling" in "bike cycling")
            if norm_act == target_norm or target_norm in norm_act or norm_act in target_norm:
                return True
        return False

    def evaluate_conditions(self, sop: SOP, weather: Any) -> Tuple[bool, Dict[str, float]]:
        """
        Evaluates weather data against SOP conditions.
        - ALL conditions must pass (AND logic).
        - If a required weather field is missing/None, evaluation FAILS (no fabrication of missing data).
        """
        matched_values: Dict[str, float] = {}

        if not sop.conditions:
            return False, {}

        for field_name, threshold in sop.conditions.items():
            # Support both object attributes and dictionary keys
            weather_val = None
            if isinstance(weather, dict):
                weather_val = weather.get(field_name)
            elif hasattr(weather, field_name):
                weather_val = getattr(weather, field_name)

            if weather_val is None:
                # Never fabricate or assume missing weather values
                return False, {}

            try:
                val_float = float(weather_val)
            except (ValueError, TypeError):
                return False, {}

            # Check min threshold
            if threshold.min is not None and val_float < threshold.min:
                return False, {}

            # Check max threshold
            if threshold.max is not None and val_float > threshold.max:
                return False, {}

            matched_values[field_name] = val_float

        return True, matched_values

    def evaluate(self, activity: str, weather: Any) -> PolicyEvaluationResult:
        """
        Evaluates all loaded SOPs for the given activity and weather data.
        - Retains all matching SOPs.
        - Selects highest severity (high > medium > low).
        - Tie-breaking: SOP ID ascending for equal severity.
        """
        matched_results: List[MatchedSOP] = []

        for sop in self.sops:
            if self.match_activity(sop, activity):
                is_match, matched_values = self.evaluate_conditions(sop, weather)
                if is_match:
                    matched_results.append(
                        MatchedSOP(sop=sop, matched_conditions=matched_values)
                    )

        if not matched_results:
            return PolicyEvaluationResult(
                activity=activity,
                weather=weather,
                matched_sops=[],
                selected_sop=None,
            )

        # Sort matches by severity descending (high > medium > low), then SOP ID ascending
        def sort_key(matched: MatchedSOP):
            severity_rank = SEVERITY_ORDER.get(matched.sop.severity, 0)
            return (-severity_rank, matched.sop.id)

        sorted_matches = sorted(matched_results, key=sort_key)
        selected = sorted_matches[0]

        return PolicyEvaluationResult(
            activity=activity,
            weather=weather,
            matched_sops=sorted_matches,
            selected_sop=selected,
        )
