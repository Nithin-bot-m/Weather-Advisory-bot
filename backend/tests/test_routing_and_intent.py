"""
Comprehensive test suite verifying routing architecture, intent classification, policy selection, and session isolation.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.graph import graph
from backend.app.state import GraphState
from backend.app.session import session_manager
from backend.app.models.weather import WeatherData

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_sessions():
    """Clear session memory before and after every test."""
    session_manager.clear_all()
    yield
    session_manager.clear_all()


@pytest.fixture
def mock_weather_data():
    """Mock weather service to avoid external Open-Meteo HTTP calls."""
    with patch("backend.app.nodes.weather.fetch_weather_forecast", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = WeatherData(
            temperature_2m=25.0,
            wind_speed_10m=45.0,  # High wind triggers SOP-001 for cycling
            precipitation=0.0,
            precipitation_probability=10.0,
            uv_index=5.0,
        )
        yield mock_fetch


def test_1_cycle_in_bhopal(mock_weather_data):
    """
    TEST 1: Input: 'Can I cycle in Bhopal?'
    Expected: intent = activity_advisory, location = Bhopal, activity = cycling
    """
    res = client.post("/chat", json={"session_id": "test-1", "message": "Can I cycle in Bhopal?"})
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "activity_advisory"
    assert data["location"] == "Bhopal"
    assert data["activity"] == "cycling"
    assert data["selected_sop"] is not None
    assert data["selected_sop"]["id"] == "SOP-001"


def test_2_cycle_in_bangalore(mock_weather_data):
    """
    TEST 2: Input: 'Can I cycle in Bangalore?'
    Expected: intent = activity_advisory, location = Bangalore/Bengaluru, activity = cycling
    """
    res = client.post("/chat", json={"session_id": "test-2", "message": "Can I cycle in Bangalore?"})
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "activity_advisory"
    assert data["location"] in ["Bangalore", "Bengaluru"]
    assert data["activity"] == "cycling"
    assert data["selected_sop"] is not None
    assert data["selected_sop"]["id"] == "SOP-001"


def test_3_walk_in_bangalore(mock_weather_data):
    """
    TEST 3: Input: 'Can I walk in Bangalore?'
    Expected: intent = activity_advisory, location = Bangalore/Bengaluru, activity = walking
    Must NOT select cycling-specific policy SOP-001 simply because it is the first SOP.
    """
    res = client.post("/chat", json={"session_id": "test-3", "message": "Can I walk in Bangalore?"})
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "activity_advisory"
    assert data["location"] in ["Bangalore", "Bengaluru"]
    assert data["activity"] == "walking"

    selected = data.get("selected_sop")
    if selected:
        assert selected["id"] != "SOP-001", "Walking must NOT select SOP-001 (Strong Wind Cycling Warning)"


def test_4_weather_in_bangalore(mock_weather_data):
    """
    TEST 4: Input: 'What is the weather in Bangalore?'
    Expected: intent = weather_query, location = Bangalore/Bengaluru
    Must NOT invoke cycling policy.
    """
    res = client.post("/chat", json={"session_id": "test-4", "message": "What is the weather in Bangalore?"})
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "weather_query"
    assert data["location"] in ["Bangalore", "Bengaluru"]
    assert data["activity"] is None
    assert data["selected_sop"] is None
    assert "SOP-001" not in data.get("response", "")
    assert "Cycling" not in data.get("response", "")


def test_5_weather_in_delhi(mock_weather_data):
    """
    TEST 5: Input: 'What is the weather in Delhi?'
    Expected: intent = weather_query, location = Delhi
    Must NOT invoke cycling policy.
    """
    res = client.post("/chat", json={"session_id": "test-5", "message": "What is the weather in Delhi?"})
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "weather_query"
    assert data["location"] == "Delhi"
    assert data["activity"] is None
    assert data["selected_sop"] is None
    assert "SOP-001" not in data.get("response", "")


def test_6_greeting():
    """
    TEST 6: Input: 'Hello'
    Expected: intent = general
    Must NOT call weather API.
    """
    with patch("backend.app.nodes.weather.fetch_weather_forecast") as mock_weather:
        res = client.post("/chat", json={"session_id": "test-6", "message": "Hello"})
        assert res.status_code == 200
        data = res.json()
        assert data["intent"] == "general"
        assert mock_weather.call_count == 0  # Weather API never called
        assert data["selected_sop"] is None


def test_7_math_question():
    """
    TEST 7: Input: 'What is 2 + 2?'
    Expected: intent = unsupported
    Must NOT call weather API. Must NOT invoke policy engine.
    """
    with patch("backend.app.nodes.weather.fetch_weather_forecast") as mock_weather:
        res = client.post("/chat", json={"session_id": "test-7", "message": "What is 2 + 2?"})
        assert res.status_code == 200
        data = res.json()
        assert data["intent"] == "unsupported"
        assert mock_weather.call_count == 0  # Weather API never called
        assert data["selected_sop"] is None
        assert "SOP-001" not in data.get("response", "")
        assert "Bhopal" not in data.get("response", "")


def test_8_tell_me_a_joke():
    """
    TEST 8: Input: 'Tell me a joke'
    Expected: intent = unsupported
    Must NOT invoke weather API or policy engine.
    """
    with patch("backend.app.nodes.weather.fetch_weather_forecast") as mock_weather:
        res = client.post("/chat", json={"session_id": "test-8", "message": "Tell me a joke"})
        assert res.status_code == 200
        data = res.json()
        assert data["intent"] == "unsupported"
        assert mock_weather.call_count == 0
        assert data["selected_sop"] is None
        assert "SOP-001" not in data.get("response", "")


def test_9_state_leakage_sequential(mock_weather_data):
    """
    TEST 9 — STATE LEAKAGE:
    Request 1: 'Can I cycle in Bhopal?'
    Request 2: 'What is the weather in Delhi?'
    Request 3: 'Can I walk in Bangalore?'
    Verify that each request uses its own intent/location/activity.
    """
    session_id = "test-session-leakage"

    # Request 1
    res1 = client.post("/chat", json={"session_id": session_id, "message": "Can I cycle in Bhopal?"})
    d1 = res1.json()
    assert d1["intent"] == "activity_advisory"
    assert d1["location"] == "Bhopal"
    assert d1["activity"] == "cycling"
    assert d1["selected_sop"] is not None and d1["selected_sop"]["id"] == "SOP-001"

    # Request 2
    res2 = client.post("/chat", json={"session_id": session_id, "message": "What is the weather in Delhi?"})
    d2 = res2.json()
    assert d2["intent"] == "weather_query"
    assert d2["location"] == "Delhi"
    assert d2["activity"] is None
    assert d2["selected_sop"] is None
    assert "SOP-001" not in d2.get("response", "")

    # Request 3
    res3 = client.post("/chat", json={"session_id": session_id, "message": "Can I walk in Bangalore?"})
    d3 = res3.json()
    assert d3["intent"] == "activity_advisory"
    assert d3["location"] in ["Bangalore", "Bengaluru"]
    assert d3["activity"] == "walking"
    selected = d3.get("selected_sop")
    if selected:
        assert selected["id"] != "SOP-001"


def test_10_state_leakage_session_reset(mock_weather_data):
    """
    TEST 10 — SESSION RESET LEAKAGE:
    Request 1: 'Can I cycle in Bhopal?'
    Reset session.
    Request 2: 'What is the weather in Mumbai?'
    Verify Bhopal does not leak into the second request.
    """
    session_id = "test-session-reset-leak"

    # Request 1
    res1 = client.post("/chat", json={"session_id": session_id, "message": "Can I cycle in Bhopal?"})
    assert res1.json()["location"] == "Bhopal"

    # Reset session
    reset_res = client.post(f"/session/{session_id}/reset")
    assert reset_res.status_code == 200

    # Request 2
    res2 = client.post("/chat", json={"session_id": session_id, "message": "What is the weather in Mumbai?"})
    d2 = res2.json()
    assert d2["intent"] == "weather_query"
    assert d2["location"] == "Mumbai"
    assert d2["activity"] is None
    assert d2["selected_sop"] is None
    assert "Bhopal" not in d2.get("response", "")
    assert "SOP-001" not in d2.get("response", "")
