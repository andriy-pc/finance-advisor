import logging
from http import HTTPStatus
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from advisor.db.db_models import NormalizedTransaction, RawTransaction
from advisor.dependencies import get_session, get_transactions_service
from advisor.ingestion.factory import ParserFactory
from advisor.service.transactions_service import TransactionsService

logger = logging.getLogger(__name__)


def extract_user_id() -> int:
    """
    Hardcoded user extraction function.

    For MVP Stage 1, all transactions are stored for user_id=1.
    In future iterations, this will extract the user from authentication context.
    """
    return 1


transactions_router = APIRouter(prefix="/transactions", tags=["transactions"])


@transactions_router.post("/bulk", status_code=HTTPStatus.CREATED)
async def bulk_upload_transactions(
    db_session: Annotated[AsyncSession, Depends(get_session)],
    file: UploadFile = File(...),
) -> dict[str, Any]:
    """
    Bulk upload transactions from CSV file.

    This endpoint:
    1. Accepts a CSV file upload
    2. Extracts the user_id (currently hardcoded to 1)
    3. Parses the CSV file into RawTransaction records
    4. Stores all transactions in the database

    Args:
        file: CSV file containing transaction data
        db_session: Database session

    Returns:
        Dictionary with success message and count of imported transactions

    Raises:
        HTTPException: If file is invalid or processing fails
    """
    # Validate file
    if not file.filename:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="Filename is missing")

    user_id = extract_user_id()

    try:
        parser = ParserFactory.get_parser(file.filename)
    except ValueError as e:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Unsupported file type. Only CSV files are supported."
        ) from e

    try:
        transactions = parser.parse_transactions(file.file, file.filename, user_id)
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=f"Failed to parse CSV file: {str(e)}"
        ) from e

    if not transactions:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="No valid transactions found in the file")

    try:
        async with db_session.begin():
            db_session.add_all(transactions)
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=f"Failed to store transactions: {str(e)}"
        ) from e

    return {
        "message": "Transactions imported successfully",
        "count": len(transactions),
        "user_id": user_id,
    }


@transactions_router.post("/categorize", status_code=HTTPStatus.OK)
async def bulk_categorization(
    db_session: Annotated[AsyncSession, Depends(get_session)],
    transactions_service: Annotated[TransactionsService, Depends(get_transactions_service)],
) -> dict[str, Any]:
    # TODO: ! this logic must be implemented as a background job due to long time-consuming interaction
    raw_transactions: list[RawTransaction] = []
    async with db_session.begin():
        try:
            raw_result = await db_session.execute(
                select(RawTransaction).outerjoin(NormalizedTransaction).where(NormalizedTransaction.id.is_(None))
            )
            raw_transactions.extend(raw_result.scalars().all())

            if not raw_transactions:
                return {"message": "All the transactions are categorized"}
        except Exception:
            logging.exception("Failed to categorize transactions")

        categorized_transactions = []
        try:
            categories = []
            for raw_db_transaction in raw_transactions:
                raw_transaction = transactions_service.map_raw_db_transaction_to_pydantic_model(raw_db_transaction)
                normalized_model = await transactions_service.normalize_and_categorize(raw_transaction, categories)
                normalized_db_model = transactions_service.map_normalized_transaction_to_db_model(normalized_model)
                categorized_transactions.append(normalized_db_model)
        except Exception:
            logger.exception("Exception occurred during normalizing categories")

        db_session.add_all(categorized_transactions)

    return {"message": "Categorized transactions successfully"}
