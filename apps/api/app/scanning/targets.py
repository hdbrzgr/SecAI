"""Normalizing target URLs and proving ownership."""

import ipaddress
import re
import secrets
from html.parser import HTMLParser
from urllib.parse import urlsplit

import dns.asyncresolver
import dns.exception

from app.core.config import get_settings
from app.core.netguard import TargetNotAllowed, fetch
from app.models import VerificationMethod

_LABEL = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)$")
WELL_KNOWN_PATH = "/.well-known/secai-verify.txt"


class InvalidTarget(ValueError):
    pass


def normalize_url(raw: str) -> tuple[str, str]:
    """Return (origin URL, hostname) for what a user typed. Only the origin is scanned."""
    raw = raw.strip()
    if not raw:
        raise InvalidTarget("Enter a website address")
    if "://" not in raw:
        raw = f"https://{raw}"
    parts = urlsplit(raw)
    if parts.scheme not in ("http", "https"):
        raise InvalidTarget("Use an http:// or https:// address")
    if parts.username or parts.password:
        raise InvalidTarget("Remove the username and password from the address")
    host = (parts.hostname or "").rstrip(".").lower()
    try:
        port = parts.port
    except ValueError as exc:
        raise InvalidTarget("The port number isn't valid") from exc
    if not host:
        raise InvalidTarget("Enter a website address, like https://example.com")

    allow_private = get_settings().scan_allow_private
    try:
        ipaddress.ip_address(host)
        is_ip = True
    except ValueError:
        is_ip = False
    if is_ip and not allow_private:
        raise InvalidTarget("Use a domain name, not an IP address, so ownership can be verified")
    if not is_ip:
        try:
            host = host.encode("idna").decode("ascii")
        except UnicodeError as exc:
            raise InvalidTarget("The domain name isn't valid") from exc
        labels = host.split(".")
        if not all(_LABEL.match(label) for label in labels):
            raise InvalidTarget("The domain name isn't valid")
        if len(labels) < 2 and not allow_private:
            raise InvalidTarget("Use a full domain name, like example.com")

    netloc = f"[{host}]" if ":" in host else host
    if port is not None:
        netloc = f"{netloc}:{port}"
    return f"{parts.scheme}://{netloc}/", host


def new_verification_token() -> str:
    return secrets.token_hex(16)


def txt_value(token: str) -> str:
    return f"secai-verify={token}"


class _MetaFinder(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.values: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "meta":
            return
        a = {k.lower(): (v or "") for k, v in attrs}
        if a.get("name", "").lower() == "secai-verify":
            self.values.append(a.get("content", "").strip())


async def _check_dns(hostname: str, token: str) -> bool:
    resolver = dns.asyncresolver.Resolver()
    resolver.lifetime = 8.0
    try:
        answer = await resolver.resolve(hostname, "TXT")
    except (dns.exception.DNSException, OSError):
        return False
    expected = txt_value(token)
    for record in answer:
        text = b"".join(record.strings).decode("utf-8", errors="replace").strip()
        if secrets.compare_digest(text, expected):
            return True
    return False


async def check_ownership(url: str, hostname: str, method: VerificationMethod, token: str) -> bool:
    """True when the proof for `method` is in place. Network errors count as not found."""
    try:
        if method == VerificationMethod.dns_txt:
            return await _check_dns(hostname, token)
        if method == VerificationMethod.well_known_file:
            result = await fetch(url.rstrip("/") + WELL_KNOWN_PATH, max_bytes=4096)
            return result.status == 200 and secrets.compare_digest(result.text.strip(), token)
        result = await fetch(url, max_bytes=512_000)
        finder = _MetaFinder()
        finder.feed(result.text)
        return result.status == 200 and any(secrets.compare_digest(v, token) for v in finder.values)
    except (TargetNotAllowed, OSError, ValueError):
        return False
    except Exception as exc:  # httpx errors: timeouts, TLS failures, bad responses
        if exc.__class__.__module__.startswith(("httpx", "httpcore")):
            return False
        raise
