"""
Activity normalization module for Weather Advisory Support Bot.
Normalizes natural language activity variations into canonical terms used by SOP policies.
"""
import re
from typing import Dict

# Dictionary mapping activity synonyms/variations to canonical terms
ACTIVITY_SYNONYMS: Dict[str, str] = {
    # Cycling / Biking variations
    "cycling": "cycling",
    "cycle": "cycling",
    "bicycling": "cycling",
    "bicycle": "cycling",
    "bike": "cycling",
    "biking": "cycling",
    "bike ride": "cycling",
    "riding a bike": "cycling",
    "ride my bike": "cycling",
    "riding my bike": "cycling",
    "take my bicycle out": "cycling",
    "taking my bicycle out": "cycling",
    "taking my bicycle out for a ride": "cycling",
    "bicycle ride": "cycling",
    "two-wheeler": "two-wheeler",
    "scooter": "two-wheeler",
    "motorcycle": "two-wheeler",

    # Running / Jogging variations
    "running": "running",
    "run": "running",
    "jogging": "running",
    "jog": "running",
    "marathon": "running",
    "sprint": "running",

    # Hiking / Trekking variations
    "hiking": "hiking",
    "hike": "hiking",
    "trekking": "hiking",
    "trek": "hiking",
    "trail walk": "hiking",
    "trail": "hiking",

    # Driving / Commuting variations
    "driving": "driving",
    "drive": "driving",
    "commuting": "driving",
    "commute": "driving",
    "travel": "travel",
    "highway driving": "driving",
    "road travel": "driving",

    # Picnic / Outdoor Gathering variations
    "picnic": "picnic",
    "outdoor gathering": "picnic",
    "outdoor leisure": "picnic",
    "park outing": "picnic",
    "park": "picnic",
    "sunbathing": "sunbathing",
    "beach": "beach",

    # Children play variations
    "children": "children",
    "kids": "children",
    "outdoor play": "children",
    "school play": "children",

    # Elderly walk variations
    "elderly": "elderly",
    "senior citizens": "elderly",
    "morning walk": "elderly",

    # Pet walk variations
    "pets": "pets",
    "dog walk": "pets",
    "pet walk": "pets",
    "animals": "pets",

    # Stargazing / Astronomy variations
    "stargazing": "stargazing",
    "night sky": "stargazing",
    "astronomy": "stargazing",
    "telescope": "stargazing",
}



def normalize_activity(activity: str) -> str:
    """
    Normalize an activity string into a clean canonical keyword form.
    Trims, lowers, removes non-alphanumeric boundaries, and maps known synonyms.
    """
    if not activity or not str(activity).strip():
        return ""

    raw = str(activity).lower().strip()
    raw_clean = re.sub(r"^[^\w]+|[^\w]+$", "", raw)

    # Direct match in synonym dictionary
    if raw_clean in ACTIVITY_SYNONYMS:
        return ACTIVITY_SYNONYMS[raw_clean]

    # Substring / phrase match in synonym dictionary (longest phrases first)
    sorted_synonyms = sorted(ACTIVITY_SYNONYMS.items(), key=lambda x: -len(x[0]))
    for phrase, canonical in sorted_synonyms:
        if phrase in raw_clean or (len(phrase) >= 4 and raw_clean in phrase):
            return canonical

    return raw_clean

