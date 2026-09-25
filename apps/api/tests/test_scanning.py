import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from app.core.config import get_settings
from app.models import Severity
from app.scanning.normalize import RawFinding, dedupe, grade
from app.scanning.pipeline import run_scan
from app.scanning.scanners.base import ScanContext
from app.scanning.scanners.exposure import ExposureScanner
from app.scanning.scanners.headers import HeadersScanner
from app.scanning.scanners.nuclei import parse_line
from app.scanning.scanners.tls import TlsScanner
from app.scanning.targets import InvalidTarget, normalize_url

PASSWORD = "correct horse battery staple"


class Site:
    """A deliberately insecure local website."""

    token = ""
    meta = False


def make_handler(site):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            routes = {
                "/.well-known/secai-verify.txt": (200, site.token),
                "/.git/HEAD": (200, "ref: refs/heads/main\n"),
                "/.env": (200, "SECRET_KEY=abc123\nDB_PASSWORD=hunter2\n"),
            }
            if self.path == "/":
                body = "<html><head>"
                if site.meta:
                    body += f'<meta name="secai-verify" content="{site.token}">'
                body += "</head><body>Hello</body></html>"
                self.send_response(200)
                self.send_header("Server", "Apache/2.4.49 (Unix)")
                self.send_header("Set-Cookie", "sessionid=abc; Path=/")
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(body.encode())
                return
            status, body = routes.get(self.path, (404, "not found"))
            self.send_response(status)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(body.encode())

    return Handler


@pytest.fixture
def allow_private(monkeypatch):
    monkeypatch.setattr(get_settings(), "scan_allow_private", True)


@pytest.fixture
def site(allow_private):
    s = Site()
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(s))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    s.url = f"http://127.0.0.1:{server.server_address[1]}"
    yield s
    server.shutdown()


async def signed_in(client):
    r = await client.post(
        "/auth/register", json={"email": "owner@example.com", "password": PASSWORD}
    )
    assert r.status_code == 201


# ---------- unit ----------


@pytest.mark.parametrize(
    ("raw", "url", "host"),
    [
        ("example.com", "https://example.com/", "example.com"),
        ("HTTPS://Shop.Example.COM/some/path?q=1", "https://shop.example.com/", "shop.example.com"),
        ("http://example.com:8080", "http://example.com:8080/", "example.com"),
        ("bücher.example", "https://xn--bcher-kva.example/", "xn--bcher-kva.example"),
    ],
)
def test_normalize_url(raw, url, host):
    assert normalize_url(raw) == (url, host)


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "ftp://example.com",
        "https://user:pw@example.com",
        "93.184.215.14",
        "localhost",
        "exa mple.com",
    ],
)
def test_normalize_url_rejects(raw):
    with pytest.raises(InvalidTarget):
        normalize_url(raw)


def test_dedupe_keeps_highest_severity_and_grade():
    a = RawFinding(tool="ZAP", rule_id="x", title="X", severity=Severity.low, url="https://a/")
    b = RawFinding(tool="Nuclei", rule_id="x", title="X", severity=Severity.high, url="https://a")
    c = RawFinding(
        tool="Headers", rule_id="y", title="Y", severity=Severity.medium, url="https://a/"
    )
    out = dedupe([a, b, c])
    assert [f.severity for f in out] == [Severity.high, Severity.medium]
    score, letter, counts = grade(out)
    assert counts["high"] == 1 and counts["medium"] == 1
    assert letter in ("C", "D") and score <= 79
    assert grade([])[1] == "A"
    crit = RawFinding(tool="t", rule_id="c", title="C", severity=Severity.critical, url="u")
    assert grade([crit])[1] == "F"


def test_nuclei_jsonl_parsing():
    line = (
        '{"template-id":"git-config","info":{"name":"Git Config Disclosure","severity":"medium",'
        '"description":"Git config exposed","remediation":"Block /.git","reference":["https://ex.com/a"],'
        '"classification":{"cwe-id":["cwe-200"]}},"matched-at":"https://example.com/.git/config",'
        '"matcher-name":"status"}'
    )
    f = parse_line(line)
    assert f.rule_id == "nuclei.git-config"
    assert f.severity == Severity.medium
    assert f.cwe == "CWE-200"
    assert f.url == "https://example.com/.git/config"
    assert f.recommendation == "Block /.git"
    assert parse_line("not json") is None


# ---------- API ----------


async def test_private_targets_are_refused_in_strict_mode(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "scan_allow_private", False)
    await signed_in(client)
    r = await client.post("/targets", json={"url": "http://127.0.0.1:8080"})
    assert r.status_code == 422
    r = await client.post("/targets", json={"url": "localhost.localdomain"})
    assert r.status_code == 422


async def test_full_scan_flow(app, client, site):
    await signed_in(client)
    r = await client.post("/targets", json={"url": site.url})
    assert r.status_code == 201, r.text
    target = r.json()
    assert target["verified_at"] is None
    site.token = target["verification_token"]

    # Can't scan before verifying.
    r = await client.post(f"/targets/{target['id']}/scans", json={"authorized": True})
    assert r.status_code == 409

    # Wrong method first: no meta tag on the page.
    r = await client.post(f"/targets/{target['id']}/verify", json={"method": "meta_tag"})
    assert r.status_code == 422
    r = await client.post(f"/targets/{target['id']}/verify", json={"method": "well_known_file"})
    assert r.status_code == 200, r.text
    assert r.json()["verified_at"]

    # The attestation is required every time.
    r = await client.post(f"/targets/{target['id']}/scans", json={"authorized": False})
    assert r.status_code == 422
    r = await client.post(f"/targets/{target['id']}/scans", json={"authorized": True})
    assert r.status_code == 202, r.text
    scan_id = r.json()["id"]
    assert app.state.enqueued == [("run_scan", scan_id)]

    # Only one scan per website at a time.
    r = await client.post(f"/targets/{target['id']}/scans", json={"authorized": True})
    assert r.status_code == 409

    await run_scan(
        app.state.sessionmaker,
        uuid.UUID(scan_id),
        scanners=[HeadersScanner(), TlsScanner(), ExposureScanner()],
    )

    scan = (await client.get(f"/scans/{scan_id}")).json()
    assert scan["status"] == "succeeded"
    assert scan["progress"] == 100
    rules = {f["rule_id"] for f in scan["findings"]}
    assert {
        "exposure/.env",
        "exposure/.git/HEAD",
        "headers.missing-csp",
        "headers.no-https",
    } <= rules
    assert "headers.version-disclosure-server" in rules
    cookie = next(
        f for f in scan["findings"] if f["rule_id"].startswith("headers.cookie-flags.sessionid")
    )
    assert "abc" not in cookie["evidence"] and "[redacted]" in cookie["evidence"]
    # Secrets file contents are never stored.
    env = next(f for f in scan["findings"] if f["rule_id"] == "exposure/.env")
    assert "hunter2" not in (env["evidence"] or "")
    assert scan["findings"][0]["severity"] == "critical"
    assert scan["summary"]["grade"] == "F"
    assert scan["summary"]["counts"]["critical"] == 1
    tools = {t["name"]: t["status"] for t in scan["summary"]["tools"]}
    assert tools == {"headers": "ok", "tls": "ok", "exposure": "ok"}

    listed = (await client.get("/targets")).json()
    assert listed[0]["last_scan"]["summary"]["grade"] == "F"


async def test_meta_tag_verification(client, site):
    await signed_in(client)
    target = (await client.post("/targets", json={"url": site.url})).json()
    site.token = target["verification_token"]
    site.meta = True
    r = await client.post(f"/targets/{target['id']}/verify", json={"method": "meta_tag"})
    assert r.status_code == 200


async def test_targets_are_scoped_to_the_workspace(client, make_client, site):
    await signed_in(client)
    target = (await client.post("/targets", json={"url": site.url})).json()
    assert (await client.post("/targets", json={"url": site.url})).status_code == 409
    async with make_client() as other:
        await other.post(
            "/auth/register", json={"email": "intruder@example.com", "password": PASSWORD}
        )
        assert (await other.get(f"/targets/{target['id']}")).status_code == 404
        assert (
            await other.post(f"/targets/{target['id']}/verify", json={"method": "dns_txt"})
        ).status_code == 404
        assert (await other.get("/targets")).json() == []


async def test_daily_scan_limit(app, client, site, monkeypatch):
    monkeypatch.setattr(get_settings(), "scans_per_day_per_org", 1)
    await signed_in(client)
    target = (await client.post("/targets", json={"url": site.url})).json()
    site.token = target["verification_token"]
    await client.post(f"/targets/{target['id']}/verify", json={"method": "well_known_file"})
    first = (await client.post(f"/targets/{target['id']}/scans", json={"authorized": True})).json()
    await run_scan(app.state.sessionmaker, uuid.UUID(first["id"]), scanners=[HeadersScanner()])
    r = await client.post(f"/targets/{target['id']}/scans", json={"authorized": True})
    assert r.status_code == 429


async def test_unverified_target_scan_job_fails_safely(app, client, site):
    """Even if a job is queued for an unverified target, the worker refuses to scan."""
    from app.models import Scan, ScanKind, ScanStatus, Target

    await signed_in(client)
    target = (await client.post("/targets", json={"url": site.url})).json()
    async with app.state.sessionmaker() as db:
        t = await db.get(Target, uuid.UUID(target["id"]))
        scan = Scan(org_id=t.org_id, target_id=t.id, kind=ScanKind.dast, status=ScanStatus.queued)
        db.add(scan)
        await db.commit()
        scan_id = scan.id
    await run_scan(app.state.sessionmaker, scan_id, scanners=[HeadersScanner()])
    async with app.state.sessionmaker() as db:
        s = await db.get(Scan, scan_id)
        assert s.status == ScanStatus.failed


def test_zap_alerts_are_grouped_and_overlaps_dropped():
    from app.scanning.scanners.zap import aggregate

    origin = "https://example.com/"
    alerts = [
        {"pluginId": "10038", "alert": "CSP not set", "risk": "Medium", "url": origin},
        {
            "pluginId": "10098",
            "alert": "Cross-Domain Misconfiguration",
            "risk": "Medium",
            "confidence": "Medium",
            "cweid": "264",
            "url": f"{origin}a",
            "evidence": "Access-Control-Allow-Origin: *",
            "solution": "Restrict CORS",
            "reference": "https://example.org/cors\nnot a url",
        },
        {
            "pluginId": "10098",
            "alert": "Cross-Domain Misconfiguration",
            "risk": "Medium",
            "url": f"{origin}b",
        },
        {
            "pluginId": "10202",
            "alert": "Absence of Anti-CSRF Tokens",
            "risk": "Medium",
            "url": origin,
            "param": "login",
        },
        {
            "pluginId": "10202",
            "alert": "Absence of Anti-CSRF Tokens",
            "risk": "Medium",
            "url": origin,
            "param": "search",
        },
        {
            "pluginId": "10027",
            "alert": "Suspicious comment",
            "risk": "Informational",
            "confidence": "False Positive",
            "url": origin,
        },
        {"pluginId": "10096", "alert": "Timestamp", "risk": "Low", "url": "https://other.example/"},
    ]
    out = {(f.rule_id, f.param): f for f in aggregate(alerts, origin)}
    assert set(out) == {("zap.10098", None), ("zap.10202", "login"), ("zap.10202", "search")}
    cors = out[("zap.10098", None)]
    assert cors.url == origin
    assert cors.cwe == "CWE-264"
    assert cors.references == ["https://example.org/cors"]
    assert f"{origin}a" in cors.evidence and f"{origin}b" in cors.evidence
    assert cors.raw["instances"] == 2


async def test_zap_is_skipped_when_not_configured():
    from app.scanning.scanners.base import ScannerUnavailable
    from app.scanning.scanners.zap import ZapScanner

    with pytest.raises(ScannerUnavailable):
        await ZapScanner().run(ScanContext(url="https://example.com/", hostname="example.com"))
