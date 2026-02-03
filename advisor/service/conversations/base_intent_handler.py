import abc
from typing import TypeVar

from advisor.db.db_models import Conversation

I = TypeVar("I")  # Intent action data
R = TypeVar("R")  # Intent action result


class BaseIntentHandler[I, R](abc.ABC):

    @abc.abstractmethod
    async def prepare_intent_data(self, conversation: Conversation) -> I: ...

    @abc.abstractmethod
    async def run_intent(self, user_id: int, intent_action_data: I) -> R: ...

    @abc.abstractmethod
    def get_success_final_message(self) -> str: ...
