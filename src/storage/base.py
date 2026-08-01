"""Storage abstraction.

The service layer depends on this interface, never on a concrete backend.
Swapping the JSON file for SQLite or Postgres means adding one implementation
and changing one line in `src.dependencies` — no service or router changes.

Scope: persistence only. The repository stores and retrieves whole records;
filtering, aggregation and other rules belong to the service layer.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from src.models.expense import Expense


class ExpenseRepository(ABC):
    """Collection-like persistence interface for `Expense` records."""

    @abstractmethod
    def list_all(self) -> list[Expense]:
        """Return every stored expense in insertion order. Empty list if none."""

    @abstractmethod
    def get(self, expense_id: UUID) -> Expense | None:
        """Return one expense, or `None` if no record has that ID."""

    @abstractmethod
    def add(self, expense: Expense) -> Expense:
        """Persist a new expense and return it.

        Raises `DuplicateExpenseError` if the ID is already present.
        """

    @abstractmethod
    def delete(self, expense_id: UUID) -> bool:
        """Remove an expense. Returns `True` if a record was removed."""
