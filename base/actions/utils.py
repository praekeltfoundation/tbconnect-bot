from typing import Any, Dict, List, Text


def get_risk_level(data: Dict[Any, Any]) -> Text:
    if data.get("exposure") == "yes":
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


def get_risk_templates(risk: Text, data: Dict[Any, Any]) -> List:
    templates = []
    if data.get("exposure") == "not sure" and risk == "low":
        templates.append("utter_risk_low_unknown_exposure")
    else:
        templates.append(f"utter_risk_{risk}")

    templates.append("utter_keywords")

    if risk != "low":
        templates.append("utter_follow_up_request")

    return templates
