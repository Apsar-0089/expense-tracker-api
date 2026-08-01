"""API layer: status codes, contracts and error envelopes."""

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

UNKNOWN_ID = "11111111-1111-4111-8111-111111111111"


def create(client: TestClient, **overrides) -> dict:
    payload = {
        "title": "Weekly shop",
        "amount": 24.50,
        "category": "Groceries",
        "date": "2026-08-01",
        **overrides,
    }
    response = client.post("/expenses", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


# --- POST /expenses --------------------------------------------------------


def test_create_returns_201_and_the_created_expense(client: TestClient, sample_payload: dict):
    response = client.post("/expenses", json=sample_payload)

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Weekly shop"
    assert body["amount"] == 24.5
    assert body["category"] == "groceries"  # normalized
    assert body["date"] == "2026-08-01"


def test_create_generates_a_unique_uuid(client: TestClient):
    ids = {create(client)["id"] for _ in range(5)}

    assert len(ids) == 5
    for value in ids:
        assert UUID(value).version == 4


def test_client_cannot_set_the_id(client: TestClient, sample_payload: dict):
    response = client.post("/expenses", json={**sample_payload, "id": UNKNOWN_ID})

    assert response.status_code == 422
    assert "detail" in response.json()


@pytest.mark.parametrize(
    "override, reason",
    [
        ({"amount": 0}, "amount must be positive"),
        ({"amount": -5}, "negative amount"),
        ({"amount": 10.999}, "more than 2 decimal places"),
        ({"amount": "abc"}, "amount is not a number"),
        ({"title": "   "}, "blank title"),
        ({"category": "   "}, "blank category"),
        ({"date": "not-a-date"}, "unparseable date"),
        ({"date": "2026-13-45"}, "impossible date"),
    ],
)
def test_create_rejects_invalid_payloads(client: TestClient, sample_payload, override, reason):
    response = client.post("/expenses", json={**sample_payload, **override})

    assert response.status_code == 422, reason
    assert isinstance(response.json()["detail"], str)


def test_create_rejects_missing_fields(client: TestClient):
    response = client.post("/expenses", json={"title": "Lonely"})

    assert response.status_code == 422
    assert "detail" in response.json()


# --- GET /expenses ---------------------------------------------------------


def test_list_is_empty_initially(client: TestClient):
    response = client.get("/expenses")

    assert response.status_code == 200
    assert response.json() == []


def test_list_returns_all_expenses_in_insertion_order(client: TestClient):
    titles = ["First", "Second", "Third"]
    for title in titles:
        create(client, title=title)

    response = client.get("/expenses")

    assert response.status_code == 200
    assert [item["title"] for item in response.json()] == titles


def test_filter_by_category(client: TestClient):
    create(client, category="groceries")
    create(client, category="transport")
    create(client, category="groceries")

    response = client.get("/expenses", params={"category": "groceries"})

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_filter_by_category_is_case_insensitive(client: TestClient):
    create(client, category="Groceries")

    for query in ("groceries", "GROCERIES", "  Groceries  "):
        response = client.get("/expenses", params={"category": query})
        assert len(response.json()) == 1, query


def test_filter_by_unknown_category_returns_empty_list(client: TestClient):
    create(client, category="groceries")

    response = client.get("/expenses", params={"category": "yachts"})

    assert response.status_code == 200
    assert response.json() == []


# --- GET /expenses/summary -------------------------------------------------


def test_summary_of_empty_store(client: TestClient):
    response = client.get("/expenses/summary")

    assert response.status_code == 200
    assert response.json() == {"total": 0.0, "count": 0, "by_category": []}


def test_summary_totals_overall_and_by_category(client: TestClient):
    create(client, category="groceries", amount=10.00)
    create(client, category="groceries", amount=15.50)
    create(client, category="transport", amount=4.25)

    body = client.get("/expenses/summary").json()

    assert body["total"] == 29.75
    assert body["count"] == 3
    assert body["by_category"] == [
        {"category": "groceries", "total": 25.5, "count": 2},
        {"category": "transport", "total": 4.25, "count": 1},
    ]


def test_summary_groups_categories_case_insensitively(client: TestClient):
    create(client, category="Food", amount=10.00)
    create(client, category="food", amount=5.00)
    create(client, category="  FOOD ", amount=5.00)

    body = client.get("/expenses/summary").json()

    assert len(body["by_category"]) == 1
    assert body["by_category"][0] == {"category": "food", "total": 20.0, "count": 3}


def test_summary_can_be_scoped_to_one_category(client: TestClient):
    create(client, category="groceries", amount=10.00)
    create(client, category="transport", amount=4.25)

    body = client.get("/expenses/summary", params={"category": "transport"}).json()

    assert body["total"] == 4.25
    assert body["count"] == 1
    assert body["by_category"] == [{"category": "transport", "total": 4.25, "count": 1}]


def test_summary_avoids_floating_point_drift(client: TestClient):
    for _ in range(3):
        create(client, category="coffee", amount=0.10)

    # 0.1 * 3 in binary floats is 0.30000000000000004; Decimal maths avoids it.
    assert client.get("/expenses/summary").json()["total"] == 0.30


def test_summary_route_is_not_shadowed_by_the_id_route(client: TestClient):
    """`/expenses/summary` must not be parsed as `/expenses/{expense_id}`."""
    response = client.get("/expenses/summary")

    assert response.status_code == 200
    assert "by_category" in response.json()


# --- GET /expenses/{id} ----------------------------------------------------


def test_get_single_expense(client: TestClient):
    created = create(client)

    response = client.get(f"/expenses/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_unknown_expense_returns_404(client: TestClient):
    response = client.get(f"/expenses/{UNKNOWN_ID}")

    assert response.status_code == 404
    assert UNKNOWN_ID in response.json()["detail"]


def test_malformed_uuid_returns_422(client: TestClient):
    response = client.get("/expenses/not-a-uuid")

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)


# --- DELETE /expenses/{id} -------------------------------------------------


def test_delete_returns_204_and_removes_the_expense(client: TestClient):
    created = create(client)

    response = client.delete(f"/expenses/{created['id']}")

    assert response.status_code == 204
    assert response.content == b""
    assert client.get("/expenses").json() == []


def test_delete_is_not_idempotent_and_404s_the_second_time(client: TestClient):
    created = create(client)

    assert client.delete(f"/expenses/{created['id']}").status_code == 204
    assert client.delete(f"/expenses/{created['id']}").status_code == 404


def test_delete_unknown_expense_returns_404(client: TestClient):
    response = client.delete(f"/expenses/{UNKNOWN_ID}")

    assert response.status_code == 404
    assert "detail" in response.json()


# --- Cross-cutting ---------------------------------------------------------


def test_data_survives_a_new_app_instance(client: TestClient, repository):
    """Persistence is on disk, not in process memory."""
    created = create(client)

    from src.dependencies import get_repository
    from src.main import create_app

    fresh_app = create_app()
    fresh_app.dependency_overrides[get_repository] = lambda: repository
    with TestClient(fresh_app) as fresh_client:
        assert fresh_client.get("/expenses").json()[0]["id"] == created["id"]


def test_corrupted_datastore_returns_500_with_detail(client: TestClient, data_file):
    data_file.write_text("{not json", encoding="utf-8")

    response = client.get("/expenses")

    assert response.status_code == 500
    assert "detail" in response.json()


def test_unknown_route_uses_the_same_error_envelope(client: TestClient):
    response = client.get("/nope")

    assert response.status_code == 404
    assert "detail" in response.json()


def test_health_check(client: TestClient):
    assert client.get("/health").json() == {"status": "ok"}
