import logging
import re
import uuid
from typing import Any, Dict, List, Optional, Text, Union
from urllib.parse import urlencode, urljoin

import httpx
import sentry_sdk
from rasa_sdk import Tracker
from rasa_sdk.events import ActionExecuted, AllSlotsReset, SessionStarted, SlotSet
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

    SLOTS = ["terms"]

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
            dispatcher.utter_message(template="utter_more_terms_doc")
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

    SLOTS = ["mobile_no", "age", "research_consent"]

    PERSISTED_SLOTS = [
        "gender",
        "province",
        "location",
        "location_confirm",
    ]

    MINOR_SKIP_SLOTS = ["location", "location_confirm", "research_consent"]

    STUDY_SKIP_SLOTS = ["province", "location", "location_confirm"]

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
        activation = tracker.get_slot("activation")

        if activation:
            if not activation.startswith("tb_study"):
                slots.remove("research_consent")
        else:
            slots.remove("research_consent")

        if activation == "tb_study_a" or activation == "tb_study_b" or activation == "tb_study_c":
            for slot in cls.STUDY_SKIP_SLOTS:
                if slot in slots:
                    slots.remove(slot)

        if tracker.get_slot("age") == "<18":
            for slot in cls.MINOR_SKIP_SLOTS:
                if slot in slots:
                    slots.remove(slot)

        for slot in slots:
            if slot == "mobile_no":
                activation = tracker.get_slot("activation")
                if not activation or not activation.endswith("_agent"):
                    continue

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
            "mobile_no": [self.from_entity(entity="number"), self.from_text()],
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
            "research_consent": [
                self.from_intent(intent="affirm", value="yes"),
                self.from_intent(intent="deny", value="no"),
                self.from_intent(intent="more", value="more"),
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
        result = self.validate_generic("age", dispatcher, value, self.age_data)

        if result.get("age") == "<18":
            result["location"] = "<not collected>"
        return result

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

    def validate_research_consent(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Optional[Text]]:
        if value == "3":
            dispatcher.utter_message(template="utter_research_consent_more_p1")
            dispatcher.utter_message(template="utter_research_consent_more_p2")
            dispatcher.utter_message(template="utter_research_consent_more_p3")
            return {"research_consent": None}
        if value == "2":
            dispatcher.utter_message(template="utter_research_consent_no")
        return self.validate_generic(
            "research_consent", dispatcher, value, {1: "yes", 2: "no", 3: "more"}
        )

    async def places_lookup(self, client, search_text, session_token, province):
        locationbias = {
            "ec": "-32.2968402,26.419389",
            "fs": "-28.4541105,26.7967849",
            "gt": "-26.2707593,28.1122679",
            "lp": "-23.4012946,29.4179324",
            "mp": "-25.565336,30.5279096",
            "nc": "-29.0466808,21.8568586",
            "nl": "-28.5305539,30.8958242",
            "nw": "-26.6638599,25.2837585",
            "wc": "-33.2277918,21.8568586",
        }[province]
        querystring = urlencode(
            {
                "key": config.GOOGLE_PLACES_API_KEY,
                "input": search_text,
                "sessiontoken": session_token,
                "language": "en",
                "components": "country:za",
                "location": locationbias,
            }
        )
        url = (
            "https://maps.googleapis.com/maps/api/place/autocomplete/json"
            f"?{querystring}"
        )
        response = (await client.get(url)).json()
        if not response["predictions"]:
            return None
        place_id = response["predictions"][0]["place_id"]

        querystring = urlencode(
            {
                "key": config.GOOGLE_PLACES_API_KEY,
                "place_id": place_id,
                "sessiontoken": session_token,
                "language": "en",
                "fields": "formatted_address,geometry",
            }
        )
        url = f"https://maps.googleapis.com/maps/api/place/details/json?{querystring}"
        response = (await client.get(url)).json()
        return response["result"]

    def get_province(self, tracker):
        return tracker.get_slot("province")

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

        session_token = uuid.uuid4().hex
        province = self.get_province(tracker)

        if hasattr(httpx, "AsyncClient"):
            # from httpx>=0.11.0, the async client is a different class
            HTTPXClient = getattr(httpx, "AsyncClient")
        else:
            HTTPXClient = getattr(httpx, "Client")

        async with HTTPXClient() as client:
            location = None
            for _ in range(3):
                try:
                    location = await self.places_lookup(
                        client, value, session_token, province
                    )
                    break
                except Exception:
                    pass
            if not location:
                dispatcher.utter_message(template="utter_incorrect_location")
                return {"location": None}
            geometry = location["geometry"]["location"]
            return {
                "location": location["formatted_address"],
                "location_coords": self.format_location(
                    geometry["lat"], geometry["lng"]
                ),
                "city_location_coords": self.format_location(
                    geometry["lat"], geometry["lng"]
                ),
            }

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

    def validate_mobile_no(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Optional[Text]]:

        numbers = re.findall(r"0\d{9}", re.sub(r"[\s-]", "", value))
        if numbers:
            return {"mobile_no": numbers[0]}
        dispatcher.utter_message(template="utter_invalid_mobile_no")
        return {"mobile_no": None}

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
        "study_tracing",
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

        activation = tracker.get_slot("activation")

        for slot in cls.SLOTS:
            if activation:
                if activation.startswith("tb_study"):
                    if slot == "tracing":
                        continue
                else:
                    if slot == "study_tracing":
                        continue

            if not tracker.get_slot(slot):
                return [slot]
        return []

    def slot_mappings(self) -> Dict[Text, Union[Dict, List[Dict]]]:
        return {
            "symptoms_cough": [
                self.from_entity(entity="number"),
                self.from_intent(intent="affirm", value="yes"),
                self.from_intent(intent="deny", value="no"),
                self.from_text(),
            ],
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
            "study_tracing": [
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
            "symptoms_cough", dispatcher, value, self.yes_no_data
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

    def validate_study_tracing(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Optional[Text]]:
        return self.validate_generic(
            "study_tracing", dispatcher, value, self.yes_no_data
        )

    def merge(self, data_minor, data):
        data_minor.update(data)
        return data_minor

    def get_healthcheck_data(self, tracker: Tracker, risk: Text) -> Dict[Text, Any]:
        research_consent = tracker.get_slot("research_consent")
        data = {
            "deduplication_id": uuid.uuid4().hex,
            "msisdn": f'+{tracker.sender_id.lstrip("+")}',
            "source": "WhatsApp",
            "province": f'ZA-{tracker.get_slot("province").upper()}' if tracker.get_slot("province") is not None else "",
            "city": tracker.get_slot("location") if tracker.get_slot("location") is not None else None,
            "age": self.AGE_MAPPING[tracker.get_slot("age")],
            "gender": self.GENDER_MAPPING[tracker.get_slot("gender")],
            "cough": self.YES_NO_MAPPING[tracker.get_slot("symptoms_cough")],
            "fever": self.YES_NO_MAPPING[tracker.get_slot("symptoms_fever")],
            "sweat": self.YES_NO_MAPPING[tracker.get_slot("symptoms_sweat")],
            "weight": self.YES_NO_MAPPING[tracker.get_slot("symptoms_weight")],
            "exposure": self.YES_NO_MAYBE_MAPPING[tracker.get_slot("exposure")],
            "risk": risk,
            "research_consent": self.YES_NO_MAPPING[
                tracker.get_slot("research_consent")
            ]
            if research_consent != "more" and research_consent is not None
            else None,
            "language": config.LANGUAGE,
        }

        if self.AGE_MAPPING[tracker.get_slot("age")] != "<18":
            city_location = self.fix_location_format(
                tracker.get_slot("city_location_coords")
            )
            if city_location != "":
                data["city_location"] = city_location
            location = self.fix_location_format(tracker.get_slot("location_coords"))
            if location != "":
                data["location"] = location
        activation = tracker.get_slot("activation")

        if activation:
            if activation.startswith("tb_study"):
                data["tracing"] = self.YES_NO_MAPPING[tracker.get_slot("study_tracing")]
            else:
                data["tracing"] = self.YES_NO_MAPPING[tracker.get_slot("tracing")]
        else:
            data["tracing"] = self.YES_NO_MAPPING[tracker.get_slot("tracing")]

        if activation:
            if activation.endswith("_agent"):
                # Switch the msisdn if the device is shared.
                data["originating_msisdn"] = data["msisdn"]
                data["msisdn"] = f'+27{tracker.get_slot("mobile_no").lstrip("0")}'
            data["activation"] = activation

        return data

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
        templates = []
        group_arm = None
        tbcheck_id = None

        if config.HEALTHCONNECT_URL and config.HEALTHCONNECT_TOKEN:
            url = urljoin(config.HEALTHCONNECT_URL, "/v2/tbcheck/")
            post_data = self.get_healthcheck_data(tracker, risk)
            # TODO: remove print
            print(post_data)
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
                        # TODO: remove print
                        print(resp.content)
                        json_resp = resp.json()

                        # Get tbcheck ID
                        tbcheck_id = json_resp.get("id")
                        consent = json_resp.get("research_consent")
                        activation = tracker.get_slot("activation")

                        if activation:
                            if not consent or (consent and activation == "tb_study_a"):
                                templates = utils.get_risk_templates(risk, data, activation)
                            else:
                                # Get template and user group arm
                                templates, group_arm = utils.get_display_message_template(
                                    json_resp
                                )
                        else:
                            templates = utils.get_risk_templates(risk, data, activation)

                        if not utils.is_duplicate_error(resp):
                            resp.raise_for_status()

                        break
                except httpx.HTTPError as e:
                    print(e)
                    if i == config.HTTP_RETRIES - 1:
                        raise e
        if group_arm:
            if group_arm.startswith("soft_"):
                return [
                    SlotSet("group_arm", group_arm),
                    SlotSet("tbcheck_id", tbcheck_id),
                ]
            else:
                for template in templates:
                    dispatcher.utter_message(template=template)
        else:
            for template in templates:
                dispatcher.utter_message(template=template)

        return []


class GroupArmForm(BaseFormAction):
    SLOTS = ["soft_commitment_plus"]

    CLINIC_SLOTS = ["clinic_visit_day"]

    DAYS_MAPPING = {
        "MONDAY": "mon",
        "TUESDAY": "tue",
        "WEDNESDAY": "wed",
        "THURSDAY": "thu",
        "FRIDAY": "fri",
    }

    def name(self) -> Text:
        return "group_arm_form"

    @classmethod
    def required_slots(cls, tracker: Tracker) -> List[Text]:
        arm = tracker.get_slot("group_arm")
        if arm:
            if arm == "soft_commit_plus":
                for slot in cls.CLINIC_SLOTS:
                    if not tracker.get_slot(slot):
                        return [slot]
                return []
            else:
                arm = arm.lower()
                return [arm]
        return []

    def slot_mappings(self) -> Dict[Text, Union[Dict, List[Dict]]]:
        return {
            "soft_commitment_plus": [
                self.from_intent(intent="affirm", value="yes"),
                self.from_intent(intent="deny", value="no"),
                self.from_text(),
            ],

            "clinic_visit_day": [
                self.from_entity(entity="number"),
                self.from_text(),
            ],
        }

    def validate_soft_commitment_plus(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Optional[Text]]:
        return self.validate_generic(
            "soft_commitment_plus", dispatcher, value, self.yes_no_data
        )

    def validate_clinic_visit_day(
        self,
        value: Text,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> Dict[Text, Optional[Text]]:
        return self.validate_generic(
            "clinic_visit_day",
            dispatcher,
            value,
            {1: "MONDAY", 2: "TUESDAY", 3: "WEDNESDAY", 4: "THURSDAY", 5: "FRIDAY"},
        )

    async def submit(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict]:
        """Check user response to display next message"""
        if config.HEALTHCONNECT_URL and config.HEALTHCONNECT_TOKEN:
            group_arm = tracker.get_slot("group_arm")

            if group_arm:
                id = tracker.get_slot("tbcheck_id")
                url = urljoin(config.HEALTHCONNECT_URL, f"/v2/tbcheck/{id}/")

                headers = {
                    "Authorization": f"Token {config.HEALTHCONNECT_TOKEN}",
                    "User-Agent": "rasa/tbconnect-bot",
                }

                soft_commit_plus = tracker.get_slot("soft_commitment_plus")

                data = {
                    "commit_get_tested": soft_commit_plus
                    if soft_commit_plus is not None
                    else False,
                    "clinic_visit_day": self.DAYS_MAPPING.get(
                        tracker.get_slot("clinic_visit_day")
                    ),
                    "location": tracker.get_slot("location_coords"),
                    "city_location": tracker.get_slot("city_location_coords"),
                }

                if hasattr(httpx, "AsyncClient"):
                    # from httpx>=0.11.0, the async client is a different class
                    HTTPXClient = getattr(httpx, "AsyncClient")
                else:
                    HTTPXClient = getattr(httpx, "Client")

                for i in range(config.HTTP_RETRIES):
                    try:
                        async with HTTPXClient() as client:
                            resp = await client.patch(url, json=data, headers=headers)
                            # TODO: remove print
                            print(resp.content)
                            break
                    except httpx.HTTPError as e:
                        print(e)
                        if i == config.HTTP_RETRIES - 1:
                            raise e

                if soft_commit_plus == "yes":
                    dispatcher.utter_message(template="utter_commitment_yes")
                elif soft_commit_plus == "no":
                    dispatcher.utter_message(template="utter_soft_commitment_plus_no")

        return []


class OptInForm(Action):
    SLOTS = [
        "symptoms_cough",
        "symptoms_fever",
        "symptoms_sweat",
        "symptoms_weight",
        "exposure",
        "tracing",
    ]

    def name(self) -> Text:
        return "action_opt_in"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        if config.HEALTHCONNECT_URL and config.HEALTHCONNECT_TOKEN:
            msisdn = f'+{tracker.sender_id.lstrip("+")}'
            url = urljoin(
                config.HEALTHCONNECT_URL, f"/v2/healthcheckuserprofile/{msisdn}/"
            )

            if not tracker.get_slot("terms"):
                dispatcher.utter_message(template="utter_do_tb_screening")
                return []

            data = {
                slot: tracker.get_slot(slot)
                for slot in self.SLOTS
                if slot.startswith("symptoms_")
            }
            data.update({"exposure": tracker.get_slot("exposure")})

            risk = utils.get_risk_level(data)

            patch_data: dict = {
                "language": config.LANGUAGE,
                "data": {"follow_up_optin": True},
            }

            if risk != "low":
                patch_data["data"]["synced_to_tb_rapidpro"] = False

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
                        resp = await client.patch(url, json=patch_data, headers=headers)
                        # TODO: remove print
                        print(resp.content)
                        resp.raise_for_status()
                        break
                except httpx.HTTPError as e:
                    if i == config.HTTP_RETRIES - 1:
                        raise e
        dispatcher.utter_message(template="utter_opt_in_yes")
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


class SetActivationAction(Action):
    def name(self):
        return "action_set_activation"

    async def get_activation(self, msisdn):
        if config.TURN_URL and config.TURN_TOKEN:
            url = urljoin(config.TURN_URL, f"/v1/contacts/{msisdn}/profile")

            headers = {
                "Accept": "application/vnd.v1+json",
                "Authorization": f"Bearer {config.TURN_TOKEN}",
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
                        resp = await client.get(url, headers=headers)
                        if resp.status_code == httpx.codes.NOT_FOUND:
                            return {}
                        resp.raise_for_status()
                        return resp.json()
                except httpx.HTTPError as e:
                    print(e)
                    if i == config.HTTP_RETRIES - 1:
                        raise e

    async def run(self, dispatcher, tracker, domain):
        msisdn = f'{tracker.sender_id.lstrip("+")}'
        data = await self.get_activation(msisdn)
        events = []
        activation = data.get("fields", {}).get("tb_activation")
        if activation:
            if activation.endswith("_agent"):
                events.append(AllSlotsReset())
            events.append(SlotSet("activation", activation))
        return events


class StudyRestriction(Action):
    def name(self) -> Text:
        return "action_study_restriction"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        events = []
        if config.HEALTHCONNECT_URL and config.HEALTHCONNECT_TOKEN:
            activation = tracker.get_slot("activation")

            if activation == "tb_study_a" or activation == "tb_study_b" or activation == "tb_study_c":
                msisdn = f'+{tracker.sender_id.lstrip("+")}'
                url = urljoin(
                    config.HEALTHCONNECT_URL, f"/v2/healthcheckuserprofile/{msisdn}/"
                )

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
                            resp = await client.get(url, headers=headers)

                            if resp:
                                data = resp.json()
                                activation = data.get("activation")
                                if activation == "tb_study_a" or activation == "tb_study_b" or activation == "tb_study_c":
                                    dispatcher.utter_message(
                                        template="utter_study_completed"
                                    )

                                    # Reset activation slot
                                    events.append(SlotSet("activation", None))
                            break
                    except httpx.HTTPError as e:
                        if i == config.HTTP_RETRIES - 1:
                            raise e
        return events
