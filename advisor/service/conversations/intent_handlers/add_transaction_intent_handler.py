import json
import logging
from datetime import datetime, timezone

from advisor.data_models import IntentType
from advisor.db.db_models import Conversation, RawTransaction
from advisor.service.conversations.base_intent_handler import BaseIntentHandler
from advisor.service.conversations.intent_handlers.add_transaction_intent_data import (
    AddTransactionIntentData,
)
from advisor.service.conversations.intent_handlers.add_transaction_intent_result import (
    AddTransactionIntentResult,
)
from advisor.service.transactions_service import TransactionsService
from advisor.service.users_service import UsersService

logger = logging.getLogger(__name__)


class AddTransactionIntentHandler(BaseIntentHandler[AddTransactionIntentData, AddTransactionIntentResult]):
    INIT_TYPE = IntentType.ADD_TRANSACTION

    def __init__(self, users_service: UsersService, transactions_service: TransactionsService):
        self.users_service = users_service
        self.transactions_service = transactions_service

    # TODO: ! add exception handling !
    async def prepare_intent_data(self, conversation: Conversation) -> AddTransactionIntentData:
        messages = conversation.messages
        collected_messages = [{"role": message.role, "content": message.content} for message in messages]
        category_names = [category.name for category in await self.users_service.get_categories(conversation.user_id)]
        add_transaction_intent_data = await self.transactions_service.llm_service.invoke_structured(
            "prepare_add_transaction_intent_data_user",
            {
                "collected_messages": collected_messages,
                "categories": category_names,
            },
            AddTransactionIntentData,
            "prepare_add_transaction_intent_data_system",
            {
                "current_date": datetime.now(timezone.utc).isoformat(),
                "default_currency": self.users_service.get_default_currency(),
                "collected_data": conversation.collected_data,
            },
        )
        validation_errors = self._validate_raw_transaction_data(add_transaction_intent_data)
        if not validation_errors:
            if add_transaction_intent_data.use_current_date:
                add_transaction_intent_data.date = datetime.now(timezone.utc).date()
            return add_transaction_intent_data
        else:
            return AddTransactionIntentData(
                clarify=True,
                request_to_user=f"Some fields have invalid values. Please refer to this list of errors: {json.dumps(validation_errors)}",
            )

    async def run_intent(self, user_id: int, intent_action_data: AddTransactionIntentData) -> AddTransactionIntentResult:
        try:
            currency = intent_action_data.currency
            if currency is None:
                currency = await self.users_service.get_default_currency()
            raw_transaction = RawTransaction(
                source="manual",
                type=intent_action_data.type,
                description=intent_action_data.description,
                raw_category=intent_action_data.raw_category,
                amount=intent_action_data.amount,
                currency=currency,
                user_id=user_id,
                raw_data=intent_action_data.extract_collected_data(),
            )
            if intent_action_data.use_current_date:
                raw_transaction.date = datetime.now(timezone.utc).date()
            else:
                raw_transaction.date = intent_action_data.date  # type: ignore

            await self.transactions_service.add_raw_transaction(raw_transaction)
            return AddTransactionIntentResult(success=True)
        except Exception:
            logger.exception("Failed to add transaction in user intent flow")
            return AddTransactionIntentResult(
                success=False,
                message="Failed to add a raw transaction. Please try adding via in the `Transactions` tab ",
            )

    @staticmethod
    def _validate_raw_transaction_data(add_transaction_intent_data: AddTransactionIntentData) -> list[str]:
        # TODO: ! implement proper validation
        return []
