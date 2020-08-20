from typing import Any, Dict, Text


def get_risk_level(data: Dict[Any, Any]) -> Text:
    symptoms = 0
    for key, value in data.items():
        if "symptoms_" in key and value == "yes":
            symptoms += 1

    cough = data.get("symptoms_cough") != "no"
    if cough:
        if data.get("symptoms_cough") == "yes gt 2weeks":
            return "high"
        elif symptoms >= 1 or data.get("exposure") != "no":
            return "high"
        else:
            return "moderate_with_cough"

    if symptoms >= 1:
        return "high"
    elif data.get("exposure") != "no":
        return "moderate_without_cough"

    return "low"
