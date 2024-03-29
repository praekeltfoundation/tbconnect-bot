from base.actions import utils


def test_risk_level():
    # No cough, no symptoms, not high risk
    data = {"symptoms_cough": "no", "exposure": "no"}
    risk = utils.get_risk_level(data)
    assert risk == "low"

    # No cough, 1+ symptoms, not high risk
    data = {"symptoms_cough": "no", "symptoms_fever": "yes", "exposure": "no"}
    risk = utils.get_risk_level(data)
    assert risk == "moderate"

    # No cough, no symptoms, high risk
    data = {"symptoms_cough": "no", "symptoms_fever": "no", "exposure": "yes"}
    risk = utils.get_risk_level(data)
    assert risk == "high"

    # No cough, 1+ symptom, high risk
    data = {"symptoms_cough": "no", "symptoms_fever": "yes", "exposure": "yes"}
    risk = utils.get_risk_level(data)
    assert risk == "high"

    # Cough, no symptoms, not high risk
    data = {"symptoms_cough": "yes", "symptoms_fever": "no", "exposure": "no"}
    risk = utils.get_risk_level(data)
    assert risk == "moderate"

    # Cough, 1+ symptoms, not high risk
    data = {"symptoms_cough": "yes", "symptoms_fever": "yes", "exposure": "no"}
    risk = utils.get_risk_level(data)
    assert risk == "moderate"

    # Cough, 1+ symptoms, high risk
    data = {"symptoms_cough": "yes", "symptoms_fever": "yes", "exposure": "yes"}
    risk = utils.get_risk_level(data)
    assert risk == "high"

    # Cough, no symptoms, high risk
    data = {"symptoms_cough": "yes", "symptoms_fever": "no", "exposure": "yes"}
    risk = utils.get_risk_level(data)
    assert risk == "high"

    # No cough, no symptoms, unknown exposure
    data = {"symptoms_cough": "no", "symptoms_fever": "no", "exposure": "not sure"}
    risk = utils.get_risk_level(data)
    assert risk == "low"


def test_risk_template():
    data = {"exposure": "not sure"}
    templates = utils.get_risk_templates("low", data)
    assert templates == ["utter_risk_low_unknown_exposure", "utter_keywords"]

    data = {"exposure": "no"}
    templates = utils.get_risk_templates("low", data, None)
    assert templates == ["utter_risk_low", "utter_keywords"]

    data = {"exposure": "not sure"}
    templates = utils.get_risk_templates("high", data)
    assert templates == ["utter_risk_high", "utter_keywords", "utter_follow_up_request"]

    data = {"exposure": "no"}
    templates = utils.get_risk_templates("low", data, activation="tb_study_a")
    assert templates == ["utter_risk_low", "utter_keywords"]


def test_group_arm_templates():
    response = {
        "id": 12,
        "profile": {
            "location": "+40.20361+40.20361",
            "tbconnect_group_arm": "soft_commitment_plus",
            "research_consent": None,
        },
        "created_by": "test",
        "msisdn": "27856454612",
    }
    templates, group_arm = utils.get_display_message_template(response)

    assert templates == ["utter_soft_commitment_plus"]
    assert group_arm == "soft_commitment_plus"


def test_control_group_arm_templates():
    response = {
        "id": 12,
        "profile": {
            "location": None,
            "tbconnect_group_arm": "control",
            "research_consent": None,
        },
        "created_by": "test",
        "msisdn": "27856454612",
    }
    templates, group_arm = utils.get_display_message_template(response)

    assert templates == ["utter_control", "utter_keywords"]
    assert group_arm == "control"


def test_extract_location_lng_lat():
    location = "+40.20361-29.30361"

    long, lat = utils.extract_location_long_lat(location)
    assert long == 40.2
    assert lat == -29.3
