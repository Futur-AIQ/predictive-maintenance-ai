import pytest
from fastapi.testclient import TestClient


def test_login_success(client, admin_user):
    resp = client.post(
        "/api/auth/login",
        data={"username": "admin@test.com", "password": "Admin@123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "admin@test.com"
    assert data["user"]["role"] == "admin"


def test_login_wrong_password(client, admin_user):
    resp = client.post(
        "/api/auth/login",
        data={"username": "admin@test.com", "password": "WrongPassword!"},
    )
    assert resp.status_code == 401
    assert "Incorrect email or password" in resp.json()["detail"]


def test_login_unknown_email(client):
    resp = client.post(
        "/api/auth/login",
        data={"username": "nobody@test.com", "password": "anything"},
    )
    assert resp.status_code == 401


def test_register_as_admin(client, admin_token):
    resp = client.post(
        "/api/auth/register",
        json={
            "email": "newengineer@test.com",
            "password": "NewUser@123",
            "full_name": "New Engineer",
            "role": "engineer",
        },
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["email"] == "newengineer@test.com"
    assert data["role"] == "engineer"


def test_register_forbidden_as_engineer(client, engineer_token):
    resp = client.post(
        "/api/auth/register",
        json={
            "email": "another@test.com",
            "password": "Another@123",
            "full_name": "Another User",
            "role": "engineer",
        },
        headers={"Authorization": f"Bearer {engineer_token}"},
    )
    assert resp.status_code == 403


def test_refresh_token(client, admin_user):
    login_resp = client.post(
        "/api/auth/login",
        data={"username": "admin@test.com", "password": "Admin@123"},
    )
    refresh_token = login_resp.json()["refresh_token"]

    resp = client.post(
        "/api/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_get_me(client, engineer_token, engineer_user):
    resp = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {engineer_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "engineer@test.com"
    assert data["role"] == "engineer"
    assert data["full_name"] == "Test Engineer"


def test_get_me_unauthenticated(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401
