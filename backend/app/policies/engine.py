from typing import List, Optional, Tuple, Dict, Any, Union
from pydantic import BaseModel, Field
from backend.app.models.weather import WeatherData
from backend.app.models.sop import SOP, MatchedSOP, SeverityLevel
from backend.app.policies.normalization import normalize_activity

SEVERITY_ORDER = {
    SeverityLevel.HIGH: 3,
    SeverityLevel.MEDIUM: 2,
    SeverityLevel.LOW: 1,
}


class PolicyEvaluationResult(BaseModel):
    activity: str = Field(..., description="The query activity evaluated")
    weather: Any = Field(..., description="The weather data used for evaluation")
    activity_sops: List[SOP] = Field(
        default_factory=list, description="All SOPs that matched the requested activity"
    )
    matched_sops: List[MatchedSOP] = Field(
        default_factory=list, description="All SOPs that matched activity and weather conditions"
    )
    selected_sop: Optional[MatchedSOP] = Field(
        None, description="The highest severity SOP selected after tie-breaking when conditions breach"
    )
    evaluated_sop: Optional[SOP] = Field(
        None, description="Primary SOP policy evaluated for this activity"
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
        Deterministic case-insensitive normalized activity matching.
        Matches if normalized input activity matches or relates to any configured SOP activity keyword.
        """
        if not activity or not str(activity).strip():
            return False

        norm_act = normalize_activity(activity)
        for target_act in sop.activities:
            target_norm = normalize_activity(target_act)
            if target_norm in ("all", "outdoor", "general", "situational") or norm_act == target_norm or target_norm in norm_act or norm_act in target_norm:
                return True
        return False

    def evaluate_conditions(self, sop: SOP, weather: Any) -> Tuple[bool, Dict[str, float]]:
        """
        Evaluates weather data against SOP conditions.
        - Supports numeric threshold mode (AND logic) and fuzzy suitability score mode.
        - If a required weather field is missing/None, evaluation FAILS (no fabrication of missing data).
        """
        matched_values: Dict[str, float] = {}

        if not sop.conditions:
            return False, {}

        # Handle fuzzy continuous evaluation if requested by SOP schema
        if getattr(sop, "eval_type", "numeric") == "fuzzy":
            scores: List[float] = []
            for field_name, threshold in sop.conditions.items():
                weather_val = None
                if isinstance(weather, dict):
                    weather_val = weather.get(field_name)
                elif hasattr(weather, field_name):
                    weather_val = getattr(weather, field_name)

                if weather_val is None:
                    return False, {}

                try:
                    val_float = float(weather_val)
                except (ValueError, TypeError):
                    return False, {}

                matched_values[field_name] = val_float

                # Compute continuous parameter comfort score between 0.0 and 1.0
                min_v = threshold.min
                max_v = threshold.max
                if min_v is not None and max_v is not None:
                    mid = (min_v + max_v) / 2.0
                    span = max((max_v - min_v) / 2.0, 1.0)
                    if min_v <= val_float <= max_v:
                        param_score = 1.0 - 0.3 * (abs(val_float - mid) / span)
                    elif val_float < min_v:
                        param_score = max(0.0, 0.7 - 0.7 * (min_v - val_float) / max(min_v, 1.0))
                    else:
                        param_score = max(0.0, 0.7 - 0.7 * (val_float - max_v) / max(max_v, 1.0))
                elif max_v is not None:
                    if val_float <= max_v:
                        param_score = 1.0 - 0.5 * (val_float / max(max_v, 1.0))
                    else:
                        param_score = max(0.0, 0.5 - 0.5 * (val_float - max_v) / max(max_v, 1.0))
                elif min_v is not None:
                    if val_float >= min_v:
                        param_score = 1.0
                    else:
                        param_score = max(0.0, val_float / max(min_v, 1.0))
                else:
                    param_score = 1.0

                scores.append(param_score)

            if not scores:
                return False, {}

            overall_suitability = sum(scores) / len(scores)
            matched_values["suitability_score"] = round(overall_suitability, 2)
            req_threshold = sop.suitability_threshold if sop.suitability_threshold is not None else 0.70
            return (overall_suitability >= req_threshold), matched_values

        # Standard numeric evaluation
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
        - Identifies all SOPs relevant to the activity (activity_sops).
        - Evaluates weather conditions for matching SOPs (matched_sops).
        - Situational override SOPs apply when their atmospheric conditions breach.
        - Selects highest priority match (situational override > high > medium > low).
        - Sets evaluated_sop to primary relevant activity SOP for traceability even when conditions do not breach.
        """
        activity_sops: List[SOP] = []
        matched_results: List[MatchedSOP] = []

        for sop in self.sops:
            is_override = getattr(sop, "situational_override", False)
            is_act_match = self.match_activity(sop, activity)

            if is_act_match and not is_override:
                activity_sops.append(sop)

            if is_act_match or is_override:
                is_condition_match, matched_values = self.evaluate_conditions(sop, weather)
                if is_condition_match:
                    matched_results.append(
                        MatchedSOP(sop=sop, matched_conditions=matched_values)
                    )

        # Determine primary evaluated SOP for the activity
        evaluated_sop: Optional[SOP] = None
        if activity_sops:
            # Sort activity SOPs by severity descending (high > medium > low), then SOP ID ascending
            sorted_activity_sops = sorted(
                activity_sops,
                key=lambda s: (
                    -SEVERITY_ORDER.get(s.severity, 0),
                    s.id,
                ),
            )
            evaluated_sop = sorted_activity_sops[0]

        if not matched_results:
            return PolicyEvaluationResult(
                activity=activity,
                weather=weather,
                activity_sops=activity_sops,
                matched_sops=[],
                selected_sop=None,
                evaluated_sop=evaluated_sop,
            )

        # Sort matches by situational override descending, then severity descending, then SOP ID ascending
        def sort_key(matched: MatchedSOP):
            override_flag = 1 if getattr(matched.sop, "situational_override", False) else 0
            severity_rank = SEVERITY_ORDER.get(matched.sop.severity, 0)
            return (-override_flag, -severity_rank, matched.sop.id)

        sorted_matches = sorted(matched_results, key=sort_key)
        selected = sorted_matches[0]

        return PolicyEvaluationResult(
            activity=activity,
            weather=weather,
            activity_sops=activity_sops,
            matched_sops=sorted_matches,
            selected_sop=selected,
            evaluated_sop=selected.sop if not evaluated_sop else evaluated_sop,
        )

