import pytest
from pydantic import ValidationError
from backend.app.models.location import LocationData
from backend.app.models.weather import WeatherData


def test_location_data_valid():
    loc = LocationData(name="Bhopal", latitude=23.25, longitude=77.41, country="India")
    assert loc.name == "Bhopal"
    assert loc.latitude == 23.25
    assert loc.longitude == 77.41
    assert loc.country == "India"


def test_location_data_missing_required():
    with pytest.raises(ValidationError):
        LocationData(name="Bhopal")


def test_weather_data_valid():
    w = WeatherData(
        temperature_2m=31.4,
        wind_speed_10m=24.2,
        precipitation=0.0,
        precipitation_probability=20.0,
        uv_index=5.3,
    )
    assert w.temperature_2m == 31.4
    assert w.wind_speed_10m == 24.2
    assert w.precipitation == 0.0
    assert w.precipitation_probability == 20.0
    assert w.uv_index == 5.3


def test_weather_data_missing_field_raises():
    # Missing uv_index should raise ValidationError, never default silently
    with pytest.raises(ValidationError):
        WeatherData(
            temperature_2m=31.4,
            wind_speed_10m=24.2,
            precipitation=0.0,
            precipitation_probability=20.0,
        )
