"""The generated OpenAPI schema is part of the deliverable, so it is tested."""

from fastapi.testclient import TestClient


def test_openapi_schema_is_served(client: TestClient):
    assert client.get("/openapi.json").status_code == 200


def test_swagger_and_redoc_are_reachable(client: TestClient):
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200


def test_every_documented_route_is_present(client: TestClient):
    paths = client.get("/openapi.json").json()["paths"]

    assert set(paths["/expenses"]) == {"get", "post"}
    assert set(paths["/expenses/{expense_id}"]) == {"get", "delete"}
    assert set(paths["/expenses/summary"]) == {"get"}


def test_documented_status_codes_match_the_implementation(client: TestClient):
    paths = client.get("/openapi.json").json()["paths"]

    assert "201" in paths["/expenses"]["post"]["responses"]
    assert "409" in paths["/expenses"]["post"]["responses"]
    assert "204" in paths["/expenses/{expense_id}"]["delete"]["responses"]
    assert "404" in paths["/expenses/{expense_id}"]["delete"]["responses"]


def test_error_responses_document_the_detail_envelope(client: TestClient):
    schema = client.get("/openapi.json").json()
    error_ref = schema["paths"]["/expenses/{expense_id}"]["get"]["responses"]["404"]
    assert error_ref["content"]["application/json"]["schema"]["$ref"].endswith("ErrorResponse")
    assert schema["components"]["schemas"]["ErrorResponse"]["required"] == ["detail"]


def test_each_error_code_documents_an_example_matching_that_code(client: TestClient):
    """A 409 must not be illustrated with a 'was not found' message."""
    paths = client.get("/openapi.json").json()["paths"]

    def example(path: str, method: str, code: str) -> str:
        content = paths[path][method]["responses"][code]["content"]["application/json"]
        return content["example"]["detail"]

    assert "already exists" in example("/expenses", "post", "409")
    assert "was not found" in example("/expenses/{expense_id}", "get", "404")
    assert "was not found" in example("/expenses/{expense_id}", "delete", "404")
    assert "valid UUID" in example("/expenses/{expense_id}", "delete", "422")
    assert "amount" in example("/expenses", "post", "422")
    assert "category" in example("/expenses", "get", "422")


def test_no_error_response_is_missing_its_example(client: TestClient):
    paths = client.get("/openapi.json").json()["paths"]

    for path, operations in paths.items():
        for method, operation in operations.items():
            for code, response in operation["responses"].items():
                if code.startswith(("4", "5")):
                    content = response.get("content", {}).get("application/json", {})
                    assert content.get("example"), f"{method.upper()} {path} {code}"


def test_every_operation_has_a_summary(client: TestClient):
    paths = client.get("/openapi.json").json()["paths"]

    for path, operations in paths.items():
        for method, operation in operations.items():
            assert operation.get("summary"), f"{method.upper()} {path} has no summary"


def test_amounts_are_documented_as_numbers(client: TestClient):
    schemas = client.get("/openapi.json").json()["components"]["schemas"]

    assert schemas["ExpenseRead"]["properties"]["amount"]["type"] == "number"
    assert schemas["ExpenseSummary"]["properties"]["total"]["type"] == "number"
