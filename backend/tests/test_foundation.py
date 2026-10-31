from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.optimizer import smoke_solve
from app.schema import INDEXES, SCHEMAS


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("MONGODB_URI", "")
    get_settings.cache_clear()
    with TestClient(app) as client:
        yield client
    get_settings.cache_clear()


def test_health_and_unconfigured_readiness(client):
    assert client.get("/api/health").json()["status"] == "ok"
    assert client.get("/api/ready").status_code == 503
    assert client.get("/api/me").status_code == 401


def test_verified_roles_and_community_isolation(client, monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()
    monkeypatch.setenv("AUTH_PUBLIC_KEY", public)
    monkeypatch.setenv("AUTH_ISSUER", "https://test.clerk.accounts.dev")
    get_settings.cache_clear()
    now = datetime.now(timezone.utc)
    claims = {"sub": "clerk-user", "iss": "https://test.clerk.accounts.dev", "azp": "http://localhost:5173", "iat": now, "nbf": now, "exp": now + timedelta(minutes=5), "role": "platform_admin"}
    token = jwt.encode(claims, key, algorithm="RS256")
    headers = {"Authorization": f"Bearer {token}"}
    db = AsyncMock()
    db.users.find_one.return_value = {"_id": "user-id", "role": "resident"}
    db.memberships.find_one.return_value = None
    app.state.db = db
    assert client.get("/api/me", headers=headers).json()["role"] == "resident"
    assert client.get("/api/admin/access", headers=headers).status_code == 403
    assert client.get("/api/communities/other/access", headers=headers).status_code == 403
    db.memberships.find_one.assert_awaited_with({"community_id": "other", "user_id": "user-id", "status": "active"})
    db.users.find_one.return_value = {"_id": "admin-id", "role": "platform_admin"}
    assert client.get("/api/admin/access", headers=headers).status_code == 200
    claims["exp"] = now - timedelta(minutes=1)
    expired = jwt.encode(claims, key, algorithm="RS256")
    assert client.get("/api/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401


def test_solver_and_collection_coverage():
    assert smoke_solve() == 7
    assert set(SCHEMAS) == set(INDEXES)
    assert "exit_cases" in SCHEMAS
