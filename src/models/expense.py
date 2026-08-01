"""Domain model.

`Expense` is the internal representation of a record and the single source of
truth for its shape on disk. It is deliberately separate from the API schemas
in `src.schemas` so the wire contract and the stored contract can evolve
independently.
"""

import datetime as dt
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

CENTS = Decimal("0.01")


def normalize_category(value: str) -> str:
    """Canonical category form: trimmed, collapsed whitespace, lowercased.

    Normalizing on write means filtering and grouping become exact-match
    operations later — "Food", "food " and "FOOD" are one category.
    """
    return " ".join(value.split()).lower()


class Expense(BaseModel):
    """A single recorded expense."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    title: str = Field(min_length=1, max_length=120)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    category: str = Field(min_length=1, max_length=50)
    date: dt.date

    @field_validator("amount")
    @classmethod
    def _to_cents(cls, value: Decimal) -> Decimal:
        """Store money at a fixed scale so `24.5` and `24.50` are one value.

        Lossless: the field constraints already reject more than 2 decimals.
        """
        return value.quantize(CENTS)

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
