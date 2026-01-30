import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends

from advisor.dependencies import get_finances_service
from advisor.service.finances_service import FinancesService

logger = logging.getLogger(__name__)

finances_router = APIRouter(prefix="/finances", tags=["budgets"])


# TODO: ! duplicated method
def extract_user_id() -> int:
    """
    Hardcoded user extraction function.

    For MVP Stage 1, all transactions are stored for user_id=1.
    In future iterations, this will extract the user from authentication context.
    """
    return 1


@finances_router.get("/current-month")
async def get_current_month_financial_state(
    finances_service: Annotated[FinancesService, Depends(get_finances_service)],
) -> dict[str, Any]:
    current_month = datetime.now(timezone.utc).month
    current_year = datetime.now(timezone.utc).year
    financial_state = await finances_service.get_up_to_date_financial_snapshot_current_month(
        extract_user_id(), current_month, current_year
    )

    return {"financial_state": financial_state.model_dump(mode="json")}
