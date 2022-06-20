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
    templates = utils.get_risk_templates("low", data)
    assert templates == ["utter_risk_low", "utter_keywords"]

    data = {"exposure": "not sure"}
    templates = utils.get_risk_templates("high", data)
    assert templates == ["utter_risk_high", "utter_keywords", "utter_follow_up_request"]


def test_group_arm_templates():
    response = {
        "id": 12,
        "profile": {
            "location": "+40.20361+40.20361",
            "tbconnect_group_arm": "planning_prompt",
            "research_consent": None,
        },
        "created_by": "test",
        "msisdn": "27856454612",
    }
    templates, group_arm = utils.get_display_message_template(response)

    assert templates == ["utter_planning_prompt"]
    assert group_arm == "planning_prompt"


def test_extract_location_lng_lat():
    location = "+40.20361-29.30361"

    long, lat = utils.extract_location_long_lat(location)
    assert long == 40.2
    assert lat == -29.3


def test_build_clinic_list():
    data = {
        "locations": [
            {
                "address": "203 Mark Street",
                "code": 853642,
                "latitude": -27.873,
                "location": "POINT (26.68533 -27.87308)",
                "longitude": 26.68533,
                "name": "fs AM Kruger Clinic",
                "province": "Free State",
                "short_name": "AM Kruger Clinic",
            },
            {
                "address": "565 Vorster Street, Wesselsbron, 9680",
                "code": 897151,
                "latitude": -27.8362,
                "location": "POINT (26.3668 -27.8362)",
                "longitude": 26.3668,
                "name": "fs Albert Luthuli Memorial Clinic",
                "province": "Free State",
                "short_name": "Albert Luthuli Mem Clinic",
            },
            {
                "address": "4 Olifant Street",
                "code": 734833,
                "latitude": -27.7533,
                "location": "POINT (26.64478 -27.75332)",
                "longitude": 26.64478,
                "name": "fs Allanridge Clinic",
                "province": "Free State",
                "short_name": "Allaridge Clinic",
            },
        ],
    }
    clinic_list, original_clinic_list = utils.build_clinic_list(data)

    assert (
        clinic_list
        == "*1.* AM Kruger Clinic\n*2.* Albert Luthuli Mem Clinic\n*3.* Allaridge Clinic\n"
    )
    assert original_clinic_list == [
        "AM Kruger Clinic",
        "Albert Luthuli Mem Clinic",
        "Allaridge Clinic",
    ]
