from uuid import uuid4

from fastapi.testclient import TestClient

from data_repair_copilot.api.app import create_app


def test_upload_and_analysis() -> None:
    client = TestClient(create_app(), base_url="http://localhost", client=("127.0.0.1", 50000))
    content = b'id,zip,note\r\n001,00501,"hello\r\nworld"\r\n002,,x\r\n002,,x\r\n'
    upload = client.post("/uploads", content=content, headers={"content-type": "text/csv"})
    assert upload.status_code == 201
    data = upload.json()
    assert (data["row_count"], data["column_count"]) == (3, 3)
    result = client.post("/analyses/" + data["upload_id"])
    assert result.status_code == 200
    issues = result.json()["issues"]
    assert {"kind": "missing_value", "column": "zip", "row_indices": [1, 2]} in issues
    assert {"kind": "exact_duplicate_row", "column": None, "row_indices": [1, 2]} in issues
    assert content == b'id,zip,note\r\n001,00501,"hello\r\nworld"\r\n002,,x\r\n002,,x\r\n'


def test_invalid_upload() -> None:
    client = TestClient(create_app(), base_url="http://localhost", client=("127.0.0.1", 50000))
    assert (
        client.post(
            "/uploads", content=b"id\n\xff\n", headers={"content-type": "text/csv"}
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/uploads", content=b"id\n" + b"a" * 1_000_000, headers={"content-type": "text/csv"}
        ).status_code
        == 413
    )
    assert (
        client.post(
            "/uploads", content=b"id\n1", headers={"content-type": "application/json"}
        ).status_code
        == 415
    )


def test_unknown_job() -> None:
    client = TestClient(create_app(), base_url="http://localhost", client=("127.0.0.1", 50000))
    assert client.post("/analyses/" + str(uuid4())).status_code == 404
    assert client.post("/analyses/invalid").status_code == 422
    a = client.post("/uploads", content=b"id\n001\n", headers={"content-type": "text/csv"}).json()
    b = client.post("/uploads", content=b'id\n""\n', headers={"content-type": "text/csv"}).json()
    assert a["upload_id"] != b["upload_id"]
    assert client.post("/analyses/" + a["upload_id"]).json()["issues"] == []
