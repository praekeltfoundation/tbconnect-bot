import json
from typing import Any, Dict, Optional, Text
from urllib.parse import urlencode

import pytest
import respx
from rasa_sdk import Tracker
from rasa_sdk.events import Form, SlotSet
from rasa_sdk.executor import CollectingDispatcher

import base.actions.actions
from base.actions.actions import (
    OptInForm,
    TBCheckForm,
    TBCheckProfileForm,
    TBCheckTermsForm,
)
from base.tests import utils


class TestTBCheckProfileForm:
    def get_tracker_for_text_slot_with_message(
        self, slot_name: Text, text: Text, msg: Optional[Dict[Text, Any]] = None
    ):
        msgs = [{"event": "user", "metadata": msg or dict()}]

        return Tracker(
            "default",
            {"requested_slot": slot_name},
            {"text": text},
            msgs,
            False,
            None,
            {},
            "action_listen",
        )

    @pytest.mark.asyncio
    async def test_validate_age(self):
        form = TBCheckProfileForm()
        dispatcher = CollectingDispatcher()

        tracker = utils.get_tracker_for_number_slot_with_value(form, "age", "1")
        events = await form.run(dispatcher=dispatcher, tracker=tracker, domain=None)
        assert events == [SlotSet("age", "<18"), SlotSet("requested_slot", "gender")]

        tracker = utils.get_tracker_for_number_slot_with_value(form, "age", "2")
        events = await form.run(dispatcher=dispatcher, tracker=tracker, domain=None)
        assert events == [SlotSet("age", "18-39"), SlotSet("requested_slot", "gender")]

        tracker = utils.get_tracker_for_number_slot_with_value(form, "age", "3")
        events = await form.run(dispatcher=dispatcher, tracker=tracker, domain=None)
        assert events == [SlotSet("age", "40-65"), SlotSet("requested_slot", "gender")]

        tracker = utils.get_tracker_for_number_slot_with_value(form, "age", "4")
        events = await form.run(dispatcher=dispatcher, tracker=tracker, domain=None)
        assert events == [SlotSet("age", ">65"), SlotSet("requested_slot", "gender")]

        tracker = utils.get_tracker_for_number_slot_with_value(form, "age", ["2", "39"])
        events = await form.run(dispatcher=dispatcher, tracker=tracker, domain=None)
        assert events == [SlotSet("age", None), SlotSet("requested_slot", "age")]

        tracker = utils.get_tracker_for_number_slot_with_value(
            form, "age", "not a number"
        )
        events = await form.run(dispatcher=dispatcher, tracker=tracker, domain=None)
        assert events == [SlotSet("age", None), SlotSet("requested_slot", "age")]

    @pytest.mark.asyncio
    async def test_validate_gender(self):
        form = TBCheckProfileForm()
        dispatcher = CollectingDispatcher()

        tracker = utils.get_tracker_for_number_slot_with_value(
            form, "gender", "1", {"age": "18-39"}
        )
        events = await form.run(dispatcher=dispatcher, tracker=tracker, domain=None)
        assert events == [
            SlotSet("gender", "MALE"),
            SlotSet("requested_slot", "province"),
        ]

        tracker = utils.get_tracker_for_number_slot_with_value(
            form, "gender", "2", {"age": "18-39"}
        )
        events = await form.run(dispatcher=dispatcher, tracker=tracker, domain=None)
        assert events == [
            SlotSet("gender", "FEMALE"),
            SlotSet("requested_slot", "province"),
        ]

        tracker = utils.get_tracker_for_number_slot_with_value(
            form, "gender", "3", {"age": "18-39"}
        )
        events = await form.run(dispatcher=dispatcher, tracker=tracker, domain=None)
        assert events == [
            SlotSet("gender", "OTHER"),
            SlotSet("requested_slot", "province"),
        ]

        tracker = utils.get_tracker_for_number_slot_with_value(
            form, "gender", "4", {"age": "18-39"}
        )
        events = await form.run(dispatcher=dispatcher, tracker=tracker, domain=None)
        assert events == [
            SlotSet("gender", "RATHER NOT SAY"),
            SlotSet("requested_slot", "province"),
        ]

    @pytest.mark.asyncio
    async def test_validate_province(self):
        form = TBCheckProfileForm()
        dispatcher = CollectingDispatcher()

        i = 1
        for p in ["ec", "fs", "gt", "nl", "lp", "mp", "nw", "nc", "wc"]:
            tracker = utils.get_tracker_for_number_slot_with_value(
                form, "province", str(i), {"age": "18-39", "gender": "MALE"}
            )
            events = await form.run(dispatcher=dispatcher, tracker=tracker, domain=None)
            assert events == [
                SlotSet("province", p),
                SlotSet("requested_slot", "location"),
            ]
            i += 1

    def test_format_location(self):
        """
        Ensures that the location pin is returned in ISO6709 format
        """
        assert TBCheckProfileForm.format_location(0, 0) == "+00+000/"
        assert TBCheckProfileForm.format_location(-1, -1) == "-01-001/"
        assert TBCheckProfileForm.format_location(1.234, -5.678) == "+01.234-005.678/"
        assert TBCheckProfileForm.format_location(-12.34, 123.456) == "-12.34+123.456/"
        assert (
            TBCheckProfileForm.format_location(51.481845, 7.216236)
            == "+51.481845+007.216236/"
        )

    @pytest.mark.asyncio
    async def test_validate_location_pin(self):
        """
        If a location pin is sent, it should be stored
        """
        form = TBCheckProfileForm()

        tracker = self.get_tracker_for_text_slot_with_message(
            "location",
            "",
            {"type": "location", "location": {"latitude": 1.23, "longitude": 4.56}},
        )
        events = await form.validate(CollectingDispatcher(), tracker, {})
        assert events == [
            SlotSet("location", "GPS: 1.23, 4.56"),
            SlotSet("location_coords", "+01.23+004.56/"),
            SlotSet("location_confirm", "yes"),
        ]

    @pytest.mark.asyncio
    async def test_validate_location_text(self):
        """
        If there's no google places API credentials, then just use the text
        """
        form = TBCheckProfileForm()

        tracker = self.get_tracker_for_text_slot_with_message("location", "Cape Town",)

        events = await form.validate(CollectingDispatcher(), tracker, {})
        assert events == [
            SlotSet("location", "Cape Town"),
        ]

    @respx.mock
    @pytest.mark.asyncio
    async def test_validate_location_google_places(self):
        """
        If there's are google places API credentials, then do a lookup
        """
        base.actions.actions.config.GOOGLE_PLACES_API_KEY = "test_key"
        querystring = urlencode(
            {
                "key": "test_key",
                "input": "Cape Town",
                "language": "en",
                "inputtype": "textquery",
                "fields": "formatted_address,geometry",
            }
        )
        request = respx.get(
            "https://maps.googleapis.com/maps/api/place/findplacefromtext/json?"
            f"{querystring}",
            content=json.dumps(
                {
                    "candidates": [
                        {
                            "formatted_address": "Cape Town, South Africa",
                            "geometry": {"location": {"lat": 1.23, "lng": 4.56}},
                        }
                    ]
                }
            ),
        )
        form = TBCheckProfileForm()

        tracker = self.get_tracker_for_text_slot_with_message("location", "Cape Town",)

        events = await form.validate(CollectingDispatcher(), tracker, {})
        assert events == [
            SlotSet("location", "Cape Town, South Africa"),
            SlotSet("city_location_coords", "+01.23+004.56/"),
        ]
        assert request.called

        base.actions.actions.config.GOOGLE_PLACES_API_KEY = None


class TestTBCheckTermsForm:
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


class TestTBCheckForm:
    @pytest.mark.asyncio
    async def test_validate_cough(self):
        form = TBCheckForm()
        dispatcher = CollectingDispatcher()

        tracker = utils.get_tracker_for_number_slot_with_value(
            form, "symptoms_cough", "1", {}
        )
        events = await form.run(dispatcher=dispatcher, tracker=tracker, domain=None)
        assert events == [
            SlotSet("symptoms_cough", "yes"),
            SlotSet("requested_slot", "symptoms_fever"),
        ]

        tracker = utils.get_tracker_for_number_slot_with_value(
            form, "symptoms_cough", "2", {}
        )
        events = await form.run(dispatcher=dispatcher, tracker=tracker, domain=None)
        assert events == [
            SlotSet("symptoms_cough", "no"),
            SlotSet("requested_slot", "symptoms_fever"),
        ]

    @respx.mock
    @pytest.mark.asyncio
    async def test_submit_to_healthconnect(self):
        """
        Submits the data to the eventstore in the correct format
        """
        base.actions.actions.config.HEALTHCONNECT_URL = "https://healthconnect"
        base.actions.actions.config.HEALTHCONNECT_TOKEN = "token"

        request = respx.post("https://healthconnect/v2/tbcheck/")

        form = TBCheckForm()
        dispatcher = CollectingDispatcher()
        tracker = utils.get_tracker_for_slot_from_intent(
            form,
            "tracing",
            "affirm",
            {
                "province": "wc",
                "age": "18-39",
                "symptoms_fever": "no",
                "symptoms_cough": "yes",
                "symptoms_sweat": "yes",
                "symptoms_weight": "yes",
                "exposure": "not sure",
                "tracing": "yes",
                "gender": "RATHER NOT SAY",
                "city_location_coords": "+1.2-3.4",
                "location_coords": "+3.4-1.2",
                "location": "Cape Town, South Africa",
            },
        )
        await form.submit(dispatcher, tracker, {})

        assert request.called
        [(request, response)] = request.calls
        data = json.loads(request.stream.body)
        assert data.pop("deduplication_id")
        assert data == {
            "msisdn": "+default",
            "source": "WhatsApp",
            "province": "ZA-WC",
            "city": "Cape Town, South Africa",
            "age": "18-40",
            "gender": "not_say",
            "cough": True,
            "fever": False,
            "sweat": True,
            "weight": True,
            "exposure": "not_sure",
            "tracing": True,
            "risk": "moderate",
            "location": "+3.4-1.2",
            "city_location": "+1.2-3.4",
        }

        base.actions.actions.config.HEALTHCONNECT_URL = None
        base.actions.actions.config.HEALTHCONNECT_TOKEN = None

    @respx.mock
    @pytest.mark.asyncio
    async def test_submit_to_healthconnect_duplicate_check(self):
        """
        Should ignore a duplicate contact error from healthconnect
        """
        base.actions.actions.config.HEALTHCONNECT_URL = "https://healthconnect"
        base.actions.actions.config.HEALTHCONNECT_TOKEN = "token"

        request = respx.post(
            "https://healthconnect/v2/tbcheck/",
            status_code=400,
            content={
                "deduplication_id": [
                    "tb check with this deduplication id already exists."
                ]
            },
        )

        form = TBCheckForm()
        dispatcher = CollectingDispatcher()
        tracker = utils.get_tracker_for_slot_from_intent(
            form,
            "tracing",
            "affirm",
            {
                "province": "wc",
                "age": "18-39",
                "symptoms_fever": "no",
                "symptoms_cough": "yes",
                "symptoms_sweat": "yes",
                "symptoms_weight": "yes",
                "exposure": "not sure",
                "tracing": "yes",
                "gender": "RATHER NOT SAY",
                "city_location_coords": "+1.2-3.4",
                "location_coords": "+3.4-1.2",
                "location": "Cape Town, South Africa",
            },
        )
        await form.submit(dispatcher, tracker, {})

        assert request.called
        # [(request, response)] = request.calls
        # data = json.loads(request.stream.body)

        base.actions.actions.config.HEALTHCONNECT_URL = None
        base.actions.actions.config.HEALTHCONNECT_TOKEN = None


class TestOptInForm:
    @respx.mock
    @pytest.mark.asyncio
    async def test_submit_to_healthconnect_low_risk(self):
        """
        Submits the data to the eventstore in the correct format
        """
        base.actions.actions.config.HEALTHCONNECT_URL = "https://healthconnect"
        base.actions.actions.config.HEALTHCONNECT_TOKEN = "token"

        request = respx.patch(
            "https://healthconnect/v2/healthcheckuserprofile/+default/"
        )

        form = OptInForm()
        dispatcher = CollectingDispatcher()
        tracker = utils.get_tracker_for_slot_from_intent(
            form,
            "terms",
            "opt_in",
            {
                "terms": "yes",
                "symptoms_fever": "no",
                "symptoms_cough": "no",
                "symptoms_sweat": "no",
                "symptoms_weight": "no",
                "exposure": "no",
                "tracing": "yes",
            },
        )
        await form.run(dispatcher, tracker, {})

        assert request.called
        [(request, response)] = request.calls
        data = json.loads(request.stream.body)
        assert data == {"data": {"follow_up_optin": True}}

        base.actions.actions.config.HEALTHCONNECT_URL = None
        base.actions.actions.config.HEALTHCONNECT_TOKEN = None

    @respx.mock
    @pytest.mark.asyncio
    async def test_submit_to_healthconnect(self):
        """
        Submits the data to the eventstore in the correct format
        """
        base.actions.actions.config.HEALTHCONNECT_URL = "https://healthconnect"
        base.actions.actions.config.HEALTHCONNECT_TOKEN = "token"

        request = respx.patch(
            "https://healthconnect/v2/healthcheckuserprofile/+default/"
        )

        form = OptInForm()
        dispatcher = CollectingDispatcher()
        tracker = utils.get_tracker_for_slot_from_intent(
            form, "terms", "opt_in", {"terms": "yes", "symptoms_cough": "yes"},
        )
        await form.run(dispatcher, tracker, {})

        assert request.called
        [(request, response)] = request.calls
        data = json.loads(request.stream.body)
        assert data == {
            "data": {"follow_up_optin": True, "synced_to_tb_rapidpro": False}
        }

        base.actions.actions.config.HEALTHCONNECT_URL = None
        base.actions.actions.config.HEALTHCONNECT_TOKEN = None

    @respx.mock
    @pytest.mark.asyncio
    async def test_submit_to_healthconnect_unknown_contact(self):
        """
        should not submit data if user has not completed a screening
        """
        base.actions.actions.config.HEALTHCONNECT_URL = "https://healthconnect"
        base.actions.actions.config.HEALTHCONNECT_TOKEN = "token"

        request = respx.patch(
            "https://healthconnect/v2/healthcheckuserprofile/+default/"
        )

        form = OptInForm()
        dispatcher = CollectingDispatcher()
        tracker = utils.get_tracker_for_slot_from_intent(form, "terms", "opt_in", {},)
        await form.run(dispatcher, tracker, {})

        assert not request.called

        base.actions.actions.config.HEALTHCONNECT_URL = None
        base.actions.actions.config.HEALTHCONNECT_TOKEN = None
