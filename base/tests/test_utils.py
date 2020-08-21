from base.actions import utils


def test_risk_level():
    # cough longer than two weeks
    data = {"symptoms_cough": "yes gt 2weeks"}
    risk = utils.get_risk_level(data)
    assert risk == "high"

    # cough less than two weeks, with one or more symptoms and exposure
    data = {
        "symptoms_cough": "yes lt 2weeks",
        "symptoms_fever": "yes",
        "exposure": "yes",
    }
    risk = utils.get_risk_level(data)
    assert risk == "high"

    # cough less than two weeks, with one or more symptoms and maybe exposure
    data = {
        "symptoms_cough": "yes lt 2weeks",
        "symptoms_fever": "yes",
        "exposure": "not sure",
    }
    risk = utils.get_risk_level(data)
    assert risk == "high"

    # cough less than two weeks, no other symptoms, no exposure
    data = {"symptoms_cough": "yes lt 2weeks", "exposure": "no"}
    risk = utils.get_risk_level(data)
    assert risk == "moderate_with_cough"

    # no cough, one or more other symptoms
    data = {"symptoms_cough": "no", "symptoms_fever": "yes"}
    risk = utils.get_risk_level(data)
    assert risk == "high"

    # no cough, with exposure
    data = {"symptoms_cough": "no", "exposure": "yes"}
    risk = utils.get_risk_level(data)
    assert risk == "moderate_without_cough"

    # no cough, no symptoms, no exposure
    data = {"symptoms_cough": "no", "exposure": "no"}
    risk = utils.get_risk_level(data)
    assert risk == "low"
