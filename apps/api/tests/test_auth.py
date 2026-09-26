import time

import pyotp

from app.core.config import get_settings

PASSWORD = "correct horse battery staple"


async def register(client, email="alice@example.com", password=PASSWORD):
    return await client.post("/auth/register", json={"email": email, "password": password})


async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
    assert r.headers["x-frame-options"] == "DENY"


async def test_register_creates_session_and_first_user_is_admin(client, make_client):
    r = await register(client, email="Alice@Example.com")
    assert r.status_code == 201
    assert r.json()["email"] == "alice@example.com"
    assert r.json()["is_superuser"] is True
    set_cookie = r.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie

    me = await client.get("/auth/me")
    assert me.status_code == 200

    async with make_client() as other:
        r2 = await register(other, email="bob@example.com")
        assert r2.json()["is_superuser"] is False


async def test_register_rejects_duplicates_and_short_passwords(client, make_client):
    await register(client)
    async with make_client() as other:
        assert (await register(other)).status_code == 409
        assert (await register(other, email="c@example.com", password="short")).status_code == 422


async def test_registration_can_be_disabled_after_first_user(app, client, make_client):
    closed = get_settings().model_copy(update={"allow_registration": False})
    app.dependency_overrides[get_settings] = lambda: closed
    assert (await register(client)).status_code == 201
    async with make_client() as other:
        assert (await register(other, email="bob@example.com")).status_code == 403


async def test_login_logout(client, make_client):
    await register(client)
    async with make_client() as c:
        bad = await c.post("/auth/login", json={"email": "alice@example.com", "password": "nope"})
        assert bad.status_code == 401
        missing = await c.post("/auth/login", json={"email": "x@example.com", "password": "nope"})
        assert missing.status_code == 401
        assert missing.json() == bad.json()

        ok = await c.post("/auth/login", json={"email": "alice@example.com", "password": PASSWORD})
        assert ok.status_code == 200
        assert ok.json()["mfa_required"] is False
        assert (await c.get("/auth/me")).status_code == 200

        assert (await c.post("/auth/logout")).status_code == 204
        assert (await c.get("/auth/me")).status_code == 401


async def test_cross_origin_writes_are_blocked(client):
    r = await client.post(
        "/auth/register",
        json={"email": "a@example.com", "password": PASSWORD},
        headers={"Origin": "https://evil.example"},
    )
    assert r.status_code == 403

    client.headers.pop("Origin")
    r = await client.post("/auth/login", json={"email": "a@example.com", "password": PASSWORD})
    assert r.status_code == 403


async def test_login_is_rate_limited_per_email(client, make_client):
    await register(client)
    limit = get_settings().login_rate_limit_per_email
    async with make_client() as c:
        for _ in range(limit):
            await c.post("/auth/login", json={"email": "alice@example.com", "password": "wrong"})
        r = await c.post("/auth/login", json={"email": "alice@example.com", "password": PASSWORD})
        assert r.status_code == 429


async def test_mfa_flow(client, make_client):
    await register(client)
    setup = (await client.post("/auth/mfa/setup")).json()
    totp = pyotp.TOTP(setup["secret"])
    now = time.time()

    assert (await client.post("/auth/mfa/enable", json={"code": "000000"})).status_code == 400
    enabled = await client.post("/auth/mfa/enable", json={"code": totp.at(now)})
    assert enabled.status_code == 200
    assert enabled.json()["mfa_enabled"] is True

    async with make_client() as c:
        r = await c.post("/auth/login", json={"email": "alice@example.com", "password": PASSWORD})
        assert r.json() == {"mfa_required": True, "user": None}
        # Password alone is not enough.
        assert (await c.get("/auth/me")).status_code == 401

        # The code already used to enable MFA can't be replayed.
        replay = await c.post("/auth/login/mfa", json={"code": totp.at(now)})
        assert replay.status_code == 401

        ok = await c.post("/auth/login/mfa", json={"code": totp.at(now + totp.interval)})
        assert ok.status_code == 200
        assert (await c.get("/auth/me")).status_code == 200


async def test_enabling_mfa_signs_out_other_sessions(client, make_client):
    await register(client)
    async with make_client() as other:
        await other.post("/auth/login", json={"email": "alice@example.com", "password": PASSWORD})
        assert (await other.get("/auth/me")).status_code == 200

        secret = (await client.post("/auth/mfa/setup")).json()["secret"]
        await client.post("/auth/mfa/enable", json={"code": pyotp.TOTP(secret).now()})

        assert (await other.get("/auth/me")).status_code == 401
        assert (await client.get("/auth/me")).status_code == 200


async def test_mfa_secret_is_encrypted_at_rest(app, client):
    from sqlalchemy import select

    from app.db.session import get_db
    from app.models import User

    await register(client)
    secret = (await client.post("/auth/mfa/setup")).json()["secret"]
    async for db in app.dependency_overrides[get_db]():
        user = await db.scalar(select(User))
        assert user.totp_pending_secret_enc
        assert secret not in user.totp_pending_secret_enc
