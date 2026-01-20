from advisor.llm.llm_service import LLMService
from advisor.models import RawTransaction, NormalizedTransaction, CategorizationResult, RecurrenceStatus


class TransactionsService:

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    async def normalize_and_categorize(self, raw_transaction: RawTransaction, categories: list[str]) -> NormalizedTransaction:
        normalized_transaction = await self._normalize_transaction(raw_transaction)
        categorized_transaction = await self._categorize_transaction(normalized_transaction)
        return categorized_transaction

    async def _normalize_transaction(self, raw_transaction: RawTransaction) -> RawTransaction:
        return await self.llm_service.invoke_structured(
            prompt_key="normalize_transaction_user",
            variables={"transaction": raw_transaction.model_dump()},
            response_model=RawTransaction,
            system_prompt_key="normalize_transaction_system"
        )

    async def _categorize_transaction(self, raw_transaction: RawTransaction, categories: list[str]) -> NormalizedTransaction:
        categorization_result = await self.llm_service.invoke_structured(
            prompt_key="categorize_transaction_user",
            variables={"transaction": raw_transaction.model_dump(), "user_categories": categories},
            response_model=CategorizationResult,
            system_prompt_key="categorize_transaction_system"
        )

        return NormalizedTransaction(
            type=raw_transaction.type,
            amount=raw_transaction.amount,
            date=raw_transaction.date,
            currency=raw_transaction.currency,
            description=raw_transaction.description,
            source=raw_transaction.source,
            raw_category=raw_transaction.raw_category,
            predicted_category=categorization_result.predicted_category,
            category_confidence=categorization_result.category_confidence,
            resolved_category=categorization_result.predicted_category, # TODO: ! this should be dynamic based on the confidence !
            recurrence_status=RecurrenceStatus.UNKNOWN,
            recurrence_confidence=0.0,
            recurrence_period=None,
        )
