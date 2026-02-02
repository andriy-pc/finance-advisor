import datetime
from decimal import Decimal
from typing import Any

from advisor.data_models import TransactionType
from advisor.service.conversations.intent_handlers.base_intent_data import (
    BaseIntentData,
)


class AddTransactionIntentData(BaseIntentData):
    type: TransactionType | None = None
    amount: Decimal | None = None
    date: datetime.date | None = None
    currency: str | None = None
    description: str | None = None
    raw_category: str | None = None

    def extract_collected_data(self) -> dict[str, Any]:
        child_only_fields = set(AddTransactionIntentData.model_fields) - set(BaseIntentData.model_fields)
        return self.model_dump(include=child_only_fields)
