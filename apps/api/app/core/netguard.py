"""Outbound network access for scans and ownership checks.

Every connection SecAI makes to a user-supplied host goes through this module:
the hostname is resolved once, every address must be public, and the connection is
pinned to a validated address (with the original Host header and TLS SNI) so DNS
rebinding can't swap in an internal address between the check and the request.
Redirects are followed manually and re-checked the same way.
"""

import asyncio
import ipaddress
import socket
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlsplit, urlunsplit

import httpx

from app.core.config import get_settings

USER_AGENT = "SecAI-Scanner/0.1 (+https://github.com/hdbrzgr/SecAI)"

# Ranges that are never scan targets even if the stdlib calls them global.
_BLOCKED = [
    ipaddress.ip_network(n)
    for n in (
        "0.0.0.0/8",
        "100.64.0.0/10",
        "169.254.0.0/16",
        "192.0.0.0/24",
        "198.18.0.0/15",
        "224.0.0.0/4",
        "240.0.0.0/4",
        "64:ff9b::/96",
        "64:ff9b:1::/48",
        "2002::/16",
        "fe80::/10",
        "fc00::/7",
        "ff00::/8",
    )
]

IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address


class TargetNotAllowed(Exception):
    """The destination resolves to an address SecAI must not connect to."""


def is_public_address(ip: IPAddress) -> bool:
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        ip = ip.ipv4_mapped
    if not ip.is_global or ip.is_multicast or ip.is_reserved or ip.is_loopback:
        return False
    return not any(ip in net for net in _BLOCKED)


async def resolve(host: str, port: int) -> list[IPAddress]:
    """Resolve `host` and return its addresses; raise if any of them isn't public."""
    try:
        literal = ipaddress.ip_address(host.strip("[]"))
        addresses: list[IPAddress] = [literal]
    except ValueError:
        try:
            infos = await asyncio.get_running_loop().getaddrinfo(
                host, port, type=socket.SOCK_STREAM
            )
        except socket.gaierror as exc:
            raise TargetNotAllowed(f"{host} could not be resolved") from exc
        addresses = list(dict.fromkeys(ipaddress.ip_address(i[4][0]) for i in infos))
    if not addresses:
        raise TargetNotAllowed(f"{host} has no addresses")
    if not get_settings().scan_allow_private:
        # Every address must be public: a mix could be exploited by picking the bad one later.
        bad = [str(a) for a in addresses if not is_public_address(a)]
        if bad:
            raise TargetNotAllowed(f"{host} resolves to a non-public address ({', '.join(bad)})")
    return addresses


def _default_port(scheme: str) -> int:
    return 443 if scheme == "https" else 80


@dataclass
class FetchResult:
    url: str
    status: int
    headers: httpx.Headers
    body: bytes
    redirects: list[str] = field(default_factory=list)
    truncated: bool = False

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", errors="replace")


async def fetch(
    url: str,
    *,
    method: str = "GET",
    follow_redirects: bool = True,
    max_redirects: int = 5,
    max_bytes: int = 1_000_000,
    timeout: float = 10.0,  # noqa: ASYNC109 - httpx's per-request timeout
    headers: dict[str, str] | None = None,
) -> FetchResult:
    """Fetch a URL through the guard. TLS certificates are not verified here; the TLS
    scanner reports certificate problems separately."""
    redirects: list[str] = []
    current = url
    # verify=False: scanning must still work on sites with broken certificates.
    async with httpx.AsyncClient(verify=False, timeout=timeout, trust_env=False) as client:  # noqa: S501
        for _ in range(max_redirects + 1):
            parts = urlsplit(current)
            if parts.scheme not in ("http", "https") or not parts.hostname:
                raise TargetNotAllowed(f"Unsupported URL: {current}")
            if parts.username or parts.password:
                raise TargetNotAllowed("URLs with credentials are not allowed")
            host = parts.hostname
            port = parts.port or _default_port(parts.scheme)
            ip = (await resolve(host, port))[0]
            ip_host = f"[{ip}]" if ip.version == 6 else str(ip)
            pinned = urlunsplit(
                (parts.scheme, f"{ip_host}:{port}", parts.path or "/", parts.query, "")
            )
            host_header = host if parts.port is None else f"{host}:{parts.port}"
            request = client.build_request(
                method,
                pinned,
                headers={"Host": host_header, "User-Agent": USER_AGENT, **(headers or {})},
                extensions={"sni_hostname": host},
            )
            response = await client.send(request, stream=True)
            try:
                body = bytearray()
                truncated = False
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > max_bytes:
                        truncated = True
                        del body[max_bytes:]
                        break
            finally:
                await response.aclose()
            location = response.headers.get("location")
            if follow_redirects and response.is_redirect and location:
                redirects.append(current)
                current = urljoin(current, location)
                continue
            return FetchResult(
                url=current,
                status=response.status_code,
                headers=response.headers,
                body=bytes(body),
                redirects=redirects,
                truncated=truncated,
            )
    raise TargetNotAllowed(f"Too many redirects from {url}")
