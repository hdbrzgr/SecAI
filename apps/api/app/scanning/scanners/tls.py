"""Certificate validity and legacy protocol support, checked with the Python ssl module."""

import asyncio
import ssl
from datetime import UTC, datetime
from urllib.parse import urlsplit

from cryptography import x509

from app.core.netguard import resolve
from app.models import Severity
from app.scanning.normalize import RawFinding
from app.scanning.scanners.base import ScanContext

TOOL = "TLS"
REF = "https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Security_Cheat_Sheet.html"


async def _handshake(ip: str, port: int, host: str, ctx: ssl.SSLContext) -> ssl.SSLObject:
    _, writer = await asyncio.wait_for(
        asyncio.open_connection(ip, port, ssl=ctx, server_hostname=host), timeout=10
    )
    try:
        obj = writer.get_extra_info("ssl_object")
        return obj
    finally:
        writer.close()


class TlsScanner:
    name = "tls"
    label = "Checking the TLS certificate and protocols"

    async def run(self, ctx: ScanContext) -> list[RawFinding]:
        parts = urlsplit(ctx.url)
        if parts.scheme != "https":
            return []
        host = parts.hostname or ctx.hostname
        port = parts.port or 443
        ip = str((await resolve(host, port))[0])
        url = ctx.url
        findings: list[RawFinding] = []

        # 1. Does the certificate validate for this hostname?
        try:
            await _handshake(ip, port, host, ssl.create_default_context())
        except ssl.SSLCertVerificationError as exc:
            reason = exc.verify_message or str(exc)
            title, sev = "TLS certificate is not trusted", Severity.high
            if "expired" in reason:
                title = "TLS certificate has expired"
            elif "Hostname mismatch" in reason or "match" in reason:
                title = f"TLS certificate isn't valid for {host}"
            elif "self-signed" in reason or "self signed" in reason:
                title = "TLS certificate is self-signed"
            findings.append(
                RawFinding(
                    tool=TOOL,
                    rule_id="tls.untrusted-certificate",
                    title=title,
                    severity=sev,
                    url=url,
                    cwe="CWE-295",
                    evidence=reason,
                    description="Browsers show a warning, and users who click through can't tell a real site from an attacker's.",
                    recommendation="Install a certificate from a trusted authority that covers this hostname (Let's Encrypt is free) and include the full chain.",
                    references=[REF],
                )
            )

        # 2. Expiry, read without verification so it works even for bad certificates.
        loose = ssl.create_default_context()
        loose.check_hostname = False
        loose.verify_mode = ssl.CERT_NONE
        try:
            obj = await _handshake(ip, port, host, loose)
            der = obj.getpeercert(binary_form=True)
            if der:
                cert = x509.load_der_x509_certificate(der)
                days = (cert.not_valid_after_utc - datetime.now(UTC)).days
                if 0 <= days < 30:
                    findings.append(
                        RawFinding(
                            tool=TOOL,
                            rule_id="tls.expiring-certificate",
                            title=f"TLS certificate expires in {days} day{'s' if days != 1 else ''}",
                            severity=Severity.medium if days < 14 else Severity.low,
                            url=url,
                            cwe="CWE-298",
                            evidence=f"Not valid after {cert.not_valid_after_utc:%Y-%m-%d %H:%M} UTC",
                            recommendation="Renew the certificate now and automate renewal (certbot, your host's auto-renew, or cert-manager).",
                            references=[REF],
                        )
                    )
        except (OSError, TimeoutError, ssl.SSLError):
            pass

        # 3. Legacy protocols (TLS 1.0 / 1.1).
        legacy = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        legacy.check_hostname = False
        legacy.verify_mode = ssl.CERT_NONE
        try:
            legacy.minimum_version = ssl.TLSVersion.TLSv1
            legacy.maximum_version = ssl.TLSVersion.TLSv1_1
            legacy.set_ciphers("DEFAULT:@SECLEVEL=0")
        except (ValueError, ssl.SSLError):
            return findings  # this OpenSSL build can't speak old TLS, so it can't test for it
        try:
            obj = await _handshake(ip, port, host, legacy)
            findings.append(
                RawFinding(
                    tool=TOOL,
                    rule_id="tls.legacy-protocol",
                    title=f"Server accepts {obj.version()}",
                    severity=Severity.medium,
                    url=url,
                    cwe="CWE-327",
                    evidence=f"Handshake succeeded with {obj.version()} ({obj.cipher()[0] if obj.cipher() else ''})",
                    description="TLS 1.0 and 1.1 are deprecated (RFC 8996) and have known weaknesses.",
                    recommendation="Allow only TLS 1.2 and 1.3 in your web server or load balancer config.",
                    references=[REF, "https://www.rfc-editor.org/rfc/rfc8996"],
                )
            )
        except (OSError, TimeoutError, ssl.SSLError):
            pass
        return findings
