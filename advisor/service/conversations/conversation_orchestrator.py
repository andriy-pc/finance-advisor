import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from advisor.data_models import (
    ConversationModel,
    ConversationRole,
    ConversationStatus,
    IntentModel,
    IntentType,
    MessageModel,
)
from advisor.db.db_async_connector import DBAsyncConnector
from advisor.db.db_models import Conversation, Message
from advisor.llm.llm_service import LLMService
from advisor.service.conversations.intent_handlers.base_intent_data import (
    BaseIntentData,
)
from advisor.service.conversations.intent_handlers.intent_handler_mapper import (
    IntentHandlerMapper,
)

logger = logging.getLogger(__name__)


class ConversationOrchestrator:

    def __init__(
        self,
        db_connector: DBAsyncConnector,
        llm_service: LLMService,
    ):
        self.db_connector = db_connector
        self.llm_service = llm_service

    @staticmethod
    def _prepare_system_message(conversation_id: UUID, content: str | None) -> MessageModel:
        if content is None:
            content = "Something went wrong :("
        return MessageModel(
            conversation_id=conversation_id,
            role=ConversationRole.SYSTEM,
            content=content,
            timestamp=datetime.now(timezone.utc),
        )

    async def get_conversations(self, user_id: int) -> list[ConversationModel]:
        async with self.db_connector.get_session() as session:
            conversations = list(
                (
                    await session.execute(
                        select(Conversation)
                        .options(selectinload(Conversation.messages))
                        .where(Conversation.user_id == user_id)
                    )
                )
                .unique()
                .scalars()
            )
            return [ConversationModel.model_validate(conversation) for conversation in conversations]

    async def handle_message(self, user_id: int, message: MessageModel) -> MessageModel:
        logger.debug(f"Handling message from user {user_id=}")

        conversation: Conversation = await self._load_conversation(user_id, message.conversation_id)
        conversation.messages.append(self.map_message_model_to_db(message))

        intent: IntentModel = await self._define_user_intent(conversation)
        logger.debug(f"For conversation with ID defined intent {intent.type}")

        if intent.type == IntentType.UNKNOWN:
            clarification_message = self._prepare_system_message(
                conversation.conversation_id,
                "Unsupported intent. Please view the list of supported actions and formulate your request accordingly",
            )
            conversation.messages.append(self.map_message_model_to_db(clarification_message))
            conversation.intent = IntentType.UNKNOWN
            await self._update_conversation_with_status(conversation, ConversationStatus.ACTIVE)
            return clarification_message

        if conversation.intent is None:
            conversation.intent = intent.type

        intent_handler = IntentHandlerMapper.get_intent_handler(intent.type)  # type: ignore
        if intent_handler is None:
            logger.debug(f"No intent handler for {intent.type} ({conversation.conversation_id=})")
            final_message = self._prepare_system_message(
                conversation.conversation_id,
                "Something went wrong and we can not process your intent. Conversation will be closed closed.",
            )
            conversation.messages.append(self.map_message_model_to_db(final_message))
            await self._update_conversation_with_status(conversation, ConversationStatus.COMPLETED_ERROR)
            return final_message

        logger.debug(f"Preparing intent data for {intent.type} ({conversation.conversation_id=})")
        intent_data: BaseIntentData = await intent_handler.prepare_intent_data(conversation)
        if intent_data.clarify or (intent_data.confidence is not None and intent_data.confidence < 0.7):
            # The second condition is a safe net in case LLM didn't set `clarify` field correctly
            logger.debug(
                f"Need clarification on intent data for {conversation.conversation_id=} and type: {intent.type}"
            )
            clarification_message = self._prepare_system_message(
                conversation.conversation_id, intent_data.request_to_user
            )
            conversation.messages.append(self.map_message_model_to_db(clarification_message))
            conversation.collected_data = intent_data.extract_collected_data()
            await self._update_conversation_with_status(conversation, ConversationStatus.ACTIVE)
            return clarification_message

        intent_action_result = await intent_handler.run_intent(user_id, intent_data)
        if intent_action_result.success:
            final_message = self._prepare_system_message(
                conversation.conversation_id, intent_handler.get_success_final_message()
            )
            conversation.messages.append(self.map_message_model_to_db(final_message))
            conversation.collected_data = intent_data.extract_collected_data()
            await self._update_conversation_with_status(conversation, ConversationStatus.COMPLETED_SUCCESS)
            return final_message
        else:
            final_message = self._prepare_system_message(
                conversation.conversation_id, "Action failed! Conversation closed."
            )
            conversation.messages.append(self.map_message_model_to_db(final_message))
            conversation.collected_data = intent_data.extract_collected_data()
            await self._update_conversation_with_status(conversation, ConversationStatus.COMPLETED_ERROR)
            return final_message

    async def _define_user_intent(self, conversation: Conversation) -> IntentModel:
        # identify user's intent

        if conversation.intent is not None:
            return IntentModel(type=conversation.intent, confidence=1)

        try:
            return await self.llm_service.invoke_structured(
                prompt_key="define_user_intent_user",
                variables={"content": conversation.messages[-1].content},
                response_model=IntentModel,
                system_prompt_key="define_user_intent_system",
            )
        except Exception:
            logger.exception("Failed to determine user intent")
            return IntentModel(
                type=IntentType.UNKNOWN, confidence=1.0, message="Failed to determine intent. Please try again"
            )

    async def _load_conversation(self, user_id: int, conversation_id: UUID | None) -> Conversation:
        if conversation_id is not None:
            async with self.db_connector.get_session() as session:
                conversation: Conversation | None = (
                    await session.execute(
                        select(Conversation)
                        .options(selectinload(Conversation.messages))
                        .where(
                            Conversation.user_id == user_id,
                            Conversation.conversation_id == conversation_id,
                            Conversation.status == ConversationStatus.ACTIVE,
                            Conversation.turn_count < Conversation.max_turns,
                        )
                    )
                ).scalar_one_or_none()

        if conversation is None:
            return await self._create_new_conversation(user_id)

        return conversation

    async def _create_new_conversation(self, user_id: int) -> Conversation:
        new_conversation = Conversation(
            user_id=user_id, status=ConversationStatus.ACTIVE, intent=None, turn_count=0, messages=[]
        )
        async with self.db_connector.get_session() as session, session.begin():
            session.add(new_conversation)
            await session.flush()
            session.expunge_all()
        return new_conversation

    async def _update_conversation_with_status(self, conversation: Conversation, status: ConversationStatus) -> None:
        conversation.status = status
        conversation.turn_count = conversation.turn_count + 1
        async with self.db_connector.get_session() as session, session.begin():
            session.add(conversation)

    @staticmethod
    def map_message_model_to_db(message_model: MessageModel) -> Message:
        return Message(**message_model.model_dump())
