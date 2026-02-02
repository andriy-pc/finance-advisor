import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends

from advisor.data_models import MessageModel
from advisor.dependencies import get_conversation_orchestrator
from advisor.service.conversations.conversation_orchestrator import (
    ConversationOrchestrator,
)

logger = logging.getLogger(__name__)

chats_router = APIRouter(prefix="/chats", tags=["budgets"])


# TODO: ! duplicated method
def extract_user_id() -> int:
    """
    Hardcoded user extraction function.

    For MVP Stage 1, all transactions are stored for user_id=1.
    In future iterations, this will extract the user from authentication context.
    """
    return 1


@chats_router.post("/message")
async def handle_user_message(
    message: MessageModel,
    conversation_orchestrator: Annotated[ConversationOrchestrator, Depends(get_conversation_orchestrator)],
) -> dict[str, Any]:
    response_message = await conversation_orchestrator.handle_message(extract_user_id(), message)

    return response_message.model_dump()
