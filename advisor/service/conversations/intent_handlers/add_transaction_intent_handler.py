import json
import logging
from datetime import timezone, datetime

from advisor.data_models import IntentType
from advisor.db.db_models import Message, RawTransaction
from advisor.service.conversations.base_intent_handler import BaseIntentHandler
from advisor.service.conversations.intent_handlers.add_transaction_intent_data import (
    AddTransactionIntentData,
)
from advisor.service.conversations.intent_handlers.add_transaction_intent_result import (
    AddTransactionIntentResult,
)
from advisor.service.transactions_service import TransactionsService

logger = logging.getLogger(__name__)


class AddTransactionIntentHandler(BaseIntentHandler[AddTransactionIntentData, AddTransactionIntentResult]):
    INIT_TYPE = IntentType.ADD_TRANSACTION

    def __init__(self, transactions_service: TransactionsService):
        self.transactions_service = transactions_service

    async def prepare_intent_data(self, messages: list[Message]) -> AddTransactionIntentData:
        add_transaction_intent_data = await self.transactions_service.llm_service.invoke_structured(
            "prepare_add_transaction_intent_data_user",
            {},
            AddTransactionIntentData,
            "prepare_add_transaction_intent_data_system"
        )
        validation_errors = self._is_raw_transaction_data_valid(add_transaction_intent_data)
        if not validation_errors:
            return add_transaction_intent_data
        else:
            return AddTransactionIntentData(
                clarify=True,
                request_to_user=f"Some fields have invalid values. Please refer to this list of errors: {json.dumps(validation_errors)}"
            )

    async def run_intent(self, intent_action_data: AddTransactionIntentData) -> AddTransactionIntentResult:
        try:
            raw_transaction = RawTransaction(
                source="manual",
                type=intent_action_data.type,
                description=intent_action_data.description,
                raw_category=intent_action_data.raw_category,
                amount=intent_action_data.amount,
                currency=intent_action_data.currency,
            )
            if intent_action_data.use_current_date:
                raw_transaction.date = datetime.now(timezone.utc).date()
            else:
                raw_transaction.date = intent_action_data.date

            await self.transactions_service.add_raw_transaction(raw_transaction)
            return AddTransactionIntentResult(success=True)
        except Exception:
            logger.exception("Failed to add transaction in user intent flow")
            return AddTransactionIntentResult(
                success=False,
                message="Failed to add a raw transaction. Please try adding via in the `Transactions` tab ",
            )

    @staticmethod
    def _is_raw_transaction_data_valid(add_transaction_intent_data: AddTransactionIntentData) -> bool:
        # TODO: ! implement proper validation
        return True
