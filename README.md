# Smart Expense Tracker API

A small REST API for tracking personal expenses, built with **FastAPI**. Data is
persisted to a local JSON file — no database required.

---

## What I built

A CRUD-style expense API with a clean three-layer separation:

```
HTTP  →  routers/    thin: parse, delegate, shape the response
         services/   business rules: filtering, totals, ID generation
         storage/    persistence only: read/write the JSON file
```

Each layer depends only on the one below it, and the storage layer sits behind
an abstract interface (`ExpenseRepository`). Swapping the JSON file for a real
database means writing one new class and changing one line in
`src/dependencies.py` — no router or service code would change.

**Features**

- Add, list, fetch and delete expenses
- Filter by category (case-insensitive)
- Totals overall and grouped by category
- UUID identifiers, generated server-side
- Pydantic validation on every request
- Consistent `{"detail": "..."}` error envelope on every non-2xx response
- Thread-safe, crash-safe JSON persistence (atomic writes)
- 57 tests
- **Bonus chosen: complete OpenAPI / Swagger documentation** (see below)

---

## Requirements

Python 3.11 or newer.

## Install

```bash
git clone <repo-url>
cd expense-tracker-api

python -m venv .venv

# macOS / Linux
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

## Run the server

```bash
uvicorn src.main:app --reload
```

The API is then available at <http://127.0.0.1:8000>.

| Documentation | URL |
| --- | --- |
| Swagger UI | <http://127.0.0.1:8000/docs> |
| ReDoc | <http://127.0.0.1:8000/redoc> |
| OpenAPI schema | <http://127.0.0.1:8000/openapi.json> |

Expenses are written to `data/expenses.json`, created automatically on the
first write. Set `EXPENSE_DATA_FILE` to store them elsewhere.

## Run the tests

```bash
pytest
```

Expected output: `57 passed`.

---

## API reference

| Method | Path | Description | Success |
| --- | --- | --- | --- |
| `POST` | `/expenses` | Add an expense | `201` |
| `GET` | `/expenses` | List all expenses | `200` |
| `GET` | `/expenses?category=food` | Filter by category | `200` |
| `GET` | `/expenses/summary` | Totals overall and by category | `200` |
| `GET` | `/expenses/{expense_id}` | Fetch one expense | `200` |
| `DELETE` | `/expenses/{expense_id}` | Delete an expense | `204` |
| `GET` | `/health` | Liveness check | `200` |

### Add an expense

```bash
curl -X POST http://127.0.0.1:8000/expenses \
  -H "Content-Type: application/json" \
  -d '{"title":"Weekly shop","amount":24.50,"category":"Groceries","date":"2026-08-01"}'
```

```json
{
  "id": "3d8f813d-7c78-4c25-af6a-57d98bf174db",
  "title": "Weekly shop",
  "amount": 24.5,
  "category": "groceries",
  "date": "2026-08-01"
}
```

### Filter by category

```bash
curl "http://127.0.0.1:8000/expenses?category=GROCERIES"
```

Matching is case- and whitespace-insensitive: `Groceries`, `groceries` and
`  GROCERIES  ` all find the same records. An unknown category returns `[]`
with `200`, not a `404` — an empty result set is not an error.

### Summary

```bash
curl http://127.0.0.1:8000/expenses/summary
```

```json
{
  "total": 26.75,
  "count": 2,
  "by_category": [
    { "category": "groceries", "total": 24.5, "count": 1 },
    { "category": "transport", "total": 2.25, "count": 1 }
  ]
}
```

Categories are ordered by total, highest first. Adding `?category=transport`
restricts every figure in the response to that one category.

### Delete an expense

```bash
curl -X DELETE http://127.0.0.1:8000/expenses/3d8f813d-7c78-4c25-af6a-57d98bf174db
```

Returns `204 No Content`. Deleting the same ID again returns `404`.

---

## Validation and errors

Every error — validation, not-found, conflict or server-side — returns the same
shape:

```json
{ "detail": "Expense with id '1111...' was not found." }
```

| Status | When |
| --- | --- |
| `201` | Expense created |
| `204` | Expense deleted |
| `404` | No expense with that ID, or unknown route |
| `409` | Expense ID already exists |
| `422` | Request failed validation (bad amount, malformed UUID, unknown field) |
| `500` | The datastore is unreadable or corrupted |

Field rules:

| Field | Rule |
| --- | --- |
| `title` | Required, 1–120 chars, whitespace-trimmed, may not be blank |
| `amount` | Required, **greater than zero**, at most 2 decimal places |
| `category` | Required, 1–50 chars, normalized to lowercase |
| `date` | Required, ISO `YYYY-MM-DD` |
| `id` | Server-generated; sending one is rejected with `422` |

FastAPI's default validation errors are a nested array, which would break the
uniform envelope, so a handler in `src/main.py` flattens them into a single
readable `detail` string.

---

## Design decisions

**Money is `Decimal`, never `float`.** Amounts are validated, stored and summed
as `Decimal`, and written to JSON as strings (`"24.50"`) so no precision is lost
in a float round-trip. Conversion to a JSON number happens once, at the response
boundary. Summing `0.10` three times returns exactly `0.30`, not
`0.30000000000000004` — there is a test for this.

**Categories are normalized on write.** Trimmed, whitespace-collapsed and
lowercased, so filtering and grouping are exact matches rather than fuzzy
comparisons. `"Food"` and `"food "` are one category, not three. The trade-off
is that stored categories are lowercase; I preferred that over a fixed `Enum`,
which would have forced a code change to add a category.

**Writes are atomic.** Data is written to a temporary file in the same
directory, flushed, `fsync`ed, then `os.replace`d over the target — an atomic
operation on both POSIX and Windows. A crash mid-write cannot leave a truncated
datastore.

**Writes are thread-safe.** FastAPI runs synchronous endpoints in a thread pool,
so concurrent requests really can hit the file at once. A `threading.Lock` makes
each read-modify-write cycle atomic, and `src/dependencies.py` caches one
repository per data file so the lock is genuinely shared. A test fires 40
concurrent inserts and asserts none are lost.

**A corrupt datastore fails loudly.** A missing or empty file is treated as an
empty store, but a file containing malformed JSON raises `StorageError` → `500`
rather than being silently discarded. Losing a user's data quietly would be the
worse failure.

**Route ordering matters.** `/expenses/summary` is declared *before*
`/expenses/{expense_id}`; reversed, FastAPI would try to parse `"summary"` as a
UUID and return `422`. A test pins this so it cannot regress.

---

## Project structure

```
expense-tracker-api/
├── README.md
├── AI_NOTES.md
├── requirements.txt
├── pytest.ini
├── data/                        # JSON datastore (created on first write)
├── src/
│   ├── main.py                  # app factory, routers, error handlers
│   ├── dependencies.py          # composition root / dependency injection
│   ├── core/
│   │   ├── config.py            # environment-driven settings
│   │   └── exceptions.py        # domain errors, no HTTP concerns
│   ├── models/expense.py        # domain entity — the shape on disk
│   ├── schemas/expense.py       # request/response contracts — shape on the wire
│   ├── storage/
│   │   ├── base.py              # ExpenseRepository interface
│   │   └── json_store.py        # JSON file implementation
│   ├── services/
│   │   └── expense_service.py   # business rules
│   └── routers/
│       ├── expenses.py
│       └── health.py
└── tests/
    ├── conftest.py              # fixtures — each test gets an isolated tmp datastore
    ├── test_storage.py          # persistence, concurrency, corruption
    ├── test_expenses_api.py     # endpoints, status codes, error envelope
    └── test_openapi.py          # the generated schema is part of the deliverable
```

`models` and `schemas` are separate on purpose. They look similar today, but
keeping them apart is what makes it structurally impossible for a client to set
its own `id`, and it lets the stored format evolve without breaking the API.

---

## Testing notes

57 tests across three files, covering:

- All endpoints, success and failure paths
- Every validation rule (parameterized: zero, negative, too many decimals,
  non-numeric, blank strings, malformed dates)
- Case-insensitive filtering and grouping
- Decimal precision — no floating-point drift in totals
- Missing file, empty file, malformed JSON, non-array JSON, invalid records
- A failed write leaving the original data intact and no temp files behind
- 40 concurrent writes with no lost records
- Persistence across a new app instance
- The generated OpenAPI schema matching the implementation, including that each
  documented error example matches the status code it illustrates

Every test runs against a fresh `tmp_path` datastore via a dependency override,
so tests never touch real data and cannot interfere with each other.
