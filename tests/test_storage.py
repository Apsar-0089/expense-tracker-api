"""Storage layer: persistence, durability and failure handling."""

import json
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from src.core.exceptions import DuplicateExpenseError, StorageError
from src.models.expense import Expense
from src.storage.json_store import JSONExpenseRepository


def make_expense(**overrides) -> Expense:
    defaults = {
        "id": uuid4(),
        "title": "Weekly shop",
        "amount": Decimal("24.50"),
        "category": "groceries",
        "date": "2026-08-01",
    }
    return Expense(**{**defaults, **overrides})


def test_missing_file_reads_as_empty(repository: JSONExpenseRepository, data_file: Path):
    assert not data_file.exists()
    assert repository.list_all() == []


def test_empty_file_reads_as_empty(repository: JSONExpenseRepository, data_file: Path):
    data_file.write_text("   ", encoding="utf-8")
    assert repository.list_all() == []


def test_add_creates_file_and_persists(repository: JSONExpenseRepository, data_file: Path):
    expense = make_expense()
    repository.add(expense)

    assert data_file.exists()
    assert repository.list_all() == [expense]


def test_amount_survives_round_trip_as_decimal(
    repository: JSONExpenseRepository, data_file: Path
):
    repository.add(make_expense(amount=Decimal("0.10")))
    repository.add(make_expense(amount=Decimal("0.20")))

    # Stored as strings, so no float rounding creeps in.
    stored = json.loads(data_file.read_text(encoding="utf-8"))
    assert [record["amount"] for record in stored] == ["0.10", "0.20"]
    assert all(isinstance(record["amount"], str) for record in stored)

    total = sum(expense.amount for expense in repository.list_all())
    assert total == Decimal("0.30")


def test_amount_is_stored_at_a_fixed_scale(repository: JSONExpenseRepository, data_file: Path):
    """`24.5` and `24.50` must not round-trip as two different strings."""
    repository.add(make_expense(amount=Decimal("24.5")))

    stored = json.loads(data_file.read_text(encoding="utf-8"))
    assert stored[0]["amount"] == "24.50"


def test_add_rejects_duplicate_id(repository: JSONExpenseRepository):
    expense = make_expense()
    repository.add(expense)

    with pytest.raises(DuplicateExpenseError):
        repository.add(expense)


def test_get_returns_none_for_unknown_id(repository: JSONExpenseRepository):
    assert repository.get(uuid4()) is None


def test_delete_returns_false_for_unknown_id(repository: JSONExpenseRepository):
    assert repository.delete(uuid4()) is False


def test_delete_removes_only_the_target(repository: JSONExpenseRepository):
    kept, removed = make_expense(), make_expense()
    repository.add(kept)
    repository.add(removed)

    assert repository.delete(removed.id) is True
    assert repository.list_all() == [kept]


def test_insertion_order_is_preserved(repository: JSONExpenseRepository):
    expenses = [make_expense(title=f"Item {index}") for index in range(5)]
    for expense in expenses:
        repository.add(expense)

    assert [e.title for e in repository.list_all()] == [e.title for e in expenses]


def test_malformed_json_raises_storage_error(
    repository: JSONExpenseRepository, data_file: Path
):
    data_file.write_text("{not json", encoding="utf-8")

    with pytest.raises(StorageError):
        repository.list_all()


def test_non_array_json_raises_storage_error(
    repository: JSONExpenseRepository, data_file: Path
):
    data_file.write_text('{"expenses": []}', encoding="utf-8")

    with pytest.raises(StorageError):
        repository.list_all()


def test_invalid_record_raises_storage_error(
    repository: JSONExpenseRepository, data_file: Path
):
    data_file.write_text('[{"id": "not-a-uuid"}]', encoding="utf-8")

    with pytest.raises(StorageError):
        repository.list_all()


def test_failed_write_leaves_no_temp_files(
    repository: JSONExpenseRepository, data_file: Path, monkeypatch
):
    repository.add(make_expense())

    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("src.storage.json_store.os.replace", boom)

    with pytest.raises(StorageError):
        repository.add(make_expense())

    # Original data intact, no .tmp litter left behind.
    assert len(repository.list_all()) == 1
    assert list(data_file.parent.glob("*.tmp")) == []


def test_concurrent_adds_do_not_lose_records(repository: JSONExpenseRepository):
    """The lock must make read-modify-write atomic across threads."""
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda _: repository.add(make_expense()), range(40)))

    assert len(repository.list_all()) == 40
