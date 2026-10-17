def register(client, email="alice@example.com", password="correct-horse-battery"):
    resp = client.post("/api/auth/register", json={"email": email, "password": password})
    assert resp.status_code == 201, resp.text
    return resp.json()
