import abc
from typing import TypeVar

from advisor.db.db_models import Conversation
from advisor.service.conversations.intent_handlers.base_intent_data import (
    BaseIntentData,
)
from advisor.service.conversations.intent_handlers.base_intent_result import (
    BaseIntentResult,
)

I = TypeVar("I", bound=BaseIntentData)  # Intent action data
R = TypeVar("R", bound=BaseIntentResult)  # Intent action result


class BaseIntentHandler[I, R](abc.ABC):

    @abc.abstractmethod
    async def prepare_intent_data(self, conversation: Conversation) -> I: ...

    @abc.abstractmethod
    async def run_intent(self, user_id: int, intent_action_data: I) -> R: ...

    @abc.abstractmethod
    def get_success_final_message(self) -> str: ...
