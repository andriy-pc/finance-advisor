from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from advisor.db.db_async_connector import DBAsyncConnector
from advisor.llm.lite_llm_client import LiteLLMClient
from advisor.llm.llm_service import LLMService
from advisor.llm.prompt_manager import PromptManager
from advisor.service.transactions_service import TransactionsService
from advisor.settings import ProjectSettings

db_connector: DBAsyncConnector | None = None
settings: ProjectSettings | None = None

_transactions_service: "TransactionsService | None" = None
_llm_service: "LLMService | None" = None
_prompt_manager: "PromptManager | None" = None
_lite_llm_client: "LiteLLMClient | None" = None


def get_lite_llm_client() -> "LiteLLMClient":
    global _lite_llm_client
    if _lite_llm_client is None:
        llm_settings = get_project_settings().llm_integration_settings
        if llm_settings is None:
            raise ValueError("llm_integration_settings is not set")
        _lite_llm_client = LiteLLMClient(llm_settings)
    return _lite_llm_client


def get_prompt_manager() -> "PromptManager":
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager


def get_llm_service() -> "LLMService":
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService(get_lite_llm_client(), get_prompt_manager())
    return _llm_service


def get_transactions_service() -> "TransactionsService":
    global _transactions_service
    if _transactions_service is None:
        _transactions_service = TransactionsService(get_llm_service())
    return _transactions_service


def get_project_settings() -> ProjectSettings:
    global settings

    if settings is None:
        settings = ProjectSettings()
    return settings


def get_db_connector() -> DBAsyncConnector:
    global db_connector

    if db_connector is None:
        url = get_project_settings().sql_connection_url
        if not url:
            raise ValueError("sql_connection_url is not set")
        db_connector = DBAsyncConnector(url)
    return db_connector


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with get_db_connector().get_session() as session:
        yield session
