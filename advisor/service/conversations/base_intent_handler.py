import abc
from typing import TypeVar

from advisor.db.db_models import Conversation, Message

I = TypeVar("I")  # Intent action data
R = TypeVar("R")  # Intent action result


class BaseIntentHandler[I, R](abc.ABC):

    @abc.abstractmethod
    async def prepare_intent_data(self, conversation: Conversation) -> I:
        # TODO: ! decide on what is the return type
        # TODO ! implement
        ...

    @abc.abstractmethod
    async def run_intent(self, user_id: int, intent_action_data: I) -> R: ...
