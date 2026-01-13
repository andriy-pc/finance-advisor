from http import HTTPStatus
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from advisor.dependencies import get_session
from advisor.ingestion.factory import ParserFactory


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

    # Get user_id
    user_id = extract_user_id()

    # Get appropriate parser
    try:
        parser = ParserFactory.get_parser(file.filename)
    except ValueError as e:
        raise HTTPException(
            status_code=HTTPStatus.BAD_REQUEST, detail="Unsupported file type. Only CSV files are supported."
        ) from e

    # Parse transactions
    try:
        transactions = parser.parse_transactions(file.file, file.filename, user_id)
    except Exception as e:
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=f"Failed to parse CSV file: {str(e)}"
        ) from e

    if not transactions:
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail="No valid transactions found in the file")

    # Store transactions in database using transaction context manager
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
