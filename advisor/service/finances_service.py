from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from advisor.data_models import (
    CategorySpendModel,
    FinancialPeriodSnapshotModel,
    PeriodEnum,
    TransactionType,
)
from advisor.db.db_async_connector import DBAsyncConnector
from advisor.db.db_models import FinancialPeriodSnapshot, NormalizedTransaction
from advisor.service.budgets_service import BudgetsService
from advisor.service.transactions_service import TransactionsService


class FinancesService:

    def __init__(
        self, db_connector: DBAsyncConnector, transactions_service: TransactionsService, budgets_service: BudgetsService
    ):
        self.db_connector = db_connector
        self.transactions_service = transactions_service
        self.budgets_service = budgets_service

    async def get_up_to_date_financial_snapshot_current_month(
        self,
        user_id: int,
        current_month: int,
        current_year: int,
    ) -> FinancialPeriodSnapshotModel:

        start_date = datetime(current_year, current_month, 1)
        end_date = datetime(current_year, current_month + 1, 1) - timedelta(days=1)

        async with self.db_connector.get_session() as session:
            financial_snapshot = (
                await session.execute(
                    select(FinancialPeriodSnapshot).where(
                        FinancialPeriodSnapshot.user_id == user_id,
                        FinancialPeriodSnapshot.start_date == start_date,
                        FinancialPeriodSnapshot.end_date == end_date,
                    )
                )
            ).scalar_one_or_none()

            transactions_not_included_in_snapshot = list(
                (
                    await session.execute(
                        select(NormalizedTransaction).where(
                            NormalizedTransaction.user_id == user_id,
                            NormalizedTransaction.date >= start_date,
                            NormalizedTransaction.date < end_date,
                            NormalizedTransaction.financial_period_snapshot_id.is_(None),
                        )
                    )
                ).scalars()
            )

            if financial_snapshot is not None and len(transactions_not_included_in_snapshot) == 0:
                return self.map_db_snapshot_to_model(financial_snapshot)

            financial_snapshot = await self._recalculate_finance_snapshot_for_period(
                user_id, start_date, end_date, financial_snapshot, transactions_not_included_in_snapshot
            )

        async with self.db_connector.get_session() as session, session.begin():
            session.add(financial_snapshot)
            # to get id for transactions references
            await session.flush()
            session.expunge(financial_snapshot)

            for transaction in transactions_not_included_in_snapshot:
                transaction.financial_period_snapshot_id = financial_snapshot.id

            session.add_all(transactions_not_included_in_snapshot)

        return self.map_db_snapshot_to_model(financial_snapshot)

    async def _recalculate_finance_snapshot_for_period(
        self,
        user_id: int,
        start_date: date,
        end_date: date,
        financial_snapshot: FinancialPeriodSnapshot | None,
        transactions_not_included_in_snapshot: list[Any],
    ) -> FinancialPeriodSnapshot:
        category_mapped_spend_model: dict[str, CategorySpendModel] = {}
        if financial_snapshot is not None:
            category_mapped_spend_model = {
                category_spend_model["category"]: CategorySpendModel(**category_spend_model)
                for category_spend_model in financial_snapshot.categories_spends
            }

        missed_outcome: Decimal = Decimal(0)
        missed_income: Decimal = Decimal(0)

        # Calculating data for transactions that were not included in the latest finance snapshot
        for transaction in transactions_not_included_in_snapshot:
            if transaction.type == TransactionType.CREDIT:
                missed_outcome += transaction.amount
            else:
                missed_income += Decimal(transaction.amount)

            category_spend_model = category_mapped_spend_model.get(transaction.resolved_category)
            if category_spend_model is None:
                category_mapped_spend_model[transaction.resolved_category] = CategorySpendModel(
                    category=transaction.resolved_category,
                    total_amount=transaction.amount,
                    currency=transaction.currency,
                    transaction_count=1,
                )
            else:
                category_spend_model.total_amount += transaction.amount
                category_spend_model.transaction_count += 1

        budget_statuses_models = await self.budgets_service.calculate_budget_statuses_per_category_spends(
            user_id, start_date, end_date, list(category_mapped_spend_model.values())
        )
        budget_statuses = [
            budget_status_model.model_dump(mode="json") for budget_status_model in budget_statuses_models
        ]

        categories_spends = [
            category_spend_model.model_dump(mode="json")
            for category_spend_model in category_mapped_spend_model.values()
        ]

        # Creating / Updating finance snapshot
        if financial_snapshot is None:
            savings_rate = Decimal(0.0)
            if missed_income > 0 and (missed_income - missed_outcome) > 0:
                savings_rate = ((missed_income - missed_outcome) / missed_income) * Decimal(100)

            financial_snapshot = FinancialPeriodSnapshot(
                period=PeriodEnum.MONTHLY,
                start_date=start_date,
                end_date=end_date,
                total_income=missed_income,
                total_outcome=missed_outcome,
                savings=missed_income - missed_outcome,
                savings_rate=savings_rate,
                categories_spends=categories_spends,
                budgets_statuses=budget_statuses,
                user_id=user_id,
                created_at=datetime.now(timezone.utc),
                computed_at=datetime.now(timezone.utc),
            )
        else:
            savings_rate = Decimal(0)
            total_income = financial_snapshot.total_income + missed_income
            total_outcome = financial_snapshot.total_outcome + missed_outcome

            if total_income > 0:
                savings_rate = ((total_income - total_outcome) / total_income) * Decimal(100)

            financial_snapshot.total_income = total_income
            financial_snapshot.total_outcome += missed_outcome
            financial_snapshot.savings = total_income - total_outcome
            financial_snapshot.savings_rate = savings_rate
            financial_snapshot.computed_at = datetime.now(timezone.utc)

            financial_snapshot.categories_spends = categories_spends
            financial_snapshot.budgets_statuses = budget_statuses
        return financial_snapshot

    @staticmethod
    def map_db_snapshot_to_model(db_snapshot: FinancialPeriodSnapshot) -> FinancialPeriodSnapshotModel:
        return FinancialPeriodSnapshotModel(**db_snapshot.to_dict())
