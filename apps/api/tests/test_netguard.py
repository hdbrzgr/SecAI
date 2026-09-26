import ipaddress

import pytest

from app.core import netguard
from app.core.config import get_settings
from app.core.netguard import TargetNotAllowed, is_public_address


@pytest.mark.parametrize(
    "addr",
    [
        "127.0.0.1",
        "10.1.2.3",
        "172.16.0.1",
        "192.168.1.1",
        "169.254.169.254",
        "100.64.0.1",
        "0.0.0.0",
        "224.0.0.1",
        "::1",
        "fe80::1",
        "fd00::1",
        "::ffff:127.0.0.1",
        "::ffff:10.0.0.1",
        "64:ff9b::a00:1",
    ],
)
def test_private_and_special_addresses_are_blocked(addr):
    assert not is_public_address(ipaddress.ip_address(addr))


@pytest.mark.parametrize("addr", ["93.184.215.14", "1.1.1.1", "2606:4700:4700::1111"])
def test_public_addresses_are_allowed(addr):
    assert is_public_address(ipaddress.ip_address(addr))


@pytest.fixture
def strict(monkeypatch):
    monkeypatch.setattr(get_settings(), "scan_allow_private", False)


async def test_resolve_rejects_loopback_names(strict):
    with pytest.raises(TargetNotAllowed):
        await netguard.resolve("localhost", 80)
    with pytest.raises(TargetNotAllowed):
        await netguard.resolve("127.0.0.1", 80)


async def test_resolve_rejects_mixed_public_and_private(strict, monkeypatch):
    async def fake_getaddrinfo(host, port, **kw):
        return [(0, 0, 0, "", ("93.184.215.14", port)), (0, 0, 0, "", ("10.0.0.5", port))]

    class Loop:
        getaddrinfo = staticmethod(fake_getaddrinfo)

    monkeypatch.setattr(netguard.asyncio, "get_running_loop", lambda: Loop())
    with pytest.raises(TargetNotAllowed, match=r"10\.0\.0\.5"):
        await netguard.resolve("rebind.example", 443)


async def test_fetch_refuses_redirect_to_internal_address(strict, monkeypatch):
    """A public site that redirects to an internal address must not be followed."""
    calls = []

    async def fake_resolve(host, port):
        calls.append(host)
        if host == "public.example":
            return [ipaddress.ip_address("93.184.215.14")]
        raise TargetNotAllowed(f"{host} resolves to a non-public address")

    import httpx

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "http://internal.example/admin"})

    real_client = httpx.AsyncClient
    monkeypatch.setattr(netguard, "resolve", fake_resolve)
    monkeypatch.setattr(
        netguard.httpx,
        "AsyncClient",
        lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw),
    )
    with pytest.raises(TargetNotAllowed):
        await netguard.fetch("http://public.example/")
    assert calls == ["public.example", "internal.example"]


async def test_fetch_rejects_credentials_and_odd_schemes(strict):
    with pytest.raises(TargetNotAllowed):
        await netguard.fetch("ftp://example.com/")
    with pytest.raises(TargetNotAllowed):
        await netguard.fetch("http://user:pass@example.com/")
