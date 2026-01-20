import datetime
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


class CategoryPrediction(BaseModel):
    category: str = Field(description="The best matching category from the list")
    confidence_score: float = Field(description="Confidence score between 0 and 1")


class RawTransaction(BaseModel):
    id: int
    external_id: UUID | None = None
    type: TransactionType
    amount: float | None = None
    date: datetime.date | None = None
    currency: str | None
    description: str | None = None
    source: str  # CSV / manual / bank
    raw_category: str | None
    user_id: int | None = None
    raw_data: dict[str, Any]


class CategorizationResult(BaseModel):
    """Result of transaction categorization with confidence score."""

    predicted_category: str = Field(
        ...,
        description="Best matching user-defined category, or suggested category with '_MISSING' suffix if no match found"
    )
    category_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for the categorization (0.0 = no confidence, 1.0 = very confident)"
    )
    reasoning: str = Field(
        ...,
        description="Brief explanation of why this category was chosen and the confidence level"
    )

    @field_validator('category_confidence')
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError('Confidence must be between 0.0 and 1.0')
        return v


class NormalizedTransaction(BaseModel):
    id: str | None = None
    external_id: UUID | None = None

    type: TransactionType
    amount: float
    date: datetime.date
    currency: str
    description: str | None
    source: str  # CSV / manual / bank

    raw_category: str  # taken from the input (CSV / manu
    predicted_category: str
    category_confidence: float  # for category
    resolved_category: str  # resolved with LLM

    recurrence_status: RecurrenceStatus
    recurrence_confidence: float | None = None
    recurrence_period: PeriodEnum | None = None


class BudgetThreshold(BaseModel):
    id: str
    category: str

    period: PeriodEnum
    limit_amount: float
    currency: str

    source: BudgedThresholdSourceEnum
    is_active: bool

    start_date: datetime.date
    end_date: datetime.date | None


class CategorySpend(BaseModel):
    category: str
    total_amount: float
    currency: str
    transaction_count: int


class BudgetStatus(BaseModel):
    category: str
    limit_amount: float
    spent_amount: float
    remaining_amount: float
    currency: str
    is_overspent: bool


class FinancialPeriodState(BaseModel):
    period: PeriodEnum
    start_date: datetime.date
    end_date: datetime.date

    total_income: float
    total_outcome: float
    savings: float
    savings_rate: float  # derived: savings / income

    category_spend: list[CategorySpend]
    budget_status: list[BudgetStatus]


class FinancialState(BaseModel):
    currency: str

    transactions: list[NormalizedTransaction]
    budgets: list[BudgetThreshold]

    current_period: FinancialPeriodState
