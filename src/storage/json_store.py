"""JSON file implementation of `ExpenseRepository`.

Design notes
------------
File format — a JSON array of expense objects, `Decimal` amounts serialized as
strings so no precision is lost through a float round-trip::

    [
      {
        "id": "0f0c2e1e-...",
        "title": "Weekly shop",
        "amount": "24.50",
        "category": "groceries",
        "date": "2026-08-01"
      }
    ]

Concurrency — FastAPI runs sync endpoints in a thread pool, so two requests can
touch the file at once. One `threading.Lock` per instance guards every
read-modify-write cycle, making `add` and `delete` atomic with respect to each
other. `src.dependencies` caches one instance per data file so the lock is
genuinely shared across requests.

Durability — writes go to a temporary file in the same directory, are flushed
and fsynced, then `os.replace`d over the target. That call is atomic on POSIX
and Windows, so a crash mid-write can never leave a truncated datastore.

Read strategy — the file is re-read on each operation rather than cached. At
take-home data volumes this costs nothing and removes a whole class of
cache-invalidation bugs.

Failure handling — a missing or empty file is treated as an empty store and
created on first write. A file that exists but cannot be parsed raises
`StorageError`; silently discarding a user's data would be far worse than
failing loudly.
"""

import json
import os
import tempfile
import threading
from pathlib import Path
from uuid import UUID

from pydantic import ValidationError

from src.core.exceptions import DuplicateExpenseError, StorageError
from src.models.expense import Expense
from src.storage.base import ExpenseRepository


class JSONExpenseRepository(ExpenseRepository):
    """Stores expenses as a JSON array on the local filesystem."""

    def __init__(self, data_file: Path) -> None:
        self._data_file = data_file
        self._lock = threading.Lock()

    # --- ExpenseRepository -------------------------------------------------

    def list_all(self) -> list[Expense]:
        with self._lock:
            return self._read()

    def get(self, expense_id: UUID) -> Expense | None:
        with self._lock:
            return next((e for e in self._read() if e.id == expense_id), None)

    def add(self, expense: Expense) -> Expense:
        with self._lock:
            expenses = self._read()
            if any(e.id == expense.id for e in expenses):
                raise DuplicateExpenseError(expense.id)
            expenses.append(expense)
            self._write(expenses)
            return expense

    def delete(self, expense_id: UUID) -> bool:
        with self._lock:
            expenses = self._read()
            remaining = [e for e in expenses if e.id != expense_id]
            if len(remaining) == len(expenses):
                return False
            self._write(remaining)
            return True

    # --- Internal file I/O -------------------------------------------------
    # Both helpers assume `self._lock` is already held by the caller.

    def _read(self) -> list[Expense]:
        """Load and validate the datastore. Missing or empty file -> []."""
        try:
            raw = self._data_file.read_text(encoding="utf-8")
        except FileNotFoundError:
            return []
        except OSError as exc:
            raise StorageError(f"Could not read datastore '{self._data_file}'.") from exc

        if not raw.strip():
            return []

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise StorageError(
                f"Datastore '{self._data_file}' contains malformed JSON."
            ) from exc

        if not isinstance(payload, list):
            raise StorageError(
                f"Datastore '{self._data_file}' must contain a JSON array of expenses."
            )

        try:
            return [Expense.model_validate(item) for item in payload]
        except ValidationError as exc:
            raise StorageError(
                f"Datastore '{self._data_file}' contains records that are not valid expenses."
            ) from exc

    def _write(self, expenses: list[Expense]) -> None:
        """Atomically replace the datastore with `expenses`."""
        payload = [expense.model_dump(mode="json") for expense in expenses]
        directory = self._data_file.parent
        temp_path: Path | None = None

        try:
            directory.mkdir(parents=True, exist_ok=True)
            # Same directory as the target, so os.replace stays on one filesystem.
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=directory,
                prefix=f".{self._data_file.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temp_path = Path(handle.name)
                json.dump(payload, handle, indent=2)
                handle.flush()
                os.fsync(handle.fileno())

            os.replace(temp_path, self._data_file)
            temp_path = None
        except OSError as exc:
            raise StorageError(f"Could not write datastore '{self._data_file}'.") from exc
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)
