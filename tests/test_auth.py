from tests.helpers import register


def test_register_returns_token_and_user(client):
    body = register(client, email="Alice@Example.com")
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "alice@example.com"  # normalized
    assert "password" not in str(body["user"]).lower()


def test_register_duplicate_email_conflicts(client):
    register(client, email="alice@example.com")
    resp = client.post(
        "/api/auth/register", json={"email": "ALICE@example.com", "password": "another-password"}
    )
    assert resp.status_code == 409


def test_register_rejects_short_password_and_bad_email(client):
    assert (
        client.post(
            "/api/auth/register", json={"email": "a@example.com", "password": "short"}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/auth/register", json={"email": "not-an-email", "password": "long-enough-pw"}
        ).status_code
        == 422
    )


def test_login_success_and_me(client):
    register(client, email="alice@example.com", password="correct-horse-battery")
    resp = client.post(
        "/api/auth/login",
        json={"email": "alice@example.com", "password": "correct-horse-battery"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "alice@example.com"


def test_login_wrong_password_and_unknown_email_look_identical(client):
    register(client, email="alice@example.com")
    wrong_pw = client.post(
        "/api/auth/login", json={"email": "alice@example.com", "password": "nope-nope"}
    )
    unknown = client.post(
        "/api/auth/login", json={"email": "ghost@example.com", "password": "nope-nope"}
    )
    assert wrong_pw.status_code == unknown.status_code == 401
    assert wrong_pw.json() == unknown.json()


def test_me_rejects_missing_and_invalid_tokens(client):
    assert client.get("/api/auth/me").status_code == 401
    bad = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert bad.status_code == 401


def test_token_for_deleted_user_is_rejected(client, db):
    from models import User

    token = register(client)["access_token"]
    db.query(User).delete()
    db.commit()

    resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
