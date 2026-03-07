from types import SimpleNamespace
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

import server


client = TestClient(server.app)


def test_vectorize_file_rejects_missing_authorization_header():
    response = client.post(
        "/api/vectorize-file",
        json={"storage_path": "roads/sample.csv"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Missing Authorization header"}


def test_vectorize_file_rejects_non_bearer_auth_scheme():
    response = client.post(
        "/api/vectorize-file",
        headers={"Authorization": "abc 123"},
        json={"storage_path": "roads/sample.csv"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}


def test_vectorize_file_rejects_invalid_token(monkeypatch):
    mock_supabase = MagicMock()
    mock_supabase.auth.get_user.return_value = SimpleNamespace(user=None)
    monkeypatch.setattr(server, "get_supabase_client", lambda: mock_supabase)

    response = client.post(
        "/api/vectorize-file",
        headers={"Authorization": "Bearer fake-token"},
        json={"storage_path": "roads/sample.csv"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}


def test_vectorize_file_allows_valid_token_and_calls_pipeline(monkeypatch):
    mock_supabase = MagicMock()
    mock_supabase.auth.get_user.return_value = SimpleNamespace(
        user=SimpleNamespace(id="user-123")
    )
    monkeypatch.setattr(server, "get_supabase_client", lambda: mock_supabase)

    expected = {"ok": True, "source": "roads/sample.csv"}

    async def fake_vectorize_and_store_supabase_file(storage_location, bucket):
        assert storage_location == "roads/sample.csv"
        assert bucket == "city-docs"
        return expected

    monkeypatch.setattr(
        server,
        "vectorize_and_store_supabase_file",
        fake_vectorize_and_store_supabase_file,
    )

    response = client.post(
        "/api/vectorize-file",
        headers={"Authorization": "Bearer valid-token"},
        json={"storage_path": "roads/sample.csv", "bucket": "city-docs"},
    )

    assert response.status_code == 200
    assert response.json() == expected
