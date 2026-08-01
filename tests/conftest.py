"""Shared test fixtures.

Every test gets a fresh app whose repository points at a pytest `tmp_path`, so
tests never touch the real datastore and never interfere with each other.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.dependencies import get_repository
from src.main import create_app
from src.storage.json_store import JSONExpenseRepository


@pytest.fixture
def data_file(tmp_path: Path) -> Path:
    return tmp_path / "expenses.json"


@pytest.fixture
def repository(data_file: Path) -> JSONExpenseRepository:
    return JSONExpenseRepository(data_file=data_file)


@pytest.fixture
def client(repository: JSONExpenseRepository) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_repository] = lambda: repository
    return TestClient(app)


@pytest.fixture
def sample_payload() -> dict:
    return {
        "title": "Weekly shop",
        "amount": 24.50,
        "category": "Groceries",
        "date": "2026-08-01",
    }
