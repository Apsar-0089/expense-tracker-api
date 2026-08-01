"""Business logic for expenses.

Knows the rules; knows nothing about HTTP or about how records are persisted.
Receives an `ExpenseRepository` by constructor injection and raises domain
exceptions from `src.core.exceptions`.

All money arithmetic happens in `Decimal`. Conversion to a JSON number occurs
once, at the response-schema boundary.
"""

from collections import defaultdict
from decimal import Decimal
from uuid import UUID, uuid4

from src.core.exceptions import ExpenseNotFoundError
from src.models.expense import Expense, normalize_category
from src.schemas.expense import CategoryTotal, ExpenseCreate, ExpenseSummary
from src.storage.base import ExpenseRepository

ZERO = Decimal("0.00")


class ExpenseService:
    def __init__(self, repository: ExpenseRepository) -> None:
        self._repository = repository

    def create(self, payload: ExpenseCreate) -> Expense:
        """Build an `Expense` from a validated payload and persist it.

        The ID is generated here, never accepted from the client. The
        repository rejects a collision, so a duplicate can never be written
        even though `uuid4` makes one vanishingly unlikely.
        """
        expense = Expense(id=uuid4(), **payload.model_dump())
        return self._repository.add(expense)

    def list_expenses(self, category: str | None = None) -> list[Expense]:
        """All expenses, optionally narrowed to one category.

        The filter is normalized the same way stored categories are, so
        `?category=Groceries` matches a record saved as `groceries`.
        """
        expenses = self._repository.list_all()
        if category is None:
            return expenses
        wanted = normalize_category(category)
        return [expense for expense in expenses if expense.category == wanted]

    def summarize(self, category: str | None = None) -> ExpenseSummary:
        """Overall total plus a per-category breakdown.

        When `category` is given, every figure covers only that category.
        Categories are ordered by total descending, then name, so the response
        is stable across calls.
        """
        expenses = self.list_expenses(category)

        totals: defaultdict[str, Decimal] = defaultdict(lambda: ZERO)
        counts: defaultdict[str, int] = defaultdict(int)
        for expense in expenses:
            totals[expense.category] += expense.amount
            counts[expense.category] += 1

        by_category = [
            CategoryTotal(category=name, total=total, count=counts[name])
            for name, total in sorted(totals.items(), key=lambda item: (-item[1], item[0]))
        ]

        return ExpenseSummary(
            total=sum((expense.amount for expense in expenses), ZERO),
            count=len(expenses),
            by_category=by_category,
        )

    def get(self, expense_id: UUID) -> Expense:
        """Fetch one expense. Raises `ExpenseNotFoundError` if absent."""
        expense = self._repository.get(expense_id)
        if expense is None:
            raise ExpenseNotFoundError(expense_id)
        return expense

    def delete(self, expense_id: UUID) -> None:
        """Delete one expense. Raises `ExpenseNotFoundError` if absent."""
        if not self._repository.delete(expense_id):
            raise ExpenseNotFoundError(expense_id)
