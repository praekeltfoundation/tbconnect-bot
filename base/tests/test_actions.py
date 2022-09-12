import pytest
from rasa_sdk import Tracker
from rasa_sdk.events import AllSlotsReset, SlotSet
from rasa_sdk.executor import CollectingDispatcher

from base.actions.actions import SetActivationAction
from base.tests import utils


class TestActionSetActivation:
    @pytest.mark.asyncio
    async def test_set_activation(self):
        """
        Should set the activation if is one.
        """
        action = SetActivationAction()
        dispatcher = CollectingDispatcher()

        action.get_activation = utils.AsyncMock()
        action.get_activation.return_value = {
            "fields": {"msisdn": "+27820001001", "tb_activation": "tb_soccer_1_2022"}
        }
        events = await action.run(
            dispatcher,
            Tracker(
                "27820001001",
                {},
                {},
                [],
                False,
                None,
                {},
                "action_listen",
            ),
            {},
        )
        assert SlotSet("activation", "tb_soccer_1_2022") in events

    @pytest.mark.asyncio
    async def test_set_activation_and_reset_slots(self):
        """
        Should set the activation if is one, and reset all slots if on
        a shared/agent device.
        """
        action = SetActivationAction()
        dispatcher = CollectingDispatcher()

        action.get_activation = utils.AsyncMock()
        action.get_activation.return_value = {
            "fields": {
                "msisdn": "+27820001001",
                "tb_activation": "tb_soccer_1_2022_agent",
            }
        }
        events = await action.run(
            dispatcher,
            Tracker(
                "27820001001",
                {},
                {},
                [],
                False,
                None,
                {},
                "action_listen",
            ),
            {},
        )
        assert AllSlotsReset() in events
        assert SlotSet("activation", "tb_soccer_1_2022_agent") in events

    @pytest.mark.asyncio
    async def test_activation_not_set(self):
        """
        Should not set the activation if there is none.
        """
        action = SetActivationAction()
        dispatcher = CollectingDispatcher()

        action.get_activation = utils.AsyncMock()
        action.get_activation.return_value = {"fields": {"msisdn": "+27820001001"}}
        events = await action.run(
            dispatcher,
            Tracker("27820001001", {}, {}, [], False, None, {}, "action_listen"),
            {},
        )
        assert SlotSet("activation", None) not in events
