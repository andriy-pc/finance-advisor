from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import UUID

from advisor.models import (
    BudgedThresholdSourceEnum,
    PeriodEnum,
    RecurrenceStatus,
    TransactionType,
)


class Base(DeclarativeBase):
    """Base class for all database models."""

    def to_dict(self) -> dict[str, Any]:
        """Convert model instance to dictionary."""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            result[column.name] = value
        return result

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Base):
            return NotImplemented
        return self.to_dict() == other.to_dict()

    def __hash__(self) -> int:
        return super().__hash__()


class User(Base):
    __tablename__ = "USER"

    id: Mapped[int] = mapped_column(BigInteger(), primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(UUID(as_uuid=True), default=uuid4, unique=True, nullable=False)

    # User profile
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Authentication (placeholder - implement proper auth later)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # User preferences
    default_currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    raw_transactions: Mapped[list["RawTransaction"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    normalized_transactions: Mapped[list["NormalizedTransaction"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    categories: Mapped[list["Category"]] = relationship(cascade="all, delete-orphan")
    budget_thresholds: Mapped[list["BudgetThreshold"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    financial_period_snapshots: Mapped[list["FinancialPeriodSnapshot"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

class GlobalCategory(Base):
    __tablename__ = "GLOBAL_CATEGORY"

    id: Mapped[int] = mapped_column(BigInteger(), primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(UUID(as_uuid=True), default=uuid4, unique=True, nullable=False)

    # Category details
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_discretionary: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

class Category(Base):
    __tablename__ = "CATEGORY"

    id: Mapped[int] = mapped_column(BigInteger(), primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(UUID(as_uuid=True), default=uuid4, unique=True, nullable=False)

    # Category details
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_discretionary: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # System vs user-defined

    # User relationship
    user_id: Mapped[int] = mapped_column(ForeignKey("USER.id"), nullable=False, index=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (Index("ix_category_user_name", "user_id", "name", unique=True),)


class RawTransaction(Base):
    """Raw transaction as ingested from CSV/bank/manual entry."""

    __tablename__ = "RAW_TRANSACTION"

    id: Mapped[int] = mapped_column(BigInteger(), primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(UUID(as_uuid=True), default=uuid4, unique=True, nullable=False)

    # Transaction details
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # bank_name / csv / manual
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    raw_category: Mapped[str | None] = mapped_column(String(100), nullable=True)  # Category from source
    amount: Mapped[Decimal] = mapped_column(Numeric(precision=15, scale=2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # User relationship
    user_id: Mapped[int] = mapped_column(ForeignKey("USER.id"), nullable=False, index=True)
    user: Mapped["User"] = relationship(back_populates="raw_transactions")

    # Flexible storage for original data
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationship to normalized transaction
    normalized_transaction: Mapped[Optional["NormalizedTransaction"]] = relationship(back_populates="raw_transaction")

    __table_args__ = (Index("ix_raw_transaction_user_date", "user_id", "date"),)


class NormalizedTransaction(Base):
    """Normalized transaction with LLM categorization and recurrence detection."""

    __tablename__ = "NORMALIZED_TRANSACTION"

    id: Mapped[int] = mapped_column(BigInteger(), primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(UUID(as_uuid=True), default=uuid4, unique=True, nullable=False)

    # Transaction details
    type: Mapped[TransactionType] = mapped_column(Enum(TransactionType), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(precision=15, scale=2), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # CSV / manual / bank

    # Category information
    raw_category: Mapped[str] = mapped_column(String(100), nullable=False)  # From input
    predicted_category: Mapped[str] = mapped_column(String(100), nullable=False)  # LLM prediction
    category_confidence: Mapped[Decimal] = mapped_column(Numeric(precision=5, scale=4), nullable=False)  # 0-1
    resolved_category: Mapped[str] = mapped_column(String(100), nullable=False)  # Final resolved category

    # Recurrence detection
    recurrence_status: Mapped[RecurrenceStatus] = mapped_column(Enum(RecurrenceStatus), nullable=False)
    recurrence_confidence: Mapped[Decimal | None] = mapped_column(Numeric(precision=5, scale=4), nullable=True)
    recurrence_period: Mapped[PeriodEnum | None] = mapped_column(Enum(PeriodEnum), nullable=True)

    # User relationship
    user_id: Mapped[int] = mapped_column(ForeignKey("USER.id"), nullable=False, index=True)
    user: Mapped["User"] = relationship(back_populates="normalized_transactions")

    # Link to raw transaction
    raw_transaction_id: Mapped[int | None] = mapped_column(ForeignKey("RAW_TRANSACTION.id"), nullable=True, unique=True)
    raw_transaction: Mapped[Optional["RawTransaction"]] = relationship(back_populates="normalized_transaction")

    # Link to financial period snapshot
    financial_period_snapshot_id: Mapped[int | None] = mapped_column(
        ForeignKey("FINANCIAL_PERIOD_SNAPSHOT.id"), nullable=True, index=True
    )
    financial_period_snapshot: Mapped[Optional["FinancialPeriodSnapshot"]] = relationship(back_populates="transactions")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (Index("ix_normalized_transaction_user_date", "user_id", "date"),)


class BudgetThreshold(Base):
    __tablename__ = "BUDGET_THRESHOLD"

    id: Mapped[int] = mapped_column(BigInteger(), primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(UUID(as_uuid=True), default=uuid4, unique=True, nullable=False)

    # Budget details
    period: Mapped[PeriodEnum] = mapped_column(Enum(PeriodEnum), nullable=False)
    limit_amount: Mapped[Decimal] = mapped_column(Numeric(precision=15, scale=2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    # Source and status
    source: Mapped[BudgedThresholdSourceEnum] = mapped_column(Enum(BudgedThresholdSourceEnum), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Date range
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # User relationship
    user_id: Mapped[int] = mapped_column(ForeignKey("USER.id"), nullable=False, index=True)
    user: Mapped["User"] = relationship(back_populates="budget_thresholds")

    # Category relationship
    category_id: Mapped[int] = mapped_column(ForeignKey("CATEGORY.id"), nullable=False, index=True)
    category: Mapped["Category"] = relationship()

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    __table_args__ = (Index("ix_budget_threshold_user_category_period", "user_id", "category_id", "period"),)


class FinancialPeriodSnapshot(Base):
    __tablename__ = "FINANCIAL_PERIOD_SNAPSHOT"

    id: Mapped[int] = mapped_column(BigInteger(), primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(UUID(as_uuid=True), default=uuid4, unique=True, nullable=False)

    # Period details
    period: Mapped[PeriodEnum] = mapped_column(Enum(PeriodEnum), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Financial metrics
    total_income: Mapped[Decimal] = mapped_column(Numeric(precision=15, scale=2), nullable=False)
    total_outcome: Mapped[Decimal] = mapped_column(Numeric(precision=15, scale=2), nullable=False)
    savings: Mapped[Decimal] = mapped_column(Numeric(precision=15, scale=2), nullable=False)
    savings_rate: Mapped[Decimal] = mapped_column(
        Numeric(precision=5, scale=4), nullable=False
    )  # savings / total_income

    # Aggregated data stored as JSON
    category_spend: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    budget_status: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)

    # User relationship
    user_id: Mapped[int] = mapped_column(ForeignKey("USER.id"), nullable=False, index=True)
    user: Mapped["User"] = relationship(back_populates="financial_period_snapshots")

    # Relationship to transactions
    transactions: Mapped[list["NormalizedTransaction"]] = relationship(back_populates="financial_period_snapshot")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    __table_args__ = (Index("ix_financial_period_snapshot_user_period", "user_id", "period", "start_date"),)
