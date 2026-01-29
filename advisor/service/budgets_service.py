from datetime import date

from sqlalchemy import select

from advisor.data_models import (
    BudgetStatusModel,
    CategorySpendModel,
)
from advisor.db.db_async_connector import DBAsyncConnector
from advisor.db.db_models import BudgetThreshold


class BudgetsService:

    def __init__(
        self,
        db_connector: DBAsyncConnector,
    ):
        self.db_connector = db_connector

    async def calculate_budget_statuses_per_category_spends(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
        category_spends: list[CategorySpendModel],
    ) -> list[BudgetStatusModel]:
        async with self.db_connector.get_session() as session:
            budget_thresholds = list(
                (
                    await session.execute(
                        select(BudgetThreshold).where(
                            BudgetThreshold.user_id == user_id,
                            BudgetThreshold.start_date <= start_date,
                            BudgetThreshold.end_date >= end_date,
                            BudgetThreshold.is_active.is_(True),
                        )
                    )
                ).scalars()
            )

            if not budget_thresholds:
                return []

            category_mapped_budget_threshold: dict[str, BudgetThreshold] = {
                budget_threshold.category.name: budget_threshold for budget_threshold in budget_thresholds
            }

            category_mapped_budget_statuses: dict[str, BudgetStatusModel] = {}

            for category_spend in category_spends:
                budget_threshold = category_mapped_budget_threshold.get(category_spend.category)

                limit_amount = None
                remaining_amount = None
                is_overspent = False
                if budget_threshold is not None:
                    limit_amount = budget_threshold.limit_amount
                    remaining_amount = budget_threshold.limit_amount - category_spend.total_amount
                    is_overspent = remaining_amount <= 0

                budged_status = BudgetStatusModel(
                    category=category_spend.category,
                    limit_amount=limit_amount,
                    spent_amount=category_spend.total_amount,
                    remaining_amount=remaining_amount,
                    currency=category_spend.currency,
                    is_overspent=is_overspent,
                )
                category_mapped_budget_statuses[category_spend.category] = budged_status

            return list(category_mapped_budget_statuses.values())
