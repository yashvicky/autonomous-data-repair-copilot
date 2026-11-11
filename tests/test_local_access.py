from fastapi.testclient import TestClient

from data_repair_copilot.api.app import create_app


def test_local_requests() -> None:
    client = TestClient(create_app(), base_url="http://localhost:8000", client=("127.0.0.1", 1))
    assert client.get("/").status_code == 200
    result = client.post(
        "/uploads",
        content=b"id\n001\n",
        headers={"content-type": "text/csv", "origin": "http://localhost:8000"},
    )
    assert result.status_code == 201
    ipv6 = TestClient(create_app(), base_url="http://[::1]:8000", client=("::1", 1))
    assert ipv6.get("/").status_code == 200


def test_untrusted_requests() -> None:
    app = create_app()
    local = TestClient(app, base_url="http://localhost:8000", client=("127.0.0.1", 1))
    remote = TestClient(app, base_url="http://localhost:8000", client=("192.0.2.8", 1))
    assert remote.get("/").status_code == 403
    assert (
        local.get("/", headers=[("host", "localhost:8000"), ("host", "evil.example")]).status_code
        == 403
    )
    assert (
        local.get(
            "/", headers=[("origin", "http://localhost:8000"), ("origin", "https://evil.example")]
        ).status_code
        == 403
    )
    for headers in (
        {"host": "attacker.example"},
        {"host": "localhost.attacker.example"},
        {"host": "127.0.0.1:99999"},
        {"origin": "https://evil.example"},
        {"origin": "null"},
        {"origin": "http://localhost:9000"},
        {"x-forwarded-for": "127.0.0.1"},
        {"forwarded": "for=127.0.0.1"},
        {"x-real-ip": "127.0.0.1"},
    ):
        assert (
            local.post(
                "/uploads", content=b"id\n1\n", headers={"content-type": "text/csv", **headers}
            ).status_code
            == 403
        )
