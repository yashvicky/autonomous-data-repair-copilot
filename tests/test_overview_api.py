from uuid import uuid4

from fastapi.testclient import TestClient

from data_repair_copilot.api.app import create_app


def test_overview_screen() -> None:
    response = TestClient(create_app()).get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Select a CSV file" in response.text
    assert "Dataset profile" in response.text
    assert "synthetic data" in response.text


def test_profile() -> None:
    client = TestClient(create_app())
    upload = client.post(
        "/uploads", content=b"id,zip\n001,00501\n002,\n002,\n", headers={"content-type": "text/csv"}
    )
    assert upload.status_code == 201
    key = upload.json()["upload_id"]
    profile = client.get(f"/uploads/{key}/profile")
    assert profile.status_code == 200
    assert (profile.json()["row_count"], profile.json()["column_count"]) == (3, 2)
    columns = profile.json()["columns"]
    assert [
        (column["name"], column["unique_count"], column["null_count"]) for column in columns
    ] == [("id", 2, 0), ("zip", 2, 0)]
    assert all(not column["sample_values"] for column in columns)
    findings = client.post(f"/analyses/{key}").json()["issues"]
    assert {"kind": "missing_value", "column": "zip", "row_indices": [1, 2]} in findings
    assert client.get(f"/uploads/{key}/profile").json() == profile.json()


def test_invalid_profile_requests() -> None:
    client = TestClient(create_app())
    assert client.get(f"/uploads/{uuid4()}/profile").status_code == 404
    assert client.get("/uploads/not-a-uuid/profile").status_code == 422
    assert (
        client.post(
            "/uploads", content=b"id\n\xff", headers={"content-type": "text/csv"}
        ).status_code
        == 400
    )
