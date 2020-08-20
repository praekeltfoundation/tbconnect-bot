from base.actions import utils


def test_risk_level():
    # TODO: update this
    data = {"test": "no"}
    risk = utils.get_risk_level(data)
    assert risk == "high"
