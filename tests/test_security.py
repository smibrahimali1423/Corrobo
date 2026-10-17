from security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_roundtrip():
    hashed = hash_password("s3cret-password")
    assert hashed != "s3cret-password"
    assert verify_password("s3cret-password", hashed)
    assert not verify_password("wrong-password", hashed)


def test_verify_password_handles_malformed_hash():
    assert verify_password("anything", "not-a-bcrypt-hash") is False


def test_token_roundtrip():
    assert decode_access_token(create_access_token(42)) == 42


def test_expired_token_is_rejected():
    assert decode_access_token(create_access_token(42, expires_minutes=-1)) is None


def test_tampered_token_is_rejected():
    token = create_access_token(42)
    assert decode_access_token(token[:-2] + ("aa" if token[-2:] != "aa" else "bb")) is None
