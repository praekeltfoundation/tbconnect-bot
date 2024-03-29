import json
from typing import Any, Dict, Optional, Text

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
    async def test_validate_mobile_no(self):
        form = TBCheckProfileForm()
        dispatcher = CollectingDispatcher()

        tracker = utils.get_tracker_for_number_slot_with_value(
            form, "mobile_no", "0820010001", {"activation": "foo_agent"}
        )
        events = await form.run(dispatcher=dispatcher, tracker=tracker, domain=None)
        assert events == [
            SlotSet("mobile_no", "0820010001"),
            SlotSet("requested_slot", "age"),
        ]

    @pytest.mark.asyncio
    async def test_validate_mobile_no_with_spaces(self):
        form = TBCheckProfileForm()
        dispatcher = CollectingDispatcher()

        tracker = utils.get_tracker_for_number_slot_with_value(
            form, "mobile_no", "082 001 0001", {"activation": "foo_agent"}
        )
        events = await form.run(dispatcher=dispatcher, tracker=tracker, domain=None)
        assert events == [
            SlotSet("mobile_no", "0820010001"),
            SlotSet("requested_slot", "age"),
        ]

    @pytest.mark.asyncio
    async def test_validate_mobile_no_with_dashes(self):
        form = TBCheckProfileForm()
        dispatcher = CollectingDispatcher()

        tracker = utils.get_tracker_for_number_slot_with_value(
            form, "mobile_no", "082-001-0001", {"activation": "foo_agent"}
        )
        events = await form.run(dispatcher=dispatcher, tracker=tracker, domain=None)
        assert events == [
            SlotSet("mobile_no", "0820010001"),
            SlotSet("requested_slot", "age"),
        ]

    @pytest.mark.asyncio
    async def test_validate_age(self):
        form = TBCheckProfileForm()
        dispatcher = CollectingDispatcher()

        tracker = utils.get_tracker_for_number_slot_with_value(form, "age", "1")
        events = await form.run(dispatcher=dispatcher, tracker=tracker, domain=None)
        assert events == [
            SlotSet("age", "<18"),
            SlotSet("location", "<not collected>"),
            SlotSet("requested_slot", "gender"),
        ]

        tracker = utils.get_tracker_for_number_slot_with_value(
            form, "age", "2", {"research_consent": "yes"}
        )
        events = await form.run(dispatcher=dispatcher, tracker=tracker, domain=None)
        assert events == [SlotSet("age", "18-39"), SlotSet("requested_slot", "gender")]

        tracker = utils.get_tracker_for_number_slot_with_value(
            form, "age", "3", {"research_consent": "yes"}
        )
        events = await form.run(dispatcher=dispatcher, tracker=tracker, domain=None)
        assert events == [SlotSet("age", "40-65"), SlotSet("requested_slot", "gender")]

        tracker = utils.get_tracker_for_number_slot_with_value(
            form, "age", "4", {"research_consent": "yes"}
        )
        events = await form.run(dispatcher=dispatcher, tracker=tracker, domain=None)
        assert events == [SlotSet("age", ">65"), SlotSet("requested_slot", "gender")]

        tracker = utils.get_tracker_for_number_slot_with_value(
            form, "age", ["2", "39"], {"research_consent": "yes"}
        )
        events = await form.run(dispatcher=dispatcher, tracker=tracker, domain=None)
        assert events == [SlotSet("age", None), SlotSet("requested_slot", "age")]

        tracker = utils.get_tracker_for_number_slot_with_value(
            form, "age", "not a number", {"research_consent": "yes"}
        )
        events = await form.run(dispatcher=dispatcher, tracker=tracker, domain=None)
        assert events == [SlotSet("age", None), SlotSet("requested_slot", "age")]

    @pytest.mark.asyncio
    async def test_validate_gender(self):
        form = TBCheckProfileForm()
        dispatcher = CollectingDispatcher()

        tracker = utils.get_tracker_for_number_slot_with_value(
            form, "gender", "1", {"age": "18-39", "research_consent": "yes"}
        )
        events = await form.run(dispatcher=dispatcher, tracker=tracker, domain=None)
        assert events == [
            SlotSet("gender", "MALE"),
            SlotSet("requested_slot", "province"),
        ]

        tracker = utils.get_tracker_for_number_slot_with_value(
            form, "gender", "2", {"age": "18-39", "research_consent": "yes"}
        )
        events = await form.run(dispatcher=dispatcher, tracker=tracker, domain=None)
        assert events == [
            SlotSet("gender", "FEMALE"),
            SlotSet("requested_slot", "province"),
        ]

        tracker = utils.get_tracker_for_number_slot_with_value(
            form, "gender", "3", {"age": "18-39", "research_consent": "yes"}
        )
        events = await form.run(dispatcher=dispatcher, tracker=tracker, domain=None)
        assert events == [
            SlotSet("gender", "OTHER"),
            SlotSet("requested_slot", "province"),
        ]

        tracker = utils.get_tracker_for_number_slot_with_value(
            form, "gender", "4", {"age": "18-39", "research_consent": "yes"}
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
                form,
                "province",
                str(i),
                {"age": "18-39", "gender": "MALE", "research_consent": "yes"},
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
        assert TBCheckProfileForm.format_location(0, 0) == "+00+000"
        assert TBCheckProfileForm.format_location(-1, -1) == "-01-001"
        assert TBCheckProfileForm.format_location(1.234, -5.678) == "+01.234-005.678"
        assert TBCheckProfileForm.format_location(-12.34, 123.456) == "-12.34+123.456"
        assert (
            TBCheckProfileForm.format_location(51.481845, 7.216236)
            == "+51.481845+007.216236"
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
            SlotSet("location_coords", "+01.23+004.56"),
            SlotSet("location_confirm", "yes"),
        ]

    @pytest.mark.asyncio
    async def test_validate_location_text(self):
        """
        If there's no google places API credentials, then just use the text
        """
        form = TBCheckProfileForm()

        tracker = self.get_tracker_for_text_slot_with_message(
            "location",
            "Cape Town",
        )

        events = await form.validate(CollectingDispatcher(), tracker, {})
        assert events == [
            SlotSet("location", "Cape Town"),
        ]

    @respx.mock
    @pytest.mark.asyncio
    async def test_validate_location_google_places(self):
        """
        If there are no results, then display error message and ask again
        """
        base.actions.actions.config.GOOGLE_PLACES_API_KEY = "test_key"
        form = TBCheckProfileForm()
        form.places_lookup = utils.AsyncMock()
        form.places_lookup.return_value = None

        tracker = self.get_tracker_for_text_slot_with_message(
            "location",
            "Cape Town",
        )

        dispatcher = CollectingDispatcher()
        events = await form.validate(dispatcher, tracker, {})
        assert events == [
            SlotSet("location", None),
        ]

        [message] = dispatcher.messages
        assert message["template"] == "utter_incorrect_location"

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
        base.actions.actions.config.LANGUAGE = "eng"

        request = respx.post(
            "https://healthconnect/v2/tbcheck/",
            content={
                "profile": {"tbconnect_group_arm": "control"},
                "id": 22,
                "research_consent": False,
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
                "research_consent": "no",
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
            "location": "+03.4-001.2",
            "city_location": "+01.2-003.4",
            "research_consent": False,
            "language": "eng",
        }

        base.actions.actions.config.HEALTHCONNECT_URL = None
        base.actions.actions.config.HEALTHCONNECT_TOKEN = None
        base.actions.actions.config.LANGUAGE = None

    @respx.mock
    @pytest.mark.asyncio
    async def test_submit_to_healthconnect_from_shared_device(self):
        """
        Submits the data to the eventstore in the correct format
        """
        base.actions.actions.config.HEALTHCONNECT_URL = "https://healthconnect"
        base.actions.actions.config.HEALTHCONNECT_TOKEN = "token"
        base.actions.actions.config.LANGUAGE = "afr"

        request = respx.post(
            "https://healthconnect/v2/tbcheck/",
            content={
                "profile": {"tbconnect_group_arm": "control"},
                "id": 22,
                "research_consent": False,
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
                "activation": "foo_agent",
                "mobile_no": "0820010001",
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
                "research_consent": "no",
            },
        )
        await form.submit(dispatcher, tracker, {})

        assert request.called
        [(request, response)] = request.calls
        data = json.loads(request.stream.body)
        assert data.pop("deduplication_id")
        assert data == {
            "msisdn": "+27820010001",
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
            "location": "+03.4-001.2",
            "city_location": "+01.2-003.4",
            "research_consent": False,
            "originating_msisdn": "+default",
            "activation": "foo_agent",
            "language": "afr",
        }

        base.actions.actions.config.HEALTHCONNECT_URL = None
        base.actions.actions.config.HEALTHCONNECT_TOKEN = None
        base.actions.actions.config.LANGUAGE = None

    @respx.mock
    @pytest.mark.asyncio
    async def test_submit_18_minor_to_healthconnect(self):
        """
        Submits the data to the eventstore in the correct format
        """
        base.actions.actions.config.HEALTHCONNECT_URL = "https://healthconnect"
        base.actions.actions.config.HEALTHCONNECT_TOKEN = "token"
        base.actions.actions.config.LANGUAGE = "zul"

        request = respx.post(
            "https://healthconnect/v2/tbcheck/",
            content={
                "profile": {"tbconnect_group_arm": "control"},
                "id": 22,
                "research_consent": True,
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
                "age": "<18",
                "symptoms_fever": "no",
                "symptoms_cough": "yes",
                "symptoms_sweat": "yes",
                "symptoms_weight": "yes",
                "exposure": "not sure",
                "tracing": "yes",
                "city_location_coords": "",
                "gender": "RATHER NOT SAY",
                "location": "<not collected>",
                "research_consent": "yes",
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
            "city": "<not collected>",
            "age": "<18",
            "gender": "not_say",
            "cough": True,
            "fever": False,
            "sweat": True,
            "weight": True,
            "exposure": "not_sure",
            "tracing": True,
            "risk": "moderate",
            "research_consent": True,
            "language": "zul",
        }

        base.actions.actions.config.HEALTHCONNECT_URL = None
        base.actions.actions.config.HEALTHCONNECT_TOKEN = None
        base.actions.actions.config.LANGUAGE = None

    @respx.mock
    @pytest.mark.asyncio
    async def test_submit_over_65_to_healthconnect(self):
        """
        Submits the data to the eventstore in the correct format
        """
        base.actions.actions.config.HEALTHCONNECT_URL = "https://healthconnect"
        base.actions.actions.config.HEALTHCONNECT_TOKEN = "token"
        base.actions.actions.config.LANGUAGE = "afr"

        request = respx.post(
            "https://healthconnect/v2/tbcheck/",
            content={
                "profile": {"tbconnect_group_arm": "control"},
                "id": 22,
                "research_consent": True,
            },
        )

        form = TBCheckForm()
        dispatcher = CollectingDispatcher()
        tracker = utils.get_tracker_for_slot_from_intent(
            form,
            "tracing",
            "affirm",
            {
                "province": "za-ec",
                "age": ">65",
                "symptoms_fever": "no",
                "symptoms_cough": "yes",
                "symptoms_sweat": "yes",
                "symptoms_weight": "yes",
                "exposure": "not sure",
                "tracing": "yes",
                "gender": "MALE",
                "city_location_coords": "+1.2-3.4",
                "location_coords": "+3.4-1.2",
                "location": "Cape Town, South Africa",
                "research_consent": "yes",
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
            "province": "ZA-ZA-EC",
            "city": "Cape Town, South Africa",
            "age": ">65",
            "gender": "male",
            "cough": True,
            "fever": False,
            "sweat": True,
            "weight": True,
            "exposure": "not_sure",
            "tracing": True,
            "risk": "moderate",
            "location": "+03.4-001.2",
            "city_location": "+01.2-003.4",
            "research_consent": True,
            "language": "afr",
        }

        base.actions.actions.config.HEALTHCONNECT_URL = None
        base.actions.actions.config.HEALTHCONNECT_TOKEN = None
        base.actions.actions.config.LANGUAGE = None

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
                "research_consent": "no",
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
        base.actions.actions.config.LANGUAGE = "eng"

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
        assert data == {"data": {"follow_up_optin": True}, "language": "eng"}

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
        base.actions.actions.config.LANGUAGE = "xho"

        request = respx.patch(
            "https://healthconnect/v2/healthcheckuserprofile/+default/"
        )

        form = OptInForm()
        dispatcher = CollectingDispatcher()
        tracker = utils.get_tracker_for_slot_from_intent(
            form,
            "terms",
            "opt_in",
            {"terms": "yes", "symptoms_cough": "yes"},
        )
        await form.run(dispatcher, tracker, {})

        assert request.called
        [(request, response)] = request.calls
        data = json.loads(request.stream.body)
        assert data == {
            "data": {"follow_up_optin": True, "synced_to_tb_rapidpro": False},
            "language": "xho",
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
        tracker = utils.get_tracker_for_slot_from_intent(
            form,
            "terms",
            "opt_in",
            {},
        )
        await form.run(dispatcher, tracker, {})

        assert not request.called

        base.actions.actions.config.HEALTHCONNECT_URL = None
        base.actions.actions.config.HEALTHCONNECT_TOKEN = None
