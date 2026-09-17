import pytest
from backend.app.models.weather import WeatherData
from backend.app.policies.loader import SOPLoader
from backend.app.policies.engine import PolicyEngine


@pytest.fixture
def engine():
    sops = SOPLoader.load_from_file("backend/app/policies/sops.yaml")
    return PolicyEngine(sops)


def test_1_high_wind_cycling_matches(engine):
    # Test 1: High wind cycling (wind = 45) -> SOP-001 (high severity) matches
    weather = WeatherData(
        temperature_2m=25.0,
        wind_speed_10m=45.0,
        precipitation=0.0,
        precipitation_probability=10.0,
        uv_index=5.0,
    )
    result = engine.evaluate(activity="cycling", weather=weather)
    assert result.has_match
    assert result.selected_sop is not None
    assert result.selected_sop.sop.id == "SOP-001"
    assert result.selected_sop.sop.severity == "high"
    assert "wind_speed_10m" in result.selected_sop.matched_conditions
    assert result.selected_sop.matched_conditions["wind_speed_10m"] == 45.0


def test_2_wind_below_threshold(engine):
    # Test 2: Wind = 25 -> SOP-001 does not match
    weather = WeatherData(
        temperature_2m=25.0,
        wind_speed_10m=25.0,
        precipitation=0.0,
        precipitation_probability=10.0,
        uv_index=5.0,
    )
    result = engine.evaluate(activity="cycling", weather=weather)
    # Wind is 25, SOP-001 requires min 40
    sop_ids = [m.sop.id for m in result.matched_sops]
    assert "SOP-001" not in sop_ids


def test_3_high_temperature_children_heat(engine):
    # Test 3: Children in park with temperature = 36 -> SOP-006 matches
    weather = WeatherData(
        temperature_2m=36.0,
        wind_speed_10m=12.0,
        precipitation=0.0,
        precipitation_probability=5.0,
        uv_index=7.0,
    )
    result = engine.evaluate(activity="children park", weather=weather)
    assert result.has_match
    assert result.selected_sop.sop.id == "SOP-006"
    assert result.selected_sop.sop.severity == "high"


def test_4_picnic_good_conditions(engine):
    # Test 4: Picnic with good weather (temp=25, wind=10, precip_prob=10) -> SOP-009 matches
    weather = WeatherData(
        temperature_2m=25.0,
        wind_speed_10m=10.0,
        precipitation=0.0,
        precipitation_probability=10.0,
        uv_index=5.0,
    )
    result = engine.evaluate(activity="picnic", weather=weather)
    assert result.has_match
    sop_ids = [m.sop.id for m in result.matched_sops]
    assert "SOP-009" in sop_ids


def test_5_picnic_poor_conditions(engine):
    # Test 5: Picnic with high wind=40 and precip_prob=80 -> SOP-009 does not match
    weather = WeatherData(
        temperature_2m=25.0,
        wind_speed_10m=40.0,
        precipitation=5.0,
        precipitation_probability=80.0,
        uv_index=3.0,
    )
    result = engine.evaluate(activity="picnic", weather=weather)
    sop_ids = [m.sop.id for m in result.matched_sops]
    assert "SOP-009" not in sop_ids


def test_6_multiple_sops_severity_and_tiebreaking(engine):
    # Test 6: Cycling with wind = 45 and UV = 9
    # Matches SOP-001 (high severity wind) and SOP-011 (medium severity UV)
    weather = WeatherData(
        temperature_2m=30.0,
        wind_speed_10m=45.0,
        precipitation=0.0,
        precipitation_probability=10.0,
        uv_index=9.0,
    )
    result = engine.evaluate(activity="cycling", weather=weather)
    assert len(result.matched_sops) >= 2
    sop_ids = [m.sop.id for m in result.matched_sops]
    assert "SOP-001" in sop_ids
    assert "SOP-011" in sop_ids
    # High severity (SOP-001) selected over medium severity (SOP-011)
    assert result.selected_sop.sop.id == "SOP-001"
    assert result.selected_sop.sop.severity == "high"


def test_7_unsupported_activity_returns_no_match(engine):
    # Test 7: Activity "flying a kite" -> zero applicable SOPs
    weather = WeatherData(
        temperature_2m=22.0,
        wind_speed_10m=15.0,
        precipitation=0.0,
        precipitation_probability=10.0,
        uv_index=4.0,
    )
    result = engine.evaluate(activity="flying a kite", weather=weather)
    assert not result.has_match
    assert len(result.matched_sops) == 0
    assert result.selected_sop is None


def test_8_missing_weather_attribute():
    # Test 8: Custom Weather object missing an attribute required by SOP
    class PartialWeather:
        temperature_2m = 30.0
        wind_speed_10m = None  # Explicitly missing/None

    sops = SOPLoader.load_from_file("backend/app/policies/sops.yaml")
    eng = PolicyEngine(sops)
    result = eng.evaluate(activity="cycling", weather=PartialWeather())
    # Should not fabricate value, evaluation fails for SOP requiring wind_speed_10m
    sop_ids = [m.sop.id for m in result.matched_sops]
    assert "SOP-001" not in sop_ids


def test_11_dynamic_sop_addition():
    # Test 11: Dynamic SOP addition without changing engine.py code
    yaml_with_13th_sop = """
sops:
  - id: SOP-013
    category: recreation
    name: Stargazing Night Sky Warning
    severity: high
    activities:
      - stargazing
      - night sky
      - telescope
    conditions:
      precipitation_probability:
        min: 50
    advice: >
      High cloud cover / rain probability (>= 50%) obstructs night sky visibility for stargazing.
"""
    new_sops = SOPLoader.load_from_yaml_string(yaml_with_13th_sop)
    engine_dynamic = PolicyEngine(new_sops)

    weather = WeatherData(
        temperature_2m=15.0,
        wind_speed_10m=5.0,
        precipitation=2.0,
        precipitation_probability=75.0,
        uv_index=0.0,
    )
    result = engine_dynamic.evaluate(activity="stargazing", weather=weather)
    assert result.has_match
    assert result.selected_sop.sop.id == "SOP-013"
    assert result.selected_sop.sop.name == "Stargazing Night Sky Warning"


def test_cycling_phrasing_variations_normalize(engine):
    # Regression test for Step 4 phrasing variations
    variations = [
        "cycle",
        "cycling",
        "bicycle",
        "bicycling",
        "bike ride",
        "ride my bike",
        "riding a bike",
        "take my bicycle out",
        "taking my bicycle out for a ride",
        "bicycle ride",
    ]
    weather = WeatherData(
        temperature_2m=25.0,
        wind_speed_10m=45.0,  # High wind triggers SOP-001
        precipitation=0.0,
        precipitation_probability=10.0,
        uv_index=5.0,
    )
    for var in variations:
        res = engine.evaluate(activity=var, weather=weather)
        assert res.evaluated_sop is not None, f"Failed evaluated_sop for variation: {var}"
        assert res.evaluated_sop.id == "SOP-001", f"Failed SOP-001 mapping for variation: {var}"
        assert res.has_match, f"Failed hazard match for variation: {var}"
        assert res.selected_sop.sop.id == "SOP-001"


def test_cycling_safe_weather_distinction(engine):
    # Situation B: SOP exists, but weather is safe (wind = 15 km/h < 40 km/h)
    weather = WeatherData(
        temperature_2m=25.0,
        wind_speed_10m=15.0,
        precipitation=0.0,
        precipitation_probability=10.0,
        uv_index=3.0,
    )
    res = engine.evaluate(activity="bicycling", weather=weather)
    assert res.selected_sop is None  # No threshold breach
    assert res.evaluated_sop is not None  # SOP-001 evaluated
    assert res.evaluated_sop.id == "SOP-001"


def test_unrelated_activity_no_sop_match(engine):
    # Situation A: No SOP exists for activity
    weather = WeatherData(
        temperature_2m=25.0,
        wind_speed_10m=15.0,
        precipitation=0.0,
        precipitation_probability=10.0,
        uv_index=3.0,
    )
    res = engine.evaluate(activity="flying a kite", weather=weather)
    assert res.selected_sop is None
    assert res.evaluated_sop is None

