import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from aiosmtpd.controller import Controller
from sqlalchemy import select

from app.core import mail
from app.core.config import get_settings
from app.maintenance import cleanup_expired, reap_stuck_scans
from app.models import (
    ActionToken,
    AuditEvent,
    Scan,
    ScanKind,
    ScanStatus,
    Target,
    User,
    UserSession,
)

PASSWORD = "correct horse battery staple"


async def register(client, email):
    r = await client.post("/auth/register", json={"email": email, "password": PASSWORD})
    assert r.status_code == 201, r.text
    return r.json()


def sent_emails(app):
    return [a for a in app.state.enqueued if a[0] == "send_email"]


def link_token(app):
    """The token from the most recent email's link."""
    return sent_emails(app)[-1][4][1].split("token=")[1]


@pytest.fixture
def smtp(monkeypatch):
    monkeypatch.setattr(get_settings(), "smtp_host", "mail.example.test")


# ---------- admin ----------


async def test_admin_routes_require_superuser(client, make_client):
    await register(client, "admin@example.com")  # first user = admin
    async with make_client() as other:
        await register(other, "user@example.com")
        assert (await other.get("/admin/overview")).status_code == 403
        assert (await other.get("/admin/users")).status_code == 403
    r = await client.get("/admin/overview")
    assert r.status_code == 200
    assert r.json()["users"] == 2


async def test_admin_manages_users_settings_and_blocklist(app, client, make_client, monkeypatch):
    monkeypatch.setattr(get_settings(), "scan_allow_private", False)
    admin = await register(client, "admin@example.com")
    async with make_client() as other:
        user = await register(other, "user@example.com")

        # Can't lock yourself out.
        r = await client.patch(f"/admin/users/{admin['id']}", json={"is_active": False})
        assert r.status_code == 409

        # Deactivating signs the user out.
        r = await client.patch(f"/admin/users/{user['id']}", json={"is_active": False})
        assert r.status_code == 200 and r.json()["is_active"] is False
        assert (await other.get("/auth/me")).status_code == 401

    # Close registration.
    r = await client.patch(
        "/admin/settings", json={"registration_open": False, "max_targets_per_org": 0}
    )
    assert r.json()["registration_open"] is False
    async with make_client() as late:
        assert (
            await late.post(
                "/auth/register", json={"email": "late@example.com", "password": PASSWORD}
            )
        ).status_code == 403
        assert (await late.get("/auth/config")).json() == {
            "registration_open": False,
            "email_enabled": False,
        }

    # Website limit.
    r = await client.post("/targets", json={"url": "example.com"})
    assert r.status_code == 409 and "limit" in r.json()["detail"]
    await client.patch("/admin/settings", json={"max_targets_per_org": 10})

    # Blocklist covers subdomains.
    r = await client.post(
        "/admin/blocked-domains", json={"domain": "https://Example.com/", "reason": "Not ours"}
    )
    assert r.status_code == 201 and r.json()["domain"] == "example.com"
    assert (
        await client.post("/admin/blocked-domains", json={"domain": "example.com"})
    ).status_code == 409
    r = await client.post("/targets", json={"url": "shop.example.com"})
    assert r.status_code == 422 and "can't be added" in r.json()["detail"]

    actions = [e["action"] for e in (await client.get("/admin/audit")).json()]
    assert {
        "admin.user.updated",
        "admin.settings.updated",
        "admin.domain.blocked",
        "user.registered",
    } <= set(actions)


async def test_kill_switch_blocks_new_and_queued_scans(app, client, monkeypatch):
    from app.scanning.pipeline import run_scan

    monkeypatch.setattr(get_settings(), "scan_allow_private", True)
    await register(client, "admin@example.com")
    async with app.state.sessionmaker() as db:
        org = await db.scalar(
            select(__import__("app.models", fromlist=["Organization"]).Organization)
        )
        t = Target(
            org_id=org.id,
            url="http://127.0.0.1:9/",
            hostname="127.0.0.1",
            verification_token="x",
            verified_at=datetime.now(UTC),
        )
        db.add(t)
        await db.flush()
        queued = Scan(org_id=org.id, target_id=t.id, kind=ScanKind.dast, status=ScanStatus.queued)
        db.add(queued)
        await db.commit()
        target_id, scan_id = t.id, queued.id

    await client.patch(
        "/admin/settings", json={"scanning_paused": True, "scanning_paused_reason": "Maintenance"}
    )
    r = await client.post(f"/targets/{target_id}/scans", json={"authorized": True})
    assert r.status_code == 503 and "Maintenance" in r.json()["detail"]

    await run_scan(app.state.sessionmaker, scan_id, scanners=[])
    async with app.state.sessionmaker() as db:
        scan = await db.get(Scan, scan_id)
        assert scan.status == ScanStatus.failed and "paused" in scan.error


# ---------- email & passwords ----------


async def test_verification_email_flow(app, client, make_client, smtp):
    await register(client, "admin@example.com")  # admins are exempt
    async with make_client() as c:
        me = await register(c, "user@example.com")
        assert me["email_verification_required"] is True
        _, to, subject, *_ = sent_emails(app)[-1]
        assert to == "user@example.com" and "Confirm" in subject
        assert (await c.post("/targets", json={"url": "example.com"})).status_code == 403

        token = link_token(app)
        r = await c.post("/auth/email/verify", json={"token": token})
        assert r.status_code == 200 and r.json()["email_verified"] is True
        # Single use.
        assert (await c.post("/auth/email/verify", json={"token": token})).status_code == 400
        assert (await c.get("/auth/me")).json()["email_verification_required"] is False


async def test_password_reset_flow(app, client, make_client, smtp):
    await register(client, "admin@example.com")
    async with make_client() as c:
        await register(c, "user@example.com")
        assert (await c.get("/auth/me")).status_code == 200

        async with make_client() as anon:
            # Same answer for unknown accounts.
            r1 = await anon.post("/auth/password/forgot", json={"email": "nobody@example.com"})
            r2 = await anon.post("/auth/password/forgot", json={"email": "USER@example.com"})
            assert r1.status_code == r2.status_code == 202 and r1.json() == r2.json()
            token = link_token(app)
            assert (
                await anon.post("/auth/password/reset", json={"token": token, "password": "short"})
            ).status_code == 422
            r = await anon.post(
                "/auth/password/reset",
                json={"token": token, "password": "a brand new long passphrase"},
            )
            assert r.status_code == 204
            assert (
                await anon.post(
                    "/auth/password/reset",
                    json={"token": token, "password": "another long passphrase"},
                )
            ).status_code == 400

        # Existing sessions were signed out; the new password works.
        assert (await c.get("/auth/me")).status_code == 401
        r = await c.post(
            "/auth/login",
            json={"email": "user@example.com", "password": "a brand new long passphrase"},
        )
        assert r.status_code == 200


async def test_expired_reset_token_is_rejected(app, client, smtp):
    await register(client, "admin@example.com")
    await client.post("/auth/password/forgot", json={"email": "admin@example.com"})
    token = link_token(app)
    async with app.state.sessionmaker() as db:
        row = await db.scalar(select(ActionToken))
        row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        await db.commit()
    r = await client.post(
        "/auth/password/reset", json={"token": token, "password": "a brand new long passphrase"}
    )
    assert r.status_code == 400


async def test_forgot_password_without_smtp(client):
    await register(client, "admin@example.com")
    assert (
        await client.post("/auth/password/forgot", json={"email": "admin@example.com"})
    ).status_code == 409


async def test_change_password(client, make_client):
    await register(client, "admin@example.com")
    async with make_client() as other:
        await other.post("/auth/login", json={"email": "admin@example.com", "password": PASSWORD})
        r = await client.post(
            "/auth/password/change",
            json={"current_password": "wrong", "new_password": "a brand new long passphrase"},
        )
        assert r.status_code == 400
        r = await client.post(
            "/auth/password/change",
            json={"current_password": PASSWORD, "new_password": "a brand new long passphrase"},
        )
        assert r.status_code == 204
        assert (await client.get("/auth/me")).status_code == 200  # this session stays
        assert (await other.get("/auth/me")).status_code == 401  # others are signed out


async def test_smtp_send_really_delivers(monkeypatch):
    received = []

    class Handler:
        async def handle_DATA(self, server, session, envelope):
            received.append(envelope)
            return "250 OK"

    import socket

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    controller = Controller(Handler(), hostname="127.0.0.1", port=port)
    controller.start()
    try:
        s = get_settings()
        monkeypatch.setattr(s, "smtp_host", "127.0.0.1")
        monkeypatch.setattr(s, "smtp_port", port)
        monkeypatch.setattr(s, "smtp_security", "none")
        msg = mail.build_message(
            "to@example.com", "Hello <b>", ["Line one & two"], ("Open", "https://x.test/?a=1&b=2")
        )
        assert await mail.send(msg) is True
        await asyncio.sleep(0.1)
        from email import message_from_bytes, policy

        parsed = message_from_bytes(received[0].content, policy=policy.default)
        body = parsed.get_body(("html",)).get_content()
        assert parsed.get_body(("plain",)).get_content().startswith("Line one & two")
        assert received[0].rcpt_tos == ["to@example.com"]
        assert "Line one &amp; two" in body and "https://x.test/?a=1&amp;b=2" in body
        assert "Powered by SecAI by hdbrzgr" in body
    finally:
        controller.stop()


# ---------- housekeeping ----------


async def test_housekeeping(app, client):
    await register(client, "admin@example.com")
    now = datetime.now(UTC)
    async with app.state.sessionmaker() as db:
        user = await db.scalar(select(User))
        from app.models import Organization

        org = await db.scalar(select(Organization))
        db.add(
            UserSession(
                user_id=user.id,
                token_hash="a" * 64,
                expires_at=now - timedelta(hours=1),
                mfa_verified=True,
            )
        )
        db.add(
            ActionToken(
                user_id=user.id,
                purpose="verify_email",
                token_hash="b" * 64,
                expires_at=now,
                used_at=now,
            )
        )
        db.add(
            Scan(
                org_id=org.id,
                kind=ScanKind.dast,
                status=ScanStatus.running,
                started_at=now - timedelta(hours=3),
            )
        )
        db.add(
            Scan(
                org_id=org.id,
                kind=ScanKind.dast,
                status=ScanStatus.running,
                started_at=now - timedelta(minutes=5),
            )
        )
        await db.commit()

    removed = await cleanup_expired(app.state.sessionmaker)
    assert removed == {"sessions": 1, "tokens": 1}
    assert (await client.get("/auth/me")).status_code == 200  # the live session survives
    assert await reap_stuck_scans(app.state.sessionmaker) == 1
    async with app.state.sessionmaker() as db:
        statuses = sorted(s.status.value for s in (await db.scalars(select(Scan))).all())
        assert statuses == ["failed", "running"]
        assert (
            await db.scalar(select(AuditEvent).where(AuditEvent.action == "user.registered"))
        ) is not None
    assert uuid.UUID(str(user.id))
