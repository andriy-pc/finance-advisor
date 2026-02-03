from advisor.data_models import IntentType
from advisor.service.conversations.base_intent_handler import BaseIntentHandler, I, R


class IntentHandlerMapper:

    intent_type_mapped_handler: dict[IntentType, BaseIntentHandler[I, R]] = {}

    @classmethod
    def register_intent_handler(cls, intent_type: IntentType, intent_handler: BaseIntentHandler[I, R]) -> None:
        IntentHandlerMapper.intent_type_mapped_handler[intent_type] = intent_handler

    @classmethod
    def get_intent_handler(cls, intent_type: IntentType) -> BaseIntentHandler[I, R] | None:
        return IntentHandlerMapper.intent_type_mapped_handler.get(intent_type)
