import datetime

from advisor.db import db_models
from advisor.llm.llm_service import LLMService
from advisor.models import (
    CategorizationResult,
    NormalizedTransaction,
    RawTransaction,
    RecurrenceStatus,
)


class TransactionsService:

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    async def normalize_and_categorize(
        self, raw_transaction: RawTransaction, categories: list[str]
    ) -> NormalizedTransaction:
        normalized_transaction = await self._normalize_transaction(raw_transaction)
        categorized_transaction = await self._categorize_transaction(normalized_transaction, categories)

        categorized_transaction.raw_transaction_id = raw_transaction.id
        categorized_transaction.user_id = raw_transaction.user_id
        return categorized_transaction

    async def _normalize_transaction(self, raw_transaction: RawTransaction) -> RawTransaction:
        return await self.llm_service.invoke_structured(
            prompt_key="normalize_transaction_user",
            variables={"transaction": raw_transaction.model_dump()},
            response_model=RawTransaction,
            system_prompt_key="normalize_transaction_system",
        )

    async def _categorize_transaction(
        self, raw_transaction: RawTransaction, categories: list[str]
    ) -> NormalizedTransaction:
        categorization_result = await self.llm_service.invoke_structured(
            prompt_key="categorize_transaction_user",
            variables={"transaction": raw_transaction.model_dump(), "user_categories": categories},
            response_model=CategorizationResult,
            system_prompt_key="categorize_transaction_system",
        )

        return NormalizedTransaction(
            type=raw_transaction.type,
            amount=raw_transaction.amount if raw_transaction.amount is not None else 0.0,
            date=raw_transaction.date if raw_transaction.date is not None else datetime.date.today(),
            currency=raw_transaction.currency if raw_transaction.currency is not None else "USD",
            description=raw_transaction.description,
            source=raw_transaction.source,
            raw_category=raw_transaction.raw_category if raw_transaction.raw_category is not None else "",
            predicted_category=categorization_result.predicted_category,
            category_confidence=categorization_result.category_confidence,
            resolved_category=categorization_result.predicted_category,  # TODO: ! this should be dynamic based on the confidence !
            recurrence_status=RecurrenceStatus.UNKNOWN,
            recurrence_confidence=0.0,
            recurrence_period=None,
        )

    @staticmethod
    def map_raw_db_transaction_to_pydantic_model(raw_db_transaction: db_models.RawTransaction) -> RawTransaction:
        return RawTransaction(**raw_db_transaction.to_dict())

    @staticmethod
    def map_normalized_transaction_to_db_model(
        normalized_db_model: NormalizedTransaction,
    ) -> db_models.NormalizedTransaction:
        return db_models.NormalizedTransaction(**normalized_db_model.model_dump())
