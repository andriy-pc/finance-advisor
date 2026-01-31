import abc
from typing import TypeVar

from advisor.db.db_models import Message

I = TypeVar("I")  # Intent action data
R = TypeVar("R")  # Intent action result


class BaseIntentHandler[I, R](abc.ABC):

    @abc.abstractmethod
    async def prepare_intent_data(self, messages: list[Message]) -> I:
        # TODO: ! decide on what is the return type
        # TODO ! implement
        ...

    @abc.abstractmethod
    async def run_intent(self, intent_action_data: I) -> R: ...
