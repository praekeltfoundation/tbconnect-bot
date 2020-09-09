from typing import Any, Dict, Text


def get_risk_level(data: Dict[Any, Any]) -> Text:
    if data.get("exposure") != "no":
        return "high"

    symptoms = 0
    for key, value in data.items():
        if key == "symptoms_cough":
            continue

        if "symptoms_" in key and value == "yes":
            symptoms += 1

    if data.get("symptoms_cough") == "yes":
        return "moderate"
    elif symptoms >= 1:
        return "moderate"

    return "low"
