import pytest
from backend.app.policies.loader import SOPLoader, SOPValidationError


def test_load_default_sops_yaml():
    sops = SOPLoader.load_from_file("backend/app/policies/sops.yaml")
    assert len(sops) >= 12
    categories = {sop.category for sop in sops}
    assert len(categories) >= 3
    severities = {sop.severity for sop in sops}
    assert "high" in severities
    assert "medium" in severities
    assert "low" in severities


def test_reject_duplicate_sop_ids():
    yaml_content = """
sops:
  - id: SOP-001
    category: outdoor_exercise
    name: First SOP
    severity: high
    activities: [cycling]
    conditions:
      wind_speed_10m: { min: 40 }
    advice: "Advice 1"
  - id: SOP-001
    category: outdoor_exercise
    name: Duplicate SOP
    severity: medium
    activities: [biking]
    conditions:
      wind_speed_10m: { min: 30 }
    advice: "Advice 2"
"""
    with pytest.raises(SOPValidationError) as excinfo:
        SOPLoader.load_from_yaml_string(yaml_content)
    assert "Duplicate SOP ID detected" in str(excinfo.value)


def test_reject_invalid_severity():
    yaml_content = """
sops:
  - id: SOP-999
    category: outdoor_exercise
    name: Extreme SOP
    severity: extreme
    activities: [running]
    conditions:
      temperature_2m: { min: 50 }
    advice: "Extreme heat"
"""
    with pytest.raises(SOPValidationError) as excinfo:
        SOPLoader.load_from_yaml_string(yaml_content)
    assert "validation failed" in str(excinfo.value).lower() or "input_value='extreme'" in str(excinfo.value)


def test_reject_malformed_yaml():
    yaml_content = "sops: [unclosed bracket"
    with pytest.raises(SOPValidationError) as excinfo:
        SOPLoader.load_from_yaml_string(yaml_content)
    assert "Malformed YAML syntax" in str(excinfo.value)
