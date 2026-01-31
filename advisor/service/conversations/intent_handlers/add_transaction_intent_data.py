import datetime
from decimal import Decimal

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
