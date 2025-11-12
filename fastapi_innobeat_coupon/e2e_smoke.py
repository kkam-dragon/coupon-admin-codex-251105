from __future__ import annotations

from fastapi.testclient import TestClient

from app.api import deps
from app.main import app


def _override_current_user():
    user = type("User", (), {"id": 1, "username": "tester"})()
    session = type("Session", (), {"jwt_id": "dummy"})()
    return deps.AuthenticatedUser(user=user, roles={"ADMIN"}, session=session, token_jti="dummy")


def run_smoke() -> None:
    app.dependency_overrides[deps.get_current_user] = _override_current_user
    client = TestClient(app)
    client.get("/health/ping").raise_for_status()
    resp = client.get("/send-query/campaigns?limit=1")
    resp.raise_for_status()
    print("Smoke test completed. items=", len(resp.json().get("items", [])))


if __name__ == "__main__":
    run_smoke()
