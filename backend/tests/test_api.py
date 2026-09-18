"""
Comprehensive unit and integration tests for FastAPI /chat API endpoints and session management.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.session import session_manager
from backend.app.nodes.understand import UserIntent
from backend.app.models.weather import WeatherData
from backend.app.services.weather import WeatherFetchError

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_sessions():
    """Clear in-memory session manager before every test."""
    session_manager.clear_all()
    yield
    session_manager.clear_all()


@pytest.fixture
def mock_openai_intent_cycling_bhopal():
    """Mock ChatOpenAI structured output returning cycling in Bhopal today."""
    with patch("backend.app.nodes.understand.ChatOpenAI") as mock_chat:
        mock_instance = MagicMock()
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(return_value=UserIntent(
            intent="activity_advisory",
            activity="cycling",
            location="Bhopal",
            time_context="today"
        ))
        mock_instance.with_structured_output = MagicMock(return_value=mock_structured)
        mock_chat.return_value = mock_instance
        yield mock_structured


@pytest.fixture
def mock_openai_intent_kite_bhopal():
    """Mock ChatOpenAI structured output returning flying a kite in Bhopal today."""
    with patch("backend.app.nodes.understand.ChatOpenAI") as mock_chat:
        mock_instance = MagicMock()
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(return_value=UserIntent(
            intent="activity_advisory",
            activity="flying a kite",
            location="Bhopal",
            time_context="today"
        ))
        mock_instance.with_structured_output = MagicMock(return_value=mock_structured)
        mock_chat.return_value = mock_instance
        yield mock_structured


@pytest.fixture
def mock_openai_intent_invalid_location():
    """Mock ChatOpenAI structured output returning activity in non-existent location."""
    with patch("backend.app.nodes.understand.ChatOpenAI") as mock_chat:
        mock_instance = MagicMock()
        mock_structured = MagicMock()
        mock_structured.ainvoke = AsyncMock(return_value=UserIntent(
            intent="activity_advisory",
            activity="cycling",
            location="XYZ_NONEXISTENT_CITY_12345",
            time_context="today"
        ))
        mock_instance.with_structured_output = MagicMock(return_value=mock_structured)
        mock_chat.return_value = mock_instance
        yield mock_structured


@pytest.fixture
def mock_weather_data():
    """Mock fetch_weather_forecast to return standard weather data avoiding 429 rate limiting."""
    with patch("backend.app.nodes.weather.fetch_weather_forecast", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = WeatherData(
            temperature_2m=25.0,
            wind_speed_10m=45.0,
            precipitation=0.0,
            precipitation_probability=10.0,
            uv_index=5.0,
        )
        yield mock_fetch


def test_fastapi_root_and_docs():
    """Test GET / and GET /docs availability."""
    res_root = client.get("/")
    assert res_root.status_code == 200
    assert res_root.json() == {"message": "Weather Advisory Bot API is running"}

    res_docs = client.get("/docs")
    assert res_docs.status_code == 200


def test_chat_validation():
    """Test validation errors for empty message or empty session_id (HTTP 422)."""
    # Empty message
    res_empty_msg = client.post("/chat", json={"session_id": "test-session", "message": "   "})
    assert res_empty_msg.status_code == 422

    # Empty session_id
    res_empty_session = client.post("/chat", json={"session_id": "", "message": "Hello"})
    assert res_empty_session.status_code == 422


def test_post_chat_success(mock_openai_intent_cycling_bhopal, mock_weather_data):
    """Test successful POST /chat request."""
    with patch("os.getenv", side_effect=lambda k, d=None: "mock-key" if k == "OPENAI_API_KEY" else d):
        payload = {
            "session_id": "demo-session-1",
            "message": "Would riding my bike in Bhopal be okay today?"
        }
        res = client.post("/chat", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["session_id"] == "demo-session-1"
        assert data["message"] == payload["message"]
        assert data["activity"] == "cycling"
        assert data["location"] == "Bhopal"
        assert data["resolved_location"] is not None
        assert data["weather"] is not None
        assert data["selected_sop"] is not None
        assert data["selected_sop"]["id"] == "SOP-001"
        assert data["error"] is None


def test_session_followup(mock_openai_intent_cycling_bhopal, mock_weather_data):
    """
    Test session context recovery across multiple turns.
    Request 1: Is it safe to cycle in Bhopal today?
    Request 2: What about this evening?
    """
    with patch("os.getenv", side_effect=lambda k, d=None: "mock-key" if k == "OPENAI_API_KEY" else d):
        session_id = "test-session-followup"

        # Turn 1
        res1 = client.post("/chat", json={"session_id": session_id, "message": "Is it safe to cycle in Bhopal today?"})
        assert res1.status_code == 200

        # Verify history saved
        history = session_manager.get_history(session_id)
        assert len(history) == 2  # user + assistant

        # Turn 2
        with patch("backend.app.nodes.understand.ChatOpenAI") as mock_chat2:
            mock_inst2 = MagicMock()
            mock_struct2 = MagicMock()
            mock_struct2.ainvoke = AsyncMock(return_value=UserIntent(
                intent="activity_advisory",
                activity="cycling",
                location="Bhopal",
                time_context="evening"
            ))
            mock_inst2.with_structured_output = MagicMock(return_value=mock_struct2)
            mock_chat2.return_value = mock_inst2

            res2 = client.post("/chat", json={"session_id": session_id, "message": "What about this evening?"})
            assert res2.status_code == 200
            data2 = res2.json()
            assert data2["activity"] == "cycling"
            assert data2["location"] == "Bhopal"
            assert data2["time_context"] == "evening"


def test_session_isolation(mock_openai_intent_cycling_bhopal, mock_weather_data):
    """Test that Session A and Session B maintain independent context histories."""
    with patch("os.getenv", side_effect=lambda k, d=None: "mock-key" if k == "OPENAI_API_KEY" else d):
        client.post("/chat", json={"session_id": "session-A", "message": "Can I cycle in Bhopal?"})
        client.post("/chat", json={"session_id": "session-B", "message": "Can I hike in Bengaluru?"})

        history_A = session_manager.get_history("session-A")
        history_B = session_manager.get_history("session-B")

        assert len(history_A) == 2
        assert len(history_B) == 2
        assert "Bhopal" in history_A[0]["content"]
        assert "Bengaluru" in history_B[0]["content"]


def test_session_reset(mock_openai_intent_cycling_bhopal, mock_weather_data):
    """Test POST /session/{session_id}/reset clearing session memory."""
    with patch("os.getenv", side_effect=lambda k, d=None: "mock-key" if k == "OPENAI_API_KEY" else d):
        session_id = "session-reset-test"

        client.post("/chat", json={"session_id": session_id, "message": "Can I cycle in Bhopal?"})
        assert len(session_manager.get_history(session_id)) == 2

        reset_res = client.post(f"/session/{session_id}/reset")
        assert reset_res.status_code == 200
        assert reset_res.json() == {"session_id": session_id, "message": "Session reset successfully"}

        assert len(session_manager.get_history(session_id)) == 0


def test_no_sop_api_test(mock_openai_intent_kite_bhopal, mock_weather_data):
    """Test query with an activity that has no applicable SOP policy."""
    with patch("os.getenv", side_effect=lambda k, d=None: "mock-key" if k == "OPENAI_API_KEY" else d):
        res = client.post("/chat", json={"session_id": "session-no-sop", "message": "Can I fly a kite in Bhopal today?"})
        assert res.status_code == 200
        data = res.json()
        assert data["selected_sop"] is None
        assert "don't have an applicable SOP" in data["response"]


def test_location_failure_api_test(mock_openai_intent_invalid_location):
    """Test handling of unresolvable location without fabricating weather."""
    with patch("os.getenv", side_effect=lambda k, d=None: "mock-key" if k == "OPENAI_API_KEY" else d):
        res = client.post("/chat", json={"session_id": "session-invalid-loc", "message": "Can I cycle in XYZ_NONEXISTENT_CITY_12345?"})
        assert res.status_code == 200
        data = res.json()
        assert data["error"] is not None
        assert "Failed to resolve location" in data["error"]
        assert data["weather"] is None
        assert data["selected_sop"] is None


def test_weather_failure_api_test(mock_openai_intent_cycling_bhopal):
    """Test handling of weather service failure."""
    with patch("os.getenv", side_effect=lambda k, d=None: "mock-key" if k == "OPENAI_API_KEY" else d), \
         patch("backend.app.nodes.weather.fetch_weather_forecast", side_effect=WeatherFetchError("Open-Meteo down")):
        res = client.post("/chat", json={"session_id": "session-weather-err", "message": "Can I cycle in Bhopal today?"})
        assert res.status_code == 200
        data = res.json()
        assert data["error"] is not None
        assert "Weather retrieval failed" in data["error"]
        assert data["selected_sop"] is None
