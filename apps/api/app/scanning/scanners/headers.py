"""HTTPS redirect, security headers, cookie flags and information disclosure."""

import re
from http.cookies import SimpleCookie
from urllib.parse import urlsplit, urlunsplit

from app.core.netguard import fetch
from app.models import Severity
from app.scanning.normalize import RawFinding
from app.scanning.scanners.base import ScanContext

TOOL = "Headers"
MDN = "https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/"
OWASP_HEADERS = "https://owasp.org/www-project-secure-headers/"


def _f(rule: str, title: str, sev: Severity, url: str, **kw) -> RawFinding:
    return RawFinding(
        tool=TOOL, rule_id=f"headers.{rule}", title=title, severity=sev, url=url, **kw
    )


class HeadersScanner:
    name = "headers"
    label = "Checking security headers and cookies"

    async def run(self, ctx: ScanContext) -> list[RawFinding]:
        findings: list[RawFinding] = []
        page = await fetch(ctx.url, max_bytes=256_000)
        final = page.url
        h = page.headers
        is_https = final.startswith("https://")

        # HTTP should redirect to HTTPS.
        http_url = urlunsplit(("http", urlsplit(ctx.url).netloc, "/", "", ""))
        try:
            plain = await fetch(http_url, follow_redirects=False, max_bytes=16_000, timeout=8)
            location = plain.headers.get("location", "")
            if plain.status < 300 or plain.status >= 400 or not location.startswith("https://"):
                findings.append(
                    _f(
                        "no-https-redirect",
                        "HTTP doesn't redirect to HTTPS",
                        Severity.medium,
                        http_url,
                        cwe="CWE-319",
                        evidence=f"GET {http_url} → {plain.status}"
                        + (f" Location: {location}" if location else ""),
                        description="Visitors who type the address without https:// stay on an unencrypted connection, where traffic can be read or changed.",
                        recommendation="Redirect every http:// request to the same URL on https:// with a 301, and add Strict-Transport-Security.",
                        references=[
                            "https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Security_Cheat_Sheet.html"
                        ],
                    )
                )
        except Exception:
            pass

        if not is_https:
            findings.append(
                _f(
                    "no-https",
                    "Site is served without HTTPS",
                    Severity.high,
                    final,
                    cwe="CWE-319",
                    evidence=f"Final URL: {final}",
                    description="Pages, logins and cookies travel unencrypted.",
                    recommendation="Serve the site over HTTPS (free certificates are available from Let's Encrypt) and redirect HTTP to HTTPS.",
                    references=["https://letsencrypt.org/getting-started/"],
                )
            )
        elif "strict-transport-security" not in h:
            findings.append(
                _f(
                    "missing-hsts",
                    "Missing Strict-Transport-Security header",
                    Severity.medium,
                    final,
                    cwe="CWE-319",
                    description="Without HSTS, a browser can be tricked into loading the site over plain HTTP on the first request.",
                    recommendation="Add `Strict-Transport-Security: max-age=31536000; includeSubDomains` to every HTTPS response.",
                    references=[MDN + "Strict-Transport-Security"],
                )
            )
        else:
            m = re.search(r"max-age=(\d+)", h["strict-transport-security"])
            if not m or int(m.group(1)) < 15552000:
                findings.append(
                    _f(
                        "weak-hsts",
                        "Strict-Transport-Security max-age is shorter than 6 months",
                        Severity.low,
                        final,
                        cwe="CWE-319",
                        evidence=f"Strict-Transport-Security: {h['strict-transport-security']}",
                        recommendation="Set `max-age` to at least 15552000 (180 days); 31536000 is common.",
                        references=[MDN + "Strict-Transport-Security"],
                    )
                )

        csp = h.get("content-security-policy")
        if not csp:
            findings.append(
                _f(
                    "missing-csp",
                    "Missing Content-Security-Policy header",
                    Severity.medium,
                    final,
                    cwe="CWE-693",
                    description="A Content-Security-Policy limits where scripts can load from and is the main defense-in-depth against cross-site scripting (XSS).",
                    recommendation="Start with `Content-Security-Policy: default-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'`, then allow the sources your pages need.",
                    references=[
                        MDN + "Content-Security-Policy",
                        "https://csp-evaluator.withgoogle.com/",
                    ],
                )
            )
        elif (
            re.search(r"script-src[^;]*'unsafe-inline'", csp)
            and "nonce-" not in csp
            and "strict-dynamic" not in csp
        ):
            findings.append(
                _f(
                    "csp-unsafe-inline",
                    "Content-Security-Policy allows inline scripts",
                    Severity.low,
                    final,
                    cwe="CWE-693",
                    evidence=f"Content-Security-Policy: {csp[:300]}",
                    description="'unsafe-inline' in script-src lets injected <script> tags run, which removes most of the XSS protection CSP gives.",
                    recommendation="Replace 'unsafe-inline' with nonces or hashes for the inline scripts you need.",
                    references=[MDN + "Content-Security-Policy/script-src"],
                )
            )

        frame_protected = "x-frame-options" in h or (csp and "frame-ancestors" in csp)
        if not frame_protected:
            findings.append(
                _f(
                    "clickjacking",
                    "Pages can be framed by other sites (clickjacking)",
                    Severity.medium,
                    final,
                    cwe="CWE-1021",
                    description="Another site can load your pages in an invisible frame and trick users into clicking buttons on them.",
                    recommendation="Add `Content-Security-Policy: frame-ancestors 'self'` (or 'none'), or `X-Frame-Options: DENY`.",
                    references=[MDN + "X-Frame-Options"],
                )
            )

        if h.get("x-content-type-options", "").lower() != "nosniff":
            findings.append(
                _f(
                    "missing-nosniff",
                    "Missing X-Content-Type-Options: nosniff",
                    Severity.low,
                    final,
                    cwe="CWE-693",
                    description="Browsers may guess content types and run an uploaded file as a script.",
                    recommendation="Add `X-Content-Type-Options: nosniff` to every response.",
                    references=[MDN + "X-Content-Type-Options"],
                )
            )

        if "referrer-policy" not in h:
            findings.append(
                _f(
                    "missing-referrer-policy",
                    "Missing Referrer-Policy header",
                    Severity.info,
                    final,
                    description="Full URLs, which can include tokens or IDs, may be sent to other sites in the Referer header.",
                    recommendation="Add `Referrer-Policy: strict-origin-when-cross-origin`.",
                    references=[MDN + "Referrer-Policy"],
                )
            )

        for header in ("server", "x-powered-by", "x-aspnet-version", "x-aspnetmvc-version"):
            value = h.get(header, "")
            if re.search(r"\d+\.\d+", value):
                findings.append(
                    _f(
                        f"version-disclosure-{header}",
                        f"{header.title()} header reveals a software version",
                        Severity.low,
                        final,
                        cwe="CWE-200",
                        evidence=f"{header.title()}: {value[:200]}",
                        description="Exact versions tell attackers which known vulnerabilities to try.",
                        recommendation=f"Remove the {header.title()} header or strip the version number in your web server or framework config.",
                        references=[OWASP_HEADERS],
                    )
                )

        acao = h.get("access-control-allow-origin", "")
        if acao == "*" and h.get("access-control-allow-credentials", "").lower() == "true":
            findings.append(
                _f(
                    "cors-wildcard-credentials",
                    "CORS allows any origin with credentials",
                    Severity.high,
                    final,
                    cwe="CWE-942",
                    evidence="Access-Control-Allow-Origin: *, Access-Control-Allow-Credentials: true",
                    recommendation="Only reflect specific trusted origins, and send Allow-Credentials only for them.",
                    references=[MDN + "Access-Control-Allow-Origin"],
                )
            )

        for raw_cookie in h.get_list("set-cookie"):
            findings.extend(self._cookie(raw_cookie, final, is_https))
        return findings

    def _cookie(self, raw_cookie: str, url: str, is_https: bool) -> list[RawFinding]:
        jar = SimpleCookie()
        try:
            jar.load(raw_cookie)
        except Exception:
            return []
        lowered = raw_cookie.lower()
        out = []
        for name in jar:
            missing = []
            if is_https and "secure" not in [p.strip() for p in lowered.split(";")]:
                missing.append("Secure")
            if "httponly" not in lowered:
                missing.append("HttpOnly")
            if "samesite" not in lowered:
                missing.append("SameSite")
            if missing:
                sev = (
                    Severity.medium
                    if "Secure" in missing and _looks_like_session(name)
                    else Severity.low
                )
                out.append(
                    RawFinding(
                        tool=TOOL,
                        rule_id=f"headers.cookie-flags.{name}",
                        title=f"Cookie {name} is missing {', '.join(missing)}",
                        severity=sev,
                        url=url,
                        param=name,
                        cwe="CWE-614" if "Secure" in missing else "CWE-1004",
                        evidence=f"Set-Cookie: {_redact_cookie(raw_cookie)[:200]}",
                        description="Secure keeps the cookie off plain HTTP, HttpOnly hides it from JavaScript (limiting XSS damage), and SameSite limits cross-site request forgery.",
                        recommendation=f"Set the cookie with `Secure; HttpOnly; SameSite=Lax` unless JavaScript genuinely needs to read {name}.",
                        references=[MDN + "Set-Cookie"],
                    )
                )
        return out


def _redact_cookie(raw_cookie: str) -> str:
    """Keep the name and attributes; never store the site's cookie value."""
    first, _, rest = raw_cookie.partition(";")
    name = first.split("=", 1)[0].strip()
    return f"{name}=[redacted]" + (f";{rest}" if rest else "")


def _looks_like_session(name: str) -> bool:
    return bool(re.search(r"sess|auth|token|sid|login|jwt", name, re.I))
