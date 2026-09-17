from backend.app.models.weather import WeatherData
from backend.app.policies.loader import SOPLoader
from backend.app.policies.engine import PolicyEngine

def main():
    print("==================================================")
    print("   Weather Advisory Support Bot - Policy Engine   ")
    print("==================================================")
    
    # Load SOPs from YAML
    sops = SOPLoader.load_from_file("backend/app/policies/sops.yaml")
    engine = PolicyEngine(sops)
    print(f"Loaded {len(sops)} SOP policies successfully.\n")

    # Sample Demonstration Query
    activity = "cycling"
    weather = WeatherData(
        temperature_2m=30.0,
        wind_speed_10m=45.0,
        precipitation=2.0,
        precipitation_probability=60.0,
        uv_index=7.0
    )

    print(f"Query Activity : '{activity}'")
    print(f"Live Weather   : {weather.model_dump()}")
    print("-" * 50)

    result = engine.evaluate(activity=activity, weather=weather)

    print(f"Total Matches  : {len(result.matched_sops)}")
    for idx, match in enumerate(result.matched_sops, 1):
        print(f"  Match {idx}: [{match.sop.id}] {match.sop.name} (Severity: {match.sop.severity.value})")
        print(f"           Matched Conditions: {match.matched_conditions}")

    print("-" * 50)
    if result.selected_sop:
        sel = result.selected_sop
        print("SELECTED SOP (Highest Severity & Tie-Broken):")
        print(f"  SOP ID    : {sel.sop.id}")
        print(f"  Name      : {sel.sop.name}")
        print(f"  Category  : {sel.sop.category}")
        print(f"  Severity  : {sel.sop.severity.value}")
        print(f"  Advice    : {sel.sop.advice.strip()}")
    else:
        print("No applicable SOP matched.")
    print("==================================================")

if __name__ == "__main__":
    main()
