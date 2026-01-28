import csv
import io
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, BinaryIO, List
from uuid import uuid4

from advisor.db.db_models import RawTransaction
from advisor.ingestion.base_parser import BaseParser
from advisor.data_models import TransactionType

DEFAULT_CURRENCY = "USD"

logger = logging.getLogger(__name__)


class CSVParser(BaseParser):

    def parse_transactions(self, file_content: BinaryIO, filename: str, user_id: int) -> List[RawTransaction]:
        content_str = file_content.read().decode("utf-8")
        in_memory_file = io.StringIO(content_str)
        reader = csv.DictReader(in_memory_file)

        transactions = []
        for row in reader:
            date_str = row.get("Date") or row.get("date")
            amount_str = row.get("Amount") or row.get("amount")
            description = row.get("Description") or row.get("description") or row.get("Memo") or ""
            raw_category = row.get("Category") or row.get("category")

            if not date_str or not amount_str:
                logger.warning(f"Skipping row due to missing date or amount. Row: {row}")
                continue

            try:
                transaction_date = (
                    datetime.fromisoformat(date_str).date()
                    if "-" in date_str
                    else datetime.strptime(date_str, "%m/%d/%Y").date()
                )
                amount_value = Decimal(amount_str)
                transaction_type = TransactionType.DEBIT if amount_value < 0 else TransactionType.CREDIT
                absolute_amount = abs(amount_value)

                raw_data: dict[str, Any] = dict(row)

                transaction = RawTransaction(
                    external_id=uuid4(),
                    source="csv",
                    type=transaction_type,
                    description=description,
                    raw_category=raw_category,
                    amount=absolute_amount,
                    currency=DEFAULT_CURRENCY,
                    date=transaction_date,
                    user_id=user_id,
                    raw_data=raw_data,
                )
                transactions.append(transaction)
            except Exception:
                logger.exception(f"Skipping row due to error. Row: {row}")
                continue

        return transactions
