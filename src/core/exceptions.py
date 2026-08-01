"""Domain-level exceptions.

The service layer raises these instead of `HTTPException`, so business logic
stays free of HTTP concerns. The API layer translates them into responses via
handlers registered in `src.main`.
"""

from uuid import UUID


class ExpenseTrackerError(Exception):
    """Base class for all application errors."""

    message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.message
        super().__init__(self.message)


class ExpenseNotFoundError(ExpenseTrackerError):
    """Raised when an expense ID does not exist in the datastore. -> 404"""

    def __init__(self, expense_id: UUID) -> None:
        self.expense_id = expense_id
        super().__init__(f"Expense with id '{expense_id}' was not found.")


class DuplicateExpenseError(ExpenseTrackerError):
    """Raised when an expense ID is already present in the datastore. -> 409"""

    def __init__(self, expense_id: UUID) -> None:
        self.expense_id = expense_id
        super().__init__(f"Expense with id '{expense_id}' already exists.")


class StorageError(ExpenseTrackerError):
    """Raised when the datastore cannot be read or written. -> 500"""

    message = "The expense datastore is unavailable or corrupted."
