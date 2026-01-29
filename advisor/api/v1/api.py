from fastapi import APIRouter

from advisor.api.v1 import finances, transactions

router = APIRouter(prefix="/api/v1")

# Include sub-routers
router.include_router(transactions.transactions_router)
router.include_router(finances.finances_router)
