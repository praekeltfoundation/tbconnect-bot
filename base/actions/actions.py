import logging
import re
import uuid
from typing import Any, Dict, List, Optional, Text, Union
from urllib.parse import urlencode, urljoin

import httpx
import sentry_sdk
from rasa_sdk import Tracker
from rasa_sdk.events import ActionExecuted, SessionStarted, SlotSet
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.forms import Action, FormAction
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.sanic import SanicIntegration

from . import config, utils

logger = logging.getLogger(__name__)

if config.SENTRY_DSN:
    sentry_logging = LoggingIntegration(level=logging.INFO, event_level=logging.ERROR)
    sentry_sdk.init(
        dsn=config.SENTRY_DSN, integrations=[sentry_logging, SanicIntegration()]
    )


class BaseFormAction(FormAction):
    def name(self) -> Text:
        """Unique identifier of the form"""

        return "base_form"

    @property
    def yes_no_data(self) -> Dict[int, Text]:
        return {1: "yes", 2: "no"}

    @property
    def yes_no_maybe_data(self) -> Dict[int, Text]:
        return {1: "yes", 2: "no", 3: "not sure"}

    @property
    def no_yeslt_yesgt_data(self) -> Dict[int, Text]:
        return {1: "no", 2: "yes lt 2weeks", 3: "yes gt 2weeks"}

    @staticmethod
    def is_int(value: Text) -> bool:
        if not isinstance(value, str):
            return False

        try:
            int(value)
            return True
        except ValueError:
            return False

    def validate_generic(
        self,
        field: Text,
        dispatcher: CollectingDispatcher,
        value: Text,
        data: Dict[int, Text],
    ) -> Dict[Text, Optional[Text]]:
        """
        Validates that the value is either:
        - One of the values
        - An integer that is one of the keys
        """
        if value and isinstance(value, str) and value.lower() in data.values():
            return {field: value}
        elif self.is_int(value) and int(value) in data:
            return {field: data[int(value)]}
        else:
            dispatcher.utter_message(template="utter_incorrect_selection")
            return {field: None}

    @staticmethod
    def format_location(latitude: float, longitude: float) -> Text:
        """
        Returns the location in ISO6709 format
        """

        def fractional_part(f):
            if not f % 1:
                return ""
            parts = str(f).split(".")
            return f".{parts[1]}"

        # latitude integer part must be fixed width 2, longitude 3
        return (
            f"{int(latitude):+03d}"
            f"{fractional_part(latitude)}"
            f"{int(longitude):+04d}"
            f"{fractional_part(longitude)}"
            "/"
        )

    @staticmethod
    def fix_location_format(text: Text) -> Text:
        """
        Previously there was a bug that caused the location to not be stored in
        proper ISO6709 format. This function extracts the latitude and longitude from
        either the incorrect or correct format, and then returns a properly formatted
        ISO6709 string
        """
        if not text:
            return ""
        regex = re.compile(
            r"""
            ^
            (?P<latitude>[\+|-]\d+\.?\d*)
            (?P<longitude>[\+|-]\d+\.?\d*)
            """,
            flags=re.VERBOSE,
        )
        match = regex.match(text)
        if not match:
            raise ValueError(f"Invalid location {text}")
        data = match.groupdict()
        return BaseFormAction.format_location(
            float(data["latitude"]), float(data["longitude"])
        )


class TBCheckTermsForm(BaseFormAction):
    """TBCheck form action"""

    SLOTS = [
        "terms",
    ]

    def name(self) -> Text:
        """Unique identifier of the form"""

        return "tbcheck_terms_form"

    @classmethod
    def required_slots(cls, tracker: Tracker) -> List[Text]:
        for slot in cls.SLOTS:
            if not tracker.get_slot(slot):
                return [slot]
        return []

    def slot_mappings(self) -> Dict[Text, Union[Dict, List[Dict]]]:
        return {
            "terms": [
                self.from_intent(intent="affirm", value="yes"),
                self.from_intent(intent="more", value="more"),
                self.from_text(),
            ]
        }

    def validate_terms(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Optional[Text]]:
        if value == "more":
            dispatcher.utter_message(template="utter_more_terms")
            return {"terms": None}

        return self.validate_generic("terms", dispatcher, value, {1: "yes"})

    def submit(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        """Define what the form has to do
            after all required slots are filled"""

        # utter submit template
        return []


class TBCheckProfileForm(BaseFormAction):
    """TBCheck form action"""

    SLOTS = ["age"]

    PERSISTED_SLOTS = [
        "gender",
        "province",
        "location",
        "location_confirm",
    ]

    def name(self) -> Text:
        """Unique identifier of the form"""

        return "tbcheck_profile_form"

    @classmethod
    def required_slots(cls, tracker: Tracker) -> List[Text]:
        """A list of required slots that the form has to fill"""
        slots = cls.SLOTS + cls.PERSISTED_SLOTS
        # This is a strange workaround
        # Rasa wants to fill all the slots with every question
        # To prevent that, we just tell Rasa with each message that the slots
        # that it's required to fill is just a single slot, the first
        # slot that hasn't been filled yet.

        for slot in slots:
            if not tracker.get_slot(slot):
                return [slot]
        return []

    @property
    def province_data(self) -> Dict[int, Text]:
        with open("base/data/lookup_tables/provinces.txt") as f:
            return dict(enumerate(f.read().splitlines(), start=1))

    @property
    def age_data(self) -> Dict[int, Text]:
        with open("base/data/lookup_tables/ages.txt") as f:
            return dict(enumerate(f.read().splitlines(), start=1))

    @property
    def gender_data(self) -> Dict[int, Text]:
        with open("base/data/lookup_tables/gender.txt") as f:
            return dict(enumerate(f.read().splitlines(), start=1))

    def slot_mappings(self) -> Dict[Text, Union[Dict, List[Dict]]]:
        return {
            "age": [self.from_entity(entity="number"), self.from_text()],
            "gender": [self.from_entity(entity="number"), self.from_text()],
            "province": [
                self.from_entity(entity="number"),
                self.from_entity(intent="inform", entity="province"),
                self.from_text(),
            ],
            "location": [self.from_text()],
            "location_confirm": [
                self.from_entity(entity="number"),
                self.from_intent(intent="affirm", value="yes"),
                self.from_intent(intent="deny", value="no"),
                self.from_text(),
            ],
        }

    def validate_age(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Optional[Text]]:
        return self.validate_generic("age", dispatcher, value, self.age_data)

    def validate_gender(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Optional[Text]]:
        return self.validate_generic("gender", dispatcher, value, self.gender_data)

    def validate_province(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Optional[Text]]:
        return self.validate_generic("province", dispatcher, value, self.province_data)

    async def validate_location(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Optional[Text]]:
        latest_message = tracker.get_last_event_for("user")
        metadata = latest_message.get("metadata")

        # Use location pin data if submitted
        if metadata and metadata.get("type") == "location":
            latitude = metadata["location"]["latitude"]
            longitude = metadata["location"]["longitude"]
            address = metadata["location"].get("address")
            if not address:
                address = f"GPS: {latitude}, {longitude}"
            return {
                "location_coords": self.format_location(latitude, longitude),
                "location": address,
                "location_confirm": "yes",
            }

        if not value:
            dispatcher.utter_message(template="utter_incorrect_selection")
            return {"location": None}

        if not config.GOOGLE_PLACES_API_KEY:
            return {
                "location": value,
            }

        querystring = urlencode(
            {
                "key": config.GOOGLE_PLACES_API_KEY,
                "input": value,
                "language": "en",
                "inputtype": "textquery",
                "fields": "formatted_address,geometry",
            }
        )

        if hasattr(httpx, "AsyncClient"):
            # from httpx>=0.11.0, the async client is a different class
            HTTPXClient = getattr(httpx, "AsyncClient")
        else:
            HTTPXClient = getattr(httpx, "Client")

        async with HTTPXClient() as client:
            response = await client.get(
                (
                    f"https://maps.googleapis.com"
                    f"/maps/api/place/findplacefromtext/json?{querystring}"
                )
            )
            location = response.json()
            if location["candidates"]:
                formatted_address = location["candidates"][0]["formatted_address"]
                geometry = location["candidates"][0]["geometry"]["location"]
                latitude = geometry["lat"]
                longitude = geometry["lng"]
                return {
                    "location": formatted_address,
                    "city_location_coords": self.format_location(latitude, longitude),
                }
            else:
                dispatcher.utter_message(template="utter_incorrect_location")
                return {"location": None}

    def validate_location_confirm(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Optional[Text]]:
        loc_confirm = self.validate_generic(
            "location_confirm", dispatcher, value, self.yes_no_data
        )
        if loc_confirm["location_confirm"] and loc_confirm["location_confirm"] == "no":
            return {"location_confirm": None, "location": None}
        return loc_confirm

    def submit(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        """Define what the form has to do
            after all required slots are filled"""

        # utter submit template
        return []


class ActionSessionStart(Action):
    def name(self) -> Text:
        return "action_session_start"

    def get_carry_over_slots(self, tracker: Tracker) -> List[Dict[Text, Any]]:
        actions = [SessionStarted()]
        carry_over_slots = (
            TBCheckTermsForm.SLOTS
            + TBCheckProfileForm.PERSISTED_SLOTS
            + ["location_coords", "city_location_coords"]
        )
        for slot in carry_over_slots:
            actions.append(SlotSet(slot, tracker.get_slot(slot)))
        return actions

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        actions = self.get_carry_over_slots(tracker)
        actions.append(ActionExecuted("action_listen"))
        return actions


class TBCheckForm(BaseFormAction):
    """TBCheck form action"""

    SLOTS = [
        "symptoms_cough",
        "symptoms_fever",
        "symptoms_sweat",
        "symptoms_weight",
        "exposure",
        "tracing",
    ]

    GENDER_MAPPING = {
        "MALE": "male",
        "FEMALE": "female",
        "OTHER": "other",
        "RATHER NOT SAY": "not_say",
    }

    AGE_MAPPING = {
        "<18": "<18",
        "18-39": "18-40",
        "40-65": "40-65",
        ">65": ">65",
    }

    YES_NO_MAYBE_MAPPING = {
        "yes": "yes",
        "no": "no",
        "not sure": "not_sure",
    }

    YES_NO_MAPPING = {
        "yes": True,
        "no": False,
    }

    def name(self) -> Text:
        """Unique identifier of the form"""

        return "tbcheck_form"

    @classmethod
    def required_slots(cls, tracker: Tracker) -> List[Text]:
        """A list of required slots that the form has to fill"""

        # This is a strange workaround
        # Rasa wants to fill all the slots with every question
        # To prevent that, we just tell Rasa with each message that the slots
        # that it's required to fill is just a single slot, the first
        # slot that hasn't been filled yet.

        for slot in cls.SLOTS:
            if not tracker.get_slot(slot):
                return [slot]
        return []

    def slot_mappings(self) -> Dict[Text, Union[Dict, List[Dict]]]:
        return {
            "symptoms_cough": [self.from_entity(entity="number"), self.from_text()],
            "symptoms_fever": [
                self.from_entity(entity="number"),
                self.from_intent(intent="affirm", value="yes"),
                self.from_intent(intent="deny", value="no"),
                self.from_text(),
            ],
            "symptoms_sweat": [
                self.from_entity(entity="number"),
                self.from_intent(intent="affirm", value="yes"),
                self.from_intent(intent="deny", value="no"),
                self.from_text(),
            ],
            "symptoms_weight": [
                self.from_entity(entity="number"),
                self.from_intent(intent="affirm", value="yes"),
                self.from_intent(intent="deny", value="no"),
                self.from_text(),
            ],
            "exposure": [
                self.from_entity(entity="number"),
                self.from_intent(intent="affirm", value="yes"),
                self.from_intent(intent="deny", value="no"),
                self.from_intent(intent="maybe", value="not sure"),
                self.from_text(),
            ],
            "tracing": [
                self.from_entity(entity="number"),
                self.from_intent(intent="affirm", value="yes"),
                self.from_intent(intent="deny", value="no"),
                self.from_text(),
            ],
        }

    def validate_symptoms_cough(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Optional[Text]]:
        return self.validate_generic(
            "symptoms_cough", dispatcher, value, self.no_yeslt_yesgt_data
        )

    def validate_symptoms_fever(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Optional[Text]]:
        return self.validate_generic(
            "symptoms_fever", dispatcher, value, self.yes_no_data
        )

    def validate_symptoms_sweat(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Optional[Text]]:
        return self.validate_generic(
            "symptoms_sweat", dispatcher, value, self.yes_no_data
        )

    def validate_symptoms_weight(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Optional[Text]]:
        return self.validate_generic(
            "symptoms_weight", dispatcher, value, self.yes_no_data
        )

    def validate_exposure(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Optional[Text]]:
        return self.validate_generic(
            "exposure", dispatcher, value, self.yes_no_maybe_data
        )

    def validate_tracing(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Optional[Text]]:
        return self.validate_generic("tracing", dispatcher, value, self.yes_no_data)

    def get_healthcheck_data(self, tracker: Tracker, risk: Text) -> Dict[Text, Any]:
        return {
            "deduplication_id": uuid.uuid4().hex,
            "msisdn": f'{tracker.sender_id.lstrip("+")}',
            "source": "WhatsApp",
            "province": f'ZA-{tracker.get_slot("province").upper()}',
            "city": tracker.get_slot("location"),
            "age": self.AGE_MAPPING[tracker.get_slot("age")],
            "gender": self.GENDER_MAPPING[tracker.get_slot("gender")],
            "cough": tracker.get_slot("symptoms_cough").replace(" ", "_"),
            "fever": self.YES_NO_MAPPING[tracker.get_slot("symptoms_fever")],
            "sweat": self.YES_NO_MAPPING[tracker.get_slot("symptoms_sweat")],
            "weight": self.YES_NO_MAPPING[tracker.get_slot("symptoms_weight")],
            "exposure": self.YES_NO_MAYBE_MAPPING[tracker.get_slot("exposure")],
            "tracing": self.YES_NO_MAPPING[tracker.get_slot("tracing")],
            "risk": risk,
            "location": tracker.get_slot("location_coords"),
        }

    async def submit(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        """Define what the form has to do
            after all required slots are filled"""
        data = {
            slot: tracker.get_slot(slot)
            for slot in self.SLOTS
            if slot.startswith("symptoms_")
        }
        data.update(
            {"exposure": tracker.get_slot("exposure"), "age": tracker.get_slot("age")}
        )

        risk = utils.get_risk_level(data)

        if config.HEALTHCONNECT_URL and config.HEALTHCONNECT_TOKEN:
            url = urljoin(config.HEALTHCONNECT_URL, "/api/v2/tbcheck/")

            post_data = self.get_healthcheck_data(tracker, risk)
            headers = {
                "Authorization": f"Token {config.HEALTHCONNECT_TOKEN}",
                "User-Agent": "rasa/tbconnect-bot",
            }

            if hasattr(httpx, "AsyncClient"):
                # from httpx>=0.11.0, the async client is a different class
                HTTPXClient = getattr(httpx, "AsyncClient")
            else:
                HTTPXClient = getattr(httpx, "Client")

            for i in range(config.HTTP_RETRIES):
                try:
                    async with HTTPXClient() as client:
                        resp = await client.post(url, json=post_data, headers=headers)
                        resp.raise_for_status()
                        break
                except httpx.HTTPError as e:
                    if i == config.HTTP_RETRIES - 1:
                        raise e

        dispatcher.utter_message(template=f"utter_risk_{risk}")
        return []


class ActionExit(Action):
    def name(self) -> Text:
        return "action_exit"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(template="utter_exit")
        return ActionSessionStart().get_carry_over_slots(tracker)
