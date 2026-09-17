"""
Evaluation and unit tests for Weather Advisory Support Bot.
"""
import pytest
import asyncio
import httpx
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.weather import fetch_weather_forecast, FORECAST_API_URL
from backend.app.services.geocoding import search_location, GEOCODING_API_URL


client = TestClient(app)


def test_placeholder():
    assert True


def test_fastapi_root_and_docs():
    res_root = client.get("/")
    assert res_root.status_code == 200
    assert res_root.json() == {"message": "Weather Advisory Bot API is running"}

    res_docs = client.get("/docs")
    assert res_docs.status_code == 200


def test_open_meteo_forecast_connectivity():
    # Test Bhopal coordinates (lat: 23.25, lon: 77.41)
    params = {
        "latitude": 23.25,
        "longitude": 77.41,
        "current": "temperature_2m,wind_speed_10m,precipitation,precipitation_probability,uv_index",
    }
    with httpx.Client() as c:
        response = c.get(FORECAST_API_URL, params=params)
        # Verify Open-Meteo forecast API is reachable (status 200 or 429 rate-limited)
        assert response.status_code in (200, 429)
        data = response.json()
        if response.status_code == 200:
            assert "current" in data
            current = data["current"]
            assert "temperature_2m" in current
            assert "wind_speed_10m" in current
        else:
            assert data.get("error") is True or "reason" in data


def test_open_meteo_geocoding_connectivity():
    data = asyncio.run(search_location("Bhopal"))
    assert "results" in data
    assert len(data["results"]) > 0
    first_result = data["results"][0]
    assert "name" in first_result
    assert first_result["name"].lower() == "bhopal"
    assert "latitude" in first_result
    assert "longitude" in first_result
