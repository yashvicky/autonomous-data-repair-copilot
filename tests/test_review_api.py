from uuid import uuid4

from fastapi.testclient import TestClient

from data_repair_copilot.api.app import create_app


def setup_review(client: TestClient, replacement="fixed") -> tuple[str, str]:
    upload = client.post(
        "/uploads", content=b"id,value\n001,bad\n002,keep\n", headers={"content-type": "text/csv"}
    )
    assert upload.status_code == 201
    preview = client.post(
        f"/uploads/{upload.json()['upload_id']}/previews",
        json={
            "proposals": [
                {"row_index": 0, "column": "value", "proposed_value": replacement},
                {"row_index": 1, "column": "value", "proposed_value": "changed"},
            ]
        },
    )
    assert preview.status_code == 201
    assert preview.json()["preview"]["changes"][0]["before"] == "bad"
    return upload.json()["upload_id"], preview.json()["review_id"]


def decisions():
    return {
        "decisions": [
            {"change_index": 0, "action": "approve"},
            {"change_index": 1, "action": "reject"},
        ],
        "metadata": {
            "0": {"reason": "synthetic", "approver": "test", "confidence": None},
            "1": {"reason": "synthetic", "approver": "test", "confidence": None},
        },
    }


def test_local_review_workflow() -> None:
    client = TestClient(create_app())
    upload_id, review = setup_review(client)
    assert client.get(f"/reviews/{review}/export").status_code == 409
    assert client.post(f"/reviews/{review}/decisions", json=decisions()).status_code == 200
    audit = client.get(f"/reviews/{review}/audit").json()
    assert [entry["action"] for entry in audit["entries"]] == ["approve", "reject"]
    assert audit["entries"][0]["original"] == "bad"
    assert client.get(f"/reviews/{review}/export").text == "id,value\n001,fixed\n002,keep\n"
    assert client.post(f"/reviews/{review}/decisions", json=decisions()).status_code == 409
    again = client.post(
        f"/uploads/{upload_id}/previews",
        json={"proposals": [{"row_index": 0, "column": "value", "proposed_value": "other"}]},
    )
    assert again.json()["preview"]["changes"][0]["before"] == "bad"


def test_invalid_decisions() -> None:
    client = TestClient(create_app())
    assert client.get(f"/reviews/{uuid4()}/audit").status_code == 404
    _, review = setup_review(client)
    data = decisions()
    data["decisions"] = data["decisions"][:1]
    assert client.post(f"/reviews/{review}/decisions", json=data).status_code == 400
    assert client.get(f"/reviews/{review}/export").status_code == 409
    assert client.post(f"/reviews/{review}/decisions", json=decisions()).status_code == 200


def test_null_export() -> None:
    client = TestClient(create_app())
    _, review = setup_review(client, replacement=None)
    assert client.post(f"/reviews/{review}/decisions", json=decisions()).status_code == 200
    assert client.get(f"/reviews/{review}/export").status_code == 409
    assert client.get(f"/reviews/{review}/audit").status_code == 200
