"""Expense HTTP routes.

Thin layer: validate input, delegate to `ExpenseService`, shape the response.
No rules live here. Domain errors raised by the service are converted to
responses by the handlers registered in `src.main`.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Query, status

from src.dependencies import ExpenseServiceDep
from src.schemas.expense import ErrorResponse, ExpenseCreate, ExpenseRead, ExpenseSummary

router = APIRouter(prefix="/expenses", tags=["expenses"])

CategoryQuery = Annotated[
    str | None,
    Query(
        min_length=1,
        max_length=50,
        description="Case-insensitive exact category match.",
        examples=["groceries"],
    ),
]

ExpenseIdPath = Annotated[UUID, Path(description="UUID of the expense.")]

SAMPLE_ID = "3d8f813d-7c78-4c25-af6a-57d98bf174db"


def _error(description: str, detail: str) -> dict:
    """Document an error response with an example matching *that* status code.

    Without an explicit example here, Swagger falls back to the single example
    on `ErrorResponse` and shows the same message for 404, 409 and 422 alike.
    """
    return {
        "model": ErrorResponse,
        "description": description,
        "content": {"application/json": {"example": {"detail": detail}}},
    }


NOT_FOUND_RESPONSE = {
    404: _error("Expense not found", f"Expense with id '{SAMPLE_ID}' was not found.")
}
CONFLICT_RESPONSE = {
    409: _error("Expense ID already exists", f"Expense with id '{SAMPLE_ID}' already exists.")
}
VALIDATION_RESPONSE = {
    422: _error("Validation error", "Invalid request. amount: Input should be greater than 0")
}
INVALID_CATEGORY_RESPONSE = {
    422: _error(
        "Validation error",
        "Invalid request. category: String should have at least 1 character",
    )
}
INVALID_ID_RESPONSE = {
    422: _error("Validation error", "Invalid request. expense_id: Input should be a valid UUID")
}


@router.post(
    "",
    response_model=ExpenseRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add an expense",
    description="Creates an expense and returns it with a server-generated UUID.",
    responses={**VALIDATION_RESPONSE, **CONFLICT_RESPONSE},
)
def create_expense(payload: ExpenseCreate, service: ExpenseServiceDep) -> ExpenseRead:
    expense = service.create(payload)
    return ExpenseRead.model_validate(expense)


@router.get(
    "",
    response_model=list[ExpenseRead],
    summary="List expenses",
    description=(
        "Returns every expense in insertion order. Pass `category` to return "
        "only expenses in that category; matching is case-insensitive. An "
        "unknown category yields an empty list, not a 404."
    ),
    responses=INVALID_CATEGORY_RESPONSE,
)
def list_expenses(service: ExpenseServiceDep, category: CategoryQuery = None) -> list[ExpenseRead]:
    expenses = service.list_expenses(category)
    return [ExpenseRead.model_validate(expense) for expense in expenses]


@router.get(
    "/summary",
    response_model=ExpenseSummary,
    summary="Total expenses overall and by category",
    description=(
        "Returns the overall total and count, plus a per-category breakdown "
        "ordered by total descending. Pass `category` to restrict every figure "
        "to a single category."
    ),
    responses=INVALID_CATEGORY_RESPONSE,
)
def get_summary(service: ExpenseServiceDep, category: CategoryQuery = None) -> ExpenseSummary:
    return service.summarize(category)


@router.get(
    "/{expense_id}",
    response_model=ExpenseRead,
    summary="Get a single expense",
    responses={**NOT_FOUND_RESPONSE, **INVALID_ID_RESPONSE},
)
def get_expense(expense_id: ExpenseIdPath, service: ExpenseServiceDep) -> ExpenseRead:
    return ExpenseRead.model_validate(service.get(expense_id))


@router.delete(
    "/{expense_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an expense",
    description="Deletes the expense and returns an empty 204 response.",
    responses={**NOT_FOUND_RESPONSE, **INVALID_ID_RESPONSE},
)
def delete_expense(expense_id: ExpenseIdPath, service: ExpenseServiceDep) -> None:
    service.delete(expense_id)
