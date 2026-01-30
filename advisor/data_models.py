import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class TransactionType(str, Enum):
    """Type of financial transaction."""

    DEBIT = "debit"  # Outcome
    CREDIT = "credit"  # Income


class SpendingType(str, Enum):
    """Classification of spending pattern."""

    RECURRING = "recurring"
    DISCRETIONARY = "discretionary"


class RecurrenceStatus(str, Enum):
    UNKNOWN = "unknown"
    INFERRED = "inferred"
    CONFIRMED = "confirmed"


class PeriodEnum(str, Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"


class BudgedThresholdSourceEnum(Enum):
    USER_DEFINED = "user_defined"
    SYSTEM_SUGGESTED = "system_suggested"


class CategoryPredictionModel(BaseModel):
    category: str = Field(description="The best matching category from the list")
    confidence_score: float = Field(description="Confidence score between 0 and 1")


class RawTransactionModel(BaseModel):
    id: int
    external_id: UUID | None = None
    type: TransactionType
    amount: Decimal | None = None
    date: datetime.date | None = None
    currency: str | None
    description: str | None = None
    source: str  # CSV / manual / bank
    raw_category: str | None
    user_id: int | None = None
    raw_data: dict[str, Any]


class CategorizationResultModel(BaseModel):
    """Result of transaction categorization with confidence score."""

    predicted_category: str = Field(
        ...,
        description="Best matching user-defined category, or suggested category with '_MISSING' suffix if no match found",
    )
    category_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for the categorization (0.0 = no confidence, 1.0 = very confident)",
    )
    reasoning: str = Field(
        ..., description="Brief explanation of why this category was chosen and the confidence level"
    )

    @field_validator("category_confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v


class NormalizedTransactionModel(BaseModel):
    id: str | None = None
    external_id: UUID | None = None

    type: TransactionType
    amount: Decimal
    date: datetime.date
    currency: str
    description: str | None
    source: str  # CSV / manual / bank

    raw_category: str  # taken from the input (CSV / manu
    predicted_category: str
    category_confidence: float  # for category
    resolved_category: str  # resolved with LLM

    recurrence_status: RecurrenceStatus
    recurrence_confidence: Decimal | None = None
    recurrence_period: PeriodEnum | None = None

    user_id: int | None = None
    raw_transaction_id: int | None = None


class BudgetThresholdModel(BaseModel):
    id: str
    category: str

    period: PeriodEnum
    limit_amount: Decimal
    currency: str

    source: BudgedThresholdSourceEnum
    is_active: bool

    start_date: datetime.date
    end_date: datetime.date | None


class CategorySpendModel(BaseModel):
    category: str
    total_amount: Decimal
    currency: str
    transaction_count: int


class BudgetStatusModel(BaseModel):
    category: str
    limit_amount: Decimal | None = None
    spent_amount: Decimal | None = None
    remaining_amount: Decimal | None = None
    currency: str
    is_overspent: bool


class FinancialPeriodSnapshotModel(BaseModel):
    period: PeriodEnum
    start_date: datetime.date
    end_date: datetime.date

    total_income: Decimal
    total_outcome: Decimal
    savings: Decimal
    savings_rate: Decimal  # derived: savings / income

    categories_spends: list[CategorySpendModel]
    budgets_statuses: list[BudgetStatusModel]


class FinancialStateModel(BaseModel):

    transactions: list[NormalizedTransactionModel]
    thresholds: list[BudgetThresholdModel]

    finance_snapshot: FinancialPeriodSnapshotModel
