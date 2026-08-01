"""API schemas (request / response contracts).

These are the only shapes the outside world sees. Keeping them apart from
`src.models.Expense` means the server-generated `id` can never be set by a
client.

Money crosses the wire as a JSON number but is validated and totalled as
`Decimal`, so no arithmetic ever happens in binary floating point.
"""

import datetime as dt
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.models.expense import normalize_category

Amount = Annotated[
    Decimal,
    Field(
        gt=0,
        max_digits=12,
        decimal_places=2,
        description="Positive amount, at most 2 decimal places.",
    ),
]


class ExpenseCreate(BaseModel):
    """Request body for creating an expense."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "title": "Weekly shop",
                "amount": 24.50,
                "category": "Groceries",
                "date": "2026-08-01",
            }
        },
    )

    title: str = Field(min_length=1, max_length=120, description="Short human-readable label.")
    amount: Amount
    category: str = Field(
        min_length=1,
        max_length=50,
        description="Stored lowercase and whitespace-normalized.",
    )
    date: dt.date = Field(description="Calendar date the money was spent (YYYY-MM-DD).")

    @field_validator("title")
    @classmethod
    def _clean_title(cls, value: str) -> str:
        title = " ".join(value.split())
        if not title:
            raise ValueError("title must not be blank")
        return title

    @field_validator("category")
    @classmethod
    def _normalize_category(cls, value: str) -> str:
        category = normalize_category(value)
        if not category:
            raise ValueError("category must not be blank")
        return category


class ExpenseRead(BaseModel):
    """Response body for a single expense."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "8cde533c-7fcb-49a7-97cb-8a8143c45429",
                "title": "Weekly shop",
                "amount": 24.5,
                "category": "groceries",
                "date": "2026-08-01",
            }
        },
    )

    id: UUID
    title: str
    amount: float
    category: str
    date: dt.date


class CategoryTotal(BaseModel):
    """Aggregated spend for one category."""

    category: str
    total: float = Field(description="Sum of amounts in this category.")
    count: int = Field(description="Number of expenses in this category.")


class ExpenseSummary(BaseModel):
    """Overall totals plus a per-category breakdown."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total": 74.5,
                "count": 3,
                "by_category": [
                    {"category": "groceries", "total": 50.0, "count": 2},
                    {"category": "transport", "total": 24.5, "count": 1},
                ],
            }
        }
    )

    total: float = Field(description="Sum of every expense in scope.")
    count: int = Field(description="Number of expenses in scope.")
    by_category: list[CategoryTotal] = Field(
        description="Per-category breakdown, highest total first."
    )


class ErrorResponse(BaseModel):
    """Uniform error envelope for every non-2xx response."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"detail": "Expense with id '8cde533c-...' was not found."}}
    )

    detail: str
