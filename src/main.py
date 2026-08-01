"""Application entry point.

Builds the FastAPI app, mounts routers, and translates domain exceptions into
HTTP responses so that every error the API emits uses the same envelope:
`{"detail": "..."}`.

Run with: `uvicorn src.main:app --reload`
"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.core.config import get_settings
from src.core.exceptions import DuplicateExpenseError, ExpenseNotFoundError, StorageError
from src.routers import expenses, health

DESCRIPTION = """
* **POST /expenses** — add an expense
* **GET /expenses** — list all expenses, or filter with `?category=`
* **GET /expenses/summary** — totals overall and grouped by category
* **GET /expenses/{expense_id}** — fetch one expense
* **DELETE /expenses/{expense_id}** — delete an expense

Every error response uses the same shape: `{"detail": "..."}`.
"""


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        summary="Track personal expenses, backed by a local JSON file.",
        description=DESCRIPTION,
    )

    app.include_router(health.router)
    app.include_router(expenses.router)

    _register_exception_handlers(app)
    return app


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ExpenseNotFoundError)
    async def _not_found(_: Request, exc: ExpenseNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": exc.message})

    @app.exception_handler(DuplicateExpenseError)
    async def _duplicate(_: Request, exc: DuplicateExpenseError) -> JSONResponse:
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content={"detail": exc.message})

    @app.exception_handler(StorageError)
    async def _storage_error(_: Request, exc: StorageError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": exc.message}
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        """Flatten Pydantic's error list into the standard error envelope."""
        problems = "; ".join(
            f"{'.'.join(str(part) for part in error['loc'][1:]) or 'body'}: {error['msg']}"
            for error in exc.errors()
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": f"Invalid request. {problems}"},
        )


app = create_app()
