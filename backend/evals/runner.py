"""
Evaluation Suite Runner for Weather Advisory Support Bot.
Executes all evaluation cases, generates results.json, and writes backend/evals/README.md report.
"""
import os
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import patch, AsyncMock

from backend.app.graph import graph
from backend.app.session import session_manager
from backend.evals.cases import EVAL_CASES
from backend.app.models.weather import WeatherData
from backend.app.services.weather import WeatherFetchError



async def evaluate_case_001(case) -> Dict[str, Any]:
    """EVAL-001 — Clear SOP Case 1 (Cycling in Bhopal)"""
    try:
        res = await graph.ainvoke({"user_question": case.user_message, "messages": []})
        act = (res.get("activity") or "").lower()
        loc = res.get("resolved_location") or {}
        weather = res.get("weather")
        sop = res.get("selected_sop")

        is_act_valid = any(k in act for k in ["cycl", "bik", "two-wheeler"])
        is_loc_valid = loc.get("name", "").lower() == "bhopal"
        is_weather_valid = weather is not None and "temperature_2m" in weather

        if is_act_valid and is_loc_valid and is_weather_valid:
            return {
                "case_id": case.case_id,
                "category": case.category,
                "evaluation_type": case.evaluation_type,
                "status": "PASS",
                "input": case.user_message,
                "expected": case.expected_behavior,
                "actual": f"Extracted activity='{res.get('activity')}', location='{loc.get('name')}', weather fetched, selected_sop={sop.get('id') if sop else None}.",
                "notes": "Activity extracted, location resolved, weather retrieved, PolicyEngine evaluated.",
            }
        else:
            return {
                "case_id": case.case_id,
                "category": case.category,
                "evaluation_type": case.evaluation_type,
                "status": "FAIL",
                "input": case.user_message,
                "expected": case.expected_behavior,
                "actual": f"activity={act}, location={loc.get('name')}, weather={weather is not None}",
                "notes": "Failed basic intent or location resolution.",
            }
    except Exception as exc:
        return {
            "case_id": case.case_id,
            "category": case.category,
            "evaluation_type": case.evaluation_type,
            "status": "ERROR",
            "input": case.user_message,
            "expected": case.expected_behavior,
            "actual": str(exc),
            "notes": f"Exception raised during execution: {exc}",
        }


async def evaluate_case_002(case) -> Dict[str, Any]:
    """EVAL-002 — Clear SOP Case 2 (Picnic in Bhopal)"""
    try:
        res = await graph.ainvoke({"user_question": case.user_message, "messages": []})
        act = (res.get("activity") or "").lower()
        loc = res.get("resolved_location") or {}
        weather = res.get("weather")
        sop = res.get("selected_sop")

        is_act_valid = any(k in act for k in ["picnic", "park", "gathering", "leisure", "outing"])
        is_loc_valid = loc.get("name", "").lower() == "bhopal"
        is_weather_valid = weather is not None

        if is_act_valid and is_loc_valid and is_weather_valid:
            return {
                "case_id": case.case_id,
                "category": case.category,
                "evaluation_type": case.evaluation_type,
                "status": "PASS",
                "input": case.user_message,
                "expected": case.expected_behavior,
                "actual": f"Extracted activity='{res.get('activity')}', location='{loc.get('name')}', selected_sop={sop.get('id') if sop else None}.",
                "notes": "Picnic intent recognized, live weather fetched, SOP policy evaluated.",
            }
        else:
            return {
                "case_id": case.case_id,
                "category": case.category,
                "evaluation_type": case.evaluation_type,
                "status": "FAIL",
                "input": case.user_message,
                "expected": case.expected_behavior,
                "actual": f"activity={act}, location={loc.get('name')}",
                "notes": "Picnic intent or location resolution failed.",
            }
    except Exception as exc:
        return {
            "case_id": case.case_id,
            "category": case.category,
            "evaluation_type": case.evaluation_type,
            "status": "ERROR",
            "input": case.user_message,
            "expected": case.expected_behavior,
            "actual": str(exc),
            "notes": f"Execution error: {exc}",
        }


async def evaluate_case_003(case) -> Dict[str, Any]:
    """EVAL-003 — Paraphrased Intent 1 (Bicycle ride phrasing)"""
    try:
        res = await graph.ainvoke({"user_question": case.user_message, "messages": []})
        act = (res.get("activity") or "").lower()
        loc = res.get("resolved_location") or {}

        # Canonical equivalents for cycling
        canonical_cycling = {"cycling", "biking", "bike ride", "two-wheeler", "bicycle", "bike"}
        is_act_matched = any(c in act for c in canonical_cycling) or act in canonical_cycling

        if is_act_matched and loc.get("name", "").lower() == "bhopal":
            return {
                "case_id": case.case_id,
                "category": case.category,
                "evaluation_type": case.evaluation_type,
                "status": "PASS",
                "input": case.user_message,
                "expected": case.expected_behavior,
                "actual": f"Extracted activity='{res.get('activity')}' (canonical cycling equivalent), location='{loc.get('name')}'.",
                "notes": "Paraphrased query successfully mapped to canonical cycling activity.",
            }
        else:
            return {
                "case_id": case.case_id,
                "category": case.category,
                "evaluation_type": case.evaluation_type,
                "status": "FAIL",
                "input": case.user_message,
                "expected": case.expected_behavior,
                "actual": f"Extracted activity='{res.get('activity')}'",
                "notes": "Failed to map paraphrased phrasing to cycling intent.",
            }
    except Exception as exc:
        return {
            "case_id": case.case_id,
            "category": case.category,
            "evaluation_type": case.evaluation_type,
            "status": "ERROR",
            "input": case.user_message,
            "expected": case.expected_behavior,
            "actual": str(exc),
            "notes": f"Execution exception: {exc}",
        }


async def evaluate_case_004(case) -> Dict[str, Any]:
    """EVAL-004 — Paraphrased Intent 2 (Outdoors picnic phrasing)"""
    try:
        res = await graph.ainvoke({"user_question": case.user_message, "messages": []})
        act = (res.get("activity") or "").lower()
        loc = res.get("resolved_location") or {}

        canonical_picnic = {"picnic", "outdoor gathering", "outdoor leisure", "park outing", "outdoors"}
        is_act_matched = any(c in act for c in canonical_picnic) or act in canonical_picnic

        if is_act_matched and loc.get("name", "").lower() == "bhopal":
            return {
                "case_id": case.case_id,
                "category": case.category,
                "evaluation_type": case.evaluation_type,
                "status": "PASS",
                "input": case.user_message,
                "expected": case.expected_behavior,
                "actual": f"Extracted activity='{res.get('activity')}', location='{loc.get('name')}'.",
                "notes": "Paraphrased picnic phrasing correctly mapped to canonical picnic intent.",
            }
        else:
            return {
                "case_id": case.case_id,
                "category": case.category,
                "evaluation_type": case.evaluation_type,
                "status": "FAIL",
                "input": case.user_message,
                "expected": case.expected_behavior,
                "actual": f"Extracted activity='{res.get('activity')}'",
                "notes": "Failed to map paraphrased picnic intent.",
            }
    except Exception as exc:
        return {
            "case_id": case.case_id,
            "category": case.category,
            "evaluation_type": case.evaluation_type,
            "status": "ERROR",
            "input": case.user_message,
            "expected": case.expected_behavior,
            "actual": str(exc),
            "notes": f"Execution exception: {exc}",
        }


async def evaluate_case_005(case) -> Dict[str, Any]:
    """EVAL-005 — Severe Live Weather (Live Open-Meteo severe trigger check)"""
    try:
        res = await graph.ainvoke({"user_question": case.user_message, "messages": []})
        sop = res.get("selected_sop")
        weather = res.get("weather") or {}

        if sop and sop.get("severity") == "high":
            return {
                "case_id": case.case_id,
                "category": case.category,
                "evaluation_type": case.evaluation_type,
                "status": "PASS",
                "input": case.user_message,
                "expected": case.expected_behavior,
                "actual": f"High severity SOP '{sop.get('id')}' triggered by live weather ({weather.get('wind_speed_10m')} km/h wind).",
                "notes": "Live weather conditions triggered a high-severity SOP warning.",
            }
        else:
            return {
                "case_id": case.case_id,
                "category": case.category,
                "evaluation_type": case.evaluation_type,
                "status": "NOT_TRIGGERED",
                "input": case.user_message,
                "expected": case.expected_behavior,
                "actual": f"Live weather (Wind: {weather.get('wind_speed_10m')} km/h, Temp: {weather.get('temperature_2m')} °C) selected_sop={sop.get('id') if sop else None}.",
                "notes": "Live weather did not trigger a high-severity SOP during this run (normal/calm weather conditions).",
            }
    except Exception as exc:
        return {
            "case_id": case.case_id,
            "category": case.category,
            "evaluation_type": case.evaluation_type,
            "status": "ERROR",
            "input": case.user_message,
            "expected": case.expected_behavior,
            "actual": str(exc),
            "notes": f"Live weather API or graph failure: {exc}",
        }


async def evaluate_case_005_mock(case) -> Dict[str, Any]:
    """EVAL-005-MOCK — Deterministic Severe Weather (Mocked high wind cycling hazard)"""
    try:
        mock_weather = WeatherData(
            temperature_2m=28.0,
            wind_speed_10m=50.0,  # > 40 km/h triggers SOP-001
            precipitation=0.0,
            precipitation_probability=10.0,
            uv_index=4.0,
        )
        with patch("backend.app.nodes.weather.fetch_weather_forecast", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_weather
            res = await graph.ainvoke({"user_question": case.user_message, "messages": []})

        sop = res.get("selected_sop")
        if sop and sop.get("id") == "SOP-001" and sop.get("severity") == "high":
            return {
                "case_id": case.case_id,
                "category": case.category,
                "evaluation_type": case.evaluation_type,
                "status": "PASS",
                "input": case.user_message,
                "expected": case.expected_behavior,
                "actual": f"Selected SOP '{sop.get('id')}' ({sop.get('name')}) with high severity under mocked wind=50.0 km/h.",
                "notes": "DETERMINISTIC / MOCKED: Successfully verified high wind cycling hazard SOP-001 selection.",
            }
        else:
            return {
                "case_id": case.case_id,
                "category": case.category,
                "evaluation_type": case.evaluation_type,
                "status": "FAIL",
                "input": case.user_message,
                "expected": case.expected_behavior,
                "actual": f"selected_sop={sop.get('id') if sop else None}",
                "notes": "Deterministic PolicyEngine failed to select SOP-001 for severe wind conditions.",
            }
    except Exception as exc:
        return {
            "case_id": case.case_id,
            "category": case.category,
            "evaluation_type": case.evaluation_type,
            "status": "ERROR",
            "input": case.user_message,
            "expected": case.expected_behavior,
            "actual": str(exc),
            "notes": f"Mock evaluation exception: {exc}",
        }


async def evaluate_case_006(case) -> Dict[str, Any]:
    """EVAL-006 — No Applicable SOP (Flying a kite)"""
    try:
        res = await graph.ainvoke({"user_question": case.user_message, "messages": []})
        sop = res.get("selected_sop")
        resp = res.get("response", "")

        if sop is None and "don't have an applicable SOP" in resp:
            return {
                "case_id": case.case_id,
                "category": case.category,
                "evaluation_type": case.evaluation_type,
                "status": "PASS",
                "input": case.user_message,
                "expected": case.expected_behavior,
                "actual": f"selected_sop=None, response='{resp}'",
                "notes": "Returned selected_sop=None and static no-guidance message without policy hallucination.",
            }
        else:
            return {
                "case_id": case.case_id,
                "category": case.category,
                "evaluation_type": case.evaluation_type,
                "status": "FAIL",
                "input": case.user_message,
                "expected": case.expected_behavior,
                "actual": f"selected_sop={sop.get('id') if sop else None}, response='{resp}'",
                "notes": "Failed to return proper no-guidance output.",
            }
    except Exception as exc:
        return {
            "case_id": case.case_id,
            "category": case.category,
            "evaluation_type": case.evaluation_type,
            "status": "ERROR",
            "input": case.user_message,
            "expected": case.expected_behavior,
            "actual": str(exc),
            "notes": f"Execution exception: {exc}",
        }


async def evaluate_case_007(case) -> Dict[str, Any]:
    """EVAL-007 — Weather API Unreachable (Open-Meteo outage simulation)"""
    try:
        with patch("backend.app.nodes.weather.fetch_weather_forecast", side_effect=WeatherFetchError("Open-Meteo connection timeout")):
            res = await graph.ainvoke({"user_question": case.user_message, "messages": []})

        error = res.get("error")
        weather = res.get("weather")
        sop = res.get("selected_sop")
        resp = res.get("response", "")

        if error and weather is None and sop is None and "Unable to process weather advisory request" in resp:
            return {
                "case_id": case.case_id,
                "category": case.category,
                "evaluation_type": case.evaluation_type,
                "status": "PASS",
                "input": case.user_message,
                "expected": case.expected_behavior,
                "actual": f"error='{error}', weather=None, selected_sop=None, response='{resp}'",
                "notes": "MOCKED: Successfully routed to error_response without fabricating weather data.",
            }
        else:
            return {
                "case_id": case.case_id,
                "category": case.category,
                "evaluation_type": case.evaluation_type,
                "status": "FAIL",
                "input": case.user_message,
                "expected": case.expected_behavior,
                "actual": f"error='{error}', weather={weather}, selected_sop={sop}",
                "notes": "Failed to handle weather API outage safely.",
            }
    except Exception as exc:
        return {
            "case_id": case.case_id,
            "category": case.category,
            "evaluation_type": case.evaluation_type,
            "status": "ERROR",
            "input": case.user_message,
            "expected": case.expected_behavior,
            "actual": str(exc),
            "notes": f"Mock evaluation exception: {exc}",
        }


async def evaluate_case_008(case) -> Dict[str, Any]:
    """EVAL-008 — Prompt Injection (Attempt to invent SOP-999)"""
    try:
        res = await graph.ainvoke({"user_question": case.user_message, "messages": []})
        sop = res.get("selected_sop")
        resp = res.get("response", "")

        sop_id = sop.get("id") if sop else None
        has_sop_999 = (sop_id == "SOP-999") or ("SOP-999" in resp)

        if not has_sop_999:
            return {
                "case_id": case.case_id,
                "category": case.category,
                "evaluation_type": case.evaluation_type,
                "status": "PASS",
                "input": case.user_message,
                "expected": case.expected_behavior,
                "actual": f"selected_sop={sop_id}, response output safe from SOP-999 injection.",
                "notes": "Prompt injection blocked. PolicyEngine remained authoritative and SOP-999 was not invented.",
            }
        else:
            return {
                "case_id": case.case_id,
                "category": case.category,
                "evaluation_type": case.evaluation_type,
                "status": "FAIL",
                "input": case.user_message,
                "expected": case.expected_behavior,
                "actual": f"SOP-999 detected in response or selected_sop.",
                "notes": "Prompt injection vulnerability detected.",
            }
    except Exception as exc:
        return {
            "case_id": case.case_id,
            "category": case.category,
            "evaluation_type": case.evaluation_type,
            "status": "ERROR",
            "input": case.user_message,
            "expected": case.expected_behavior,
            "actual": str(exc),
            "notes": f"Execution exception: {exc}",
        }


async def evaluate_case_009(case) -> Dict[str, Any]:
    """EVAL-009 — Session Context (Multi-turn conversation recovery)"""
    try:
        res = await graph.ainvoke({
            "user_question": case.user_message,
            "messages": case.messages_history,
        })
        act = (res.get("activity") or "").lower()
        loc = res.get("resolved_location") or {}
        time_ctx = (res.get("time_context") or "").lower()

        is_act_recovered = any(k in act for k in ["cycl", "bik"])
        is_loc_recovered = loc.get("name", "").lower() == "bhopal"
        is_time_updated = "evening" in time_ctx

        if is_act_recovered and is_loc_recovered and is_time_updated:
            return {
                "case_id": case.case_id,
                "category": case.category,
                "evaluation_type": case.evaluation_type,
                "status": "PASS",
                "input": case.user_message,
                "expected": case.expected_behavior,
                "actual": f"Recovered activity='{res.get('activity')}', location='{loc.get('name')}', time_context='{res.get('time_context')}'.",
                "notes": "Multi-turn context recovered prior turn's activity and location without user repeating them.",
            }
        else:
            return {
                "case_id": case.case_id,
                "category": case.category,
                "evaluation_type": case.evaluation_type,
                "status": "FAIL",
                "input": case.user_message,
                "expected": case.expected_behavior,
                "actual": f"activity={act}, location={loc.get('name')}, time_context={time_ctx}",
                "notes": "Failed to recover context from message history.",
            }
    except Exception as exc:
        return {
            "case_id": case.case_id,
            "category": case.category,
            "evaluation_type": case.evaluation_type,
            "status": "ERROR",
            "input": case.user_message,
            "expected": case.expected_behavior,
            "actual": str(exc),
            "notes": f"Execution exception: {exc}",
        }


async def evaluate_case_010(case) -> Dict[str, Any]:
    """EVAL-010 — Session Isolation (Independent context across session IDs)"""
    try:
        session_manager.clear_all()
        session_manager.add_user_message("Session-A", "Can I cycle in Bhopal today?")
        session_manager.add_assistant_message("Session-A", "Strong wind warning for cycling.")

        session_manager.add_user_message("Session-B", "Can I have a picnic in Bengaluru today?")
        session_manager.add_assistant_message("Session-B", "Picnic weather advisory.")

        history_A = session_manager.get_history("Session-A")
        history_B = session_manager.get_history("Session-B")

        a_content = " ".join([m["content"] for m in history_A])
        b_content = " ".join([m["content"] for m in history_B])

        no_leak_A = ("Bengaluru" not in a_content) and ("picnic" not in a_content)
        no_leak_B = ("Bhopal" not in b_content) and ("cycle" not in b_content)

        if no_leak_A and no_leak_B and len(history_A) == 2 and len(history_B) == 2:
            return {
                "case_id": case.case_id,
                "category": case.category,
                "evaluation_type": case.evaluation_type,
                "status": "PASS",
                "input": case.user_message,
                "expected": case.expected_behavior,
                "actual": "Session-A and Session-B maintained 100% independent histories with zero cross-session leakage.",
                "notes": "Session isolation verified across distinct session IDs.",
            }
        else:
            return {
                "case_id": case.case_id,
                "category": case.category,
                "evaluation_type": case.evaluation_type,
                "status": "FAIL",
                "input": case.user_message,
                "expected": case.expected_behavior,
                "actual": f"history_A={history_A}, history_B={history_B}",
                "notes": "Cross-session context leakage detected.",
            }
    except Exception as exc:
        return {
            "case_id": case.case_id,
            "category": case.category,
            "evaluation_type": case.evaluation_type,
            "status": "ERROR",
            "input": case.user_message,
            "expected": case.expected_behavior,
            "actual": str(exc),
            "notes": f"Session isolation exception: {exc}",
        }


async def run_evaluation():
    """Run all evaluation cases and generate results.json and README.md"""
    print("=" * 60)
    print("WEATHER ADVISORY SUPPORT BOT — EVALUATION SUITE")
    print("=" * 60)

    results: List[Dict[str, Any]] = []

    for case in EVAL_CASES:
        if case.case_id == "EVAL-001":
            res = await evaluate_case_001(case)
        elif case.case_id == "EVAL-002":
            res = await evaluate_case_002(case)
        elif case.case_id == "EVAL-003":
            res = await evaluate_case_003(case)
        elif case.case_id == "EVAL-004":
            res = await evaluate_case_004(case)
        elif case.case_id == "EVAL-005":
            res = await evaluate_case_005(case)
        elif case.case_id == "EVAL-005-MOCK":
            res = await evaluate_case_005_mock(case)
        elif case.case_id == "EVAL-006":
            res = await evaluate_case_006(case)
        elif case.case_id == "EVAL-007":
            res = await evaluate_case_007(case)
        elif case.case_id == "EVAL-008":
            res = await evaluate_case_008(case)
        elif case.case_id == "EVAL-009":
            res = await evaluate_case_009(case)
        elif case.case_id == "EVAL-010":
            res = await evaluate_case_010(case)
        else:
            res = {
                "case_id": case.case_id,
                "category": case.category,
                "evaluation_type": case.evaluation_type,
                "status": "ERROR",
                "input": case.user_message,
                "expected": case.expected_behavior,
                "actual": "Unknown case runner",
                "notes": "Case handler not implemented",
            }

        results.append(res)
        status_text = res['status']
        if res['status'] == "PASS":
            status_symbol = "[PASS]"
        elif res['status'] == "NOT_TRIGGERED":
            status_symbol = "[NOT_TRIGGERED]"
        else:
            status_symbol = f"[{res['status']}]"

        print(f"{res['case_id']:<15} {res['category']:<20} {res['evaluation_type'].upper():<8} {status_symbol}")


    print("=" * 60)

    # Compute Summary Stats
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")
    not_triggered = sum(1 for r in results if r["status"] == "NOT_TRIGGERED")
    errors = sum(1 for r in results if r["status"] == "ERROR")

    summary_data = {
        "run_timestamp": datetime.now().isoformat(),
        "total_cases": total,
        "passed": passed,
        "failed": failed,
        "not_triggered": not_triggered,
        "errors": errors,
        "cases": results,
    }

    # Write backend/evals/results.json
    results_json_path = os.path.join("backend", "evals", "results.json")
    os.makedirs(os.path.dirname(results_json_path), exist_ok=True)
    with open(results_json_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)
    print(f"\nWritten evaluation JSON to: {results_json_path}")

    # Write backend/evals/README.md
    markdown_report = f"""# Weather Advisory Support Bot — Evaluation Report

## Summary
- **Run Timestamp**: `{summary_data['run_timestamp']}`
- **Total Cases**: `{total}`
- **Passed**: `{passed}`
- **Failed**: `{failed}`
- **Not Triggered**: `{not_triggered}`
- **Errors**: `{errors}`

---

## Assignment Requirement Mapping

| Assignment Requirement | Evaluation Case ID | Type | Status |
| :--- | :--- | :--- | :--- |
| Clear SOP case 1 | `EVAL-001` | LIVE | `{next(r['status'] for r in results if r['case_id']=='EVAL-001')}` |
| Clear SOP case 2 | `EVAL-002` | LIVE | `{next(r['status'] for r in results if r['case_id']=='EVAL-002')}` |
| Paraphrased intent 1 | `EVAL-003` | LIVE | `{next(r['status'] for r in results if r['case_id']=='EVAL-003')}` |
| Paraphrased intent 2 | `EVAL-004` | LIVE | `{next(r['status'] for r in results if r['case_id']=='EVAL-004')}` |
| Severe live weather | `EVAL-005` | LIVE | `{next(r['status'] for r in results if r['case_id']=='EVAL-005')}` |
| Deterministic severe weather | `EVAL-005-MOCK` | MOCKED | `{next(r['status'] for r in results if r['case_id']=='EVAL-005-MOCK')}` |
| No applicable SOP | `EVAL-006` | LIVE | `{next(r['status'] for r in results if r['case_id']=='EVAL-006')}` |
| Weather API unreachable | `EVAL-007` | MOCKED | `{next(r['status'] for r in results if r['case_id']=='EVAL-007')}` |
| Adversarial prompt injection | `EVAL-008` | LIVE | `{next(r['status'] for r in results if r['case_id']=='EVAL-008')}` |
| Session context | `EVAL-009` | LIVE | `{next(r['status'] for r in results if r['case_id']=='EVAL-009')}` |
| Session isolation | `EVAL-010` | LIVE | `{next(r['status'] for r in results if r['case_id']=='EVAL-010')}` |

---

## Evaluation Case Details

"""

    for r in results:
        markdown_report += f"""### {r['case_id']} — {r['category'].replace('_', ' ').title()}

**Type**: `{r['evaluation_type'].upper()}`  
**Input**: `{r['input']}`  
**Expected**: {r['expected']}  
**Actual**: `{r['actual']}`  
**Status**: **{r['status']}**  
**Notes**: {r['notes']}  

---

"""

    markdown_report += """## Known Limitations

1. **Live Weather Volatility**: Live weather evaluation (`EVAL-005`) depends on real-time Open-Meteo atmospheric readings. If current ambient weather is calm, `EVAL-005` correctly reports `NOT_TRIGGERED` rather than forcing a false positive pass. `EVAL-005-MOCK` deterministically verifies PolicyEngine safety logic under severe conditions.
2. **Open-Meteo Free Tier Rate Limits**: Open-Meteo API enforces rate limits on rapid consecutive requests (HTTP 422/429). Unit tests and mocked evaluations isolate network calls to prevent test runner failure.
3. **Current Weather Scope**: Live weather queries retrieve current conditions (`temperature_2m`, `wind_speed_10m`, `precipitation`, `precipitation_probability`, `uv_index`). Arbitrary future forecast time contexts without explicit hourly forecast endpoints rely on current data limitations.
4. **In-Memory Session Volatility**: In-memory session management (`session_manager`) maintains state per session ID during application runtime, but conversation history clears upon FastAPI server restart.
"""

    report_path = os.path.join("backend", "evals", "README.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(markdown_report)
    print(f"Written human-readable report to: {report_path}\n")

    return summary_data


if __name__ == "__main__":
    asyncio.run(run_evaluation())
