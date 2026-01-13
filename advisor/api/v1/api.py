from fastapi import APIRouter

from advisor.api.v1 import transactions

router = APIRouter(prefix="/api/v1")

# Include sub-routers
router.include_router(transactions.transactions_router)
