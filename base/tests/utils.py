from rasa_sdk import Tracker


def get_tracker_for_number_slot_with_value(form, slot_name, value, existing_slots={}):
    slots = {}
    slots.update({"requested_slot": slot_name})
    slots.update(existing_slots)
    return Tracker(
        "default",
        slots,
        {"entities": [{"entity": "number", "value": value}]},
        [],
        False,
        None,
        {"name": form.name(), "validate": True, "rejected": False},
        "action_listen",
    )


def get_tracker_for_slot_from_intent(form, slot_name, intent_name, existing_slots={}):
    slots = {}
    slots.update({"requested_slot": slot_name})
    slots.update(existing_slots)
    return Tracker(
        "default",
        slots,
        {"intent": {"name": intent_name, "confidence": 1}},
        [],
        False,
        None,
        {"name": form.name(), "validate": True, "rejected": False},
        "action_listen",
    )
