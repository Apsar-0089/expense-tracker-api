"""Composition root.

The only module that knows which concrete storage backend is in use. Routers
depend on `ExpenseServiceDep`, so tests can override `get_repository` with one
pointed at a temp directory and never touch the real datastore.
"""

from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends

from src.core.config import Settings, get_settings
from src.services.expense_service import ExpenseService
from src.storage.base import ExpenseRepository
from src.storage.json_store import JSONExpenseRepository

SettingsDep = Annotated[Settings, Depends(get_settings)]


@lru_cache
def _build_repository(data_file: str) -> ExpenseRepository:
    """One repository instance per data file — its write lock must be shared."""
    return JSONExpenseRepository(data_file=Path(data_file))


def get_repository(settings: SettingsDep) -> ExpenseRepository:
    return _build_repository(str(settings.data_file))


RepositoryDep = Annotated[ExpenseRepository, Depends(get_repository)]


def get_expense_service(repository: RepositoryDep) -> ExpenseService:
    return ExpenseService(repository=repository)


ExpenseServiceDep = Annotated[ExpenseService, Depends(get_expense_service)]
