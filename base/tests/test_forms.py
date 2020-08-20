import pytest
from rasa_sdk.events import Form, SlotSet
from rasa_sdk.executor import CollectingDispatcher

from base.actions.actions import TBCheckTermsForm
from base.tests import utils


class TestHealthCheckTermsForm:
    @pytest.mark.asyncio
    async def test_validate_terms(self):
        form = TBCheckTermsForm()
        dispatcher = CollectingDispatcher()

        tracker = utils.get_tracker_for_slot_from_intent(form, "terms", "affirm")
        events = await form.run(dispatcher=dispatcher, tracker=tracker, domain=None)
        assert form.required_slots(tracker) == ["terms"]
        assert events == [
            SlotSet("terms", "yes"),
            Form(None),
            SlotSet("requested_slot", None),
        ]

        tracker = utils.get_tracker_for_slot_from_intent(form, "terms", "more")
        events = await form.run(dispatcher=dispatcher, tracker=tracker, domain=None)
        assert events == [SlotSet("terms", None), SlotSet("requested_slot", "terms")]
