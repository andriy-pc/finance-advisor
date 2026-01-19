from advisor.llm.llm_service import LLMService
from advisor.models import RawTransaction, NormalizedTransaction


class TransactionsService:

    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    async def normalize_and_categorize(self, raw_transaction: RawTransaction) -> NormalizedTransaction:
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

    async def _categorize_transaction(self, raw_transaction: RawTransaction) -> NormalizedTransaction:
        pass
