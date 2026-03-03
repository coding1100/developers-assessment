import uuid
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from pydantic import EmailStr
from sqlalchemy import Column, Numeric
from sqlmodel import Field, Relationship, SQLModel


class RemittanceStatus(str, Enum):
    PENDING = "PENDING"
    REMITTED = "REMITTED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class WorkLogRemittanceStatus(str, Enum):
    REMITTED = "REMITTED"
    UNREMITTED = "UNREMITTED"


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    items: list["Item"] = Relationship(back_populates="owner", cascade_delete=True)
    worklogs: list["WorkLog"] = Relationship(
        back_populates="worker", cascade_delete=True
    )
    remittances: list["Remittance"] = Relationship(
        back_populates="worker", cascade_delete=True
    )


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Shared properties
class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on item creation
class ItemCreate(ItemBase):
    pass


# Properties to receive on item update
class ItemUpdate(ItemBase):
    title: str | None = Field(default=None, min_length=1, max_length=255)  # type: ignore


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="items")


# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


class WorkLogBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)


class WorkLog(WorkLogBase, table=True):
    __tablename__ = "worklog"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE", index=True
    )
    settled_amount: Decimal = Field(
        default=Decimal("0.00"),
        sa_column=Column(Numeric(12, 2), nullable=False, default=Decimal("0.00")),
    )
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    worker: User | None = Relationship(back_populates="worklogs")
    segments: list["WorkSegment"] = Relationship(
        back_populates="worklog", cascade_delete=True
    )
    adjustments: list["WorkAdjustment"] = Relationship(
        back_populates="worklog", cascade_delete=True
    )
    remittance_lines: list["RemittanceLine"] = Relationship(
        back_populates="worklog", cascade_delete=True
    )


class WorkSegment(SQLModel, table=True):
    __tablename__ = "work_segment"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    worklog_id: uuid.UUID = Field(
        foreign_key="worklog.id", nullable=False, ondelete="CASCADE", index=True
    )
    minutes: int = Field(gt=0)
    hourly_rate: Decimal = Field(
        sa_column=Column(Numeric(12, 2), nullable=False),
    )
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    worklog: WorkLog | None = Relationship(back_populates="segments")


class WorkAdjustment(SQLModel, table=True):
    __tablename__ = "work_adjustment"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    worklog_id: uuid.UUID = Field(
        foreign_key="worklog.id", nullable=False, ondelete="CASCADE", index=True
    )
    amount: Decimal = Field(
        sa_column=Column(Numeric(12, 2), nullable=False),
    )
    reason: str | None = Field(default=None, max_length=255)
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    worklog: WorkLog | None = Relationship(back_populates="adjustments")


class Remittance(SQLModel, table=True):
    __tablename__ = "remittance"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE", index=True
    )
    period_start: date = Field(index=True)
    period_end: date = Field(index=True)
    status: str = Field(default=RemittanceStatus.PENDING.value, max_length=20, index=True)
    total_amount: Decimal = Field(
        sa_column=Column(Numeric(12, 2), nullable=False),
    )
    failure_reason: str | None = Field(default=None, max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    processed_at: datetime | None = Field(default=None)
    worker: User | None = Relationship(back_populates="remittances")
    lines: list["RemittanceLine"] = Relationship(
        back_populates="remittance", cascade_delete=True
    )


class RemittanceLine(SQLModel, table=True):
    __tablename__ = "remittance_line"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    remittance_id: uuid.UUID = Field(
        foreign_key="remittance.id", nullable=False, ondelete="CASCADE", index=True
    )
    worklog_id: uuid.UUID = Field(
        foreign_key="worklog.id", nullable=False, ondelete="CASCADE", index=True
    )
    amount: Decimal = Field(
        sa_column=Column(Numeric(12, 2), nullable=False),
    )
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    remittance: Remittance | None = Relationship(back_populates="lines")
    worklog: WorkLog | None = Relationship(back_populates="remittance_lines")


class WorkLogAmountPublic(SQLModel):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    total_amount: Decimal
    settled_amount: Decimal
    unremitted_amount: Decimal
    remittance_status: WorkLogRemittanceStatus


class WorkLogAmountsPublic(SQLModel):
    data: list[WorkLogAmountPublic]
    count: int


class RemittanceLinePublic(SQLModel):
    worklog_id: uuid.UUID
    amount: Decimal


class RemittanceSettlementPublic(SQLModel):
    id: uuid.UUID
    user_id: uuid.UUID
    status: str
    total_amount: Decimal
    period_start: date
    period_end: date
    failure_reason: str | None = None
    line_items: list[RemittanceLinePublic]


class RemittanceSettlementsPublic(SQLModel):
    data: list[RemittanceSettlementPublic]
    count: int


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)
