"""OWASP ZAP (Apache-2.0), driven over its API: spider the site, let the passive scanner
analyse every response, collect alerts. Baseline only: no active attacks are sent."""

import asyncio
import time
from collections import defaultdict
from typing import Any

import httpx
from redis.asyncio import Redis

from app.core.config import get_settings
from app.core.netguard import resolve
from app.models import Severity
from app.scanning.normalize import RawFinding
from app.scanning.scanners.base import ScanContext, ScannerUnavailable

_RISK = {
    "High": Severity.high,
    "Medium": Severity.medium,
    "Low": Severity.low,
    "Informational": Severity.info,
}

# Passive rules the Headers scanner already checks precisely (one finding instead of two).
COVERED_BY_HEADERS = {
    "10010",  # cookie without HttpOnly
    "10011",  # cookie without Secure
    "10020",  # anti-clickjacking header
    "10021",  # X-Content-Type-Options
    "10035",  # Strict-Transport-Security
    "10036",  # Server header version
    "10037",  # X-Powered-By
    "10038",  # CSP not set
    "10054",  # cookie without SameSite
}
# Rules where each parameter is a separate problem (per cookie, per form field).
PER_PARAM = {"10202", "10031", "40012", "40014", "40018", "90022"}
MAX_URLS_IN_EVIDENCE = 5


def aggregate(alerts: list[dict[str, Any]], origin: str) -> list[RawFinding]:
    """One finding per ZAP rule (per parameter where that matters), listing affected URLs."""
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for a in alerts:
        plugin = str(a.get("pluginId", ""))
        if plugin in COVERED_BY_HEADERS or a.get("confidence") == "False Positive":
            continue
        if not str(a.get("url", "")).startswith(origin.rstrip("/")):
            continue
        param = a.get("param", "") if plugin in PER_PARAM else ""
        groups[(plugin, param)].append(a)

    out = []
    for (plugin, param), items in groups.items():
        first = items[0]
        urls = list(dict.fromkeys(i["url"] for i in items))
        lines = urls[:MAX_URLS_IN_EVIDENCE]
        if len(urls) > MAX_URLS_IN_EVIDENCE:
            lines.append(f"… and {len(urls) - MAX_URLS_IN_EVIDENCE} more URLs")
        if first.get("evidence"):
            lines.append(f"Evidence: {str(first['evidence'])[:300]}")
        cwe = str(first.get("cweid", ""))
        refs = [
            r.strip()
            for r in str(first.get("reference", "")).splitlines()
            if r.strip().startswith("http")
        ]
        out.append(
            RawFinding(
                tool="ZAP",
                rule_id=f"zap.{plugin}",
                title=first.get("alert") or first.get("name") or f"ZAP rule {plugin}",
                severity=_RISK.get(first.get("risk", ""), Severity.info),
                url=origin if len(urls) > 1 else urls[0],
                param=param or None,
                cwe=f"CWE-{cwe}" if cwe.isdigit() and int(cwe) > 0 else None,
                evidence="\n".join(lines),
                description=(first.get("description") or "").strip() or None,
                recommendation=(first.get("solution") or "").strip() or None,
                references=refs[:5],
                raw={
                    "pluginId": plugin,
                    "confidence": first.get("confidence"),
                    "instances": len(items),
                },
            )
        )
    return out


class ZapScanner:
    name = "zap"
    label = "Crawling the site with OWASP ZAP"

    async def run(self, ctx: ScanContext) -> list[RawFinding]:
        settings = get_settings()
        if not settings.zap_url or not settings.zap_api_key:
            raise ScannerUnavailable("OWASP ZAP isn't configured on this instance")
        await resolve(ctx.hostname, 443)  # re-check right before handing the target to ZAP

        redis = Redis.from_url(settings.redis_url)
        # One ZAP session at a time: each scan starts ZAP from a clean session.
        lock = redis.lock(
            "secai:zap",
            timeout=settings.scan_tool_timeout_seconds + 60,
            blocking_timeout=settings.scan_tool_timeout_seconds,
        )
        try:
            if not await lock.acquire():
                raise ScannerUnavailable("OWASP ZAP was busy with other scans for too long")
            try:
                return await self._scan(settings, ctx.url)
            finally:
                await lock.release()
        finally:
            await redis.aclose()

    async def _scan(self, settings, url: str) -> list[RawFinding]:
        async with httpx.AsyncClient(
            base_url=settings.zap_url,
            headers={"X-ZAP-API-Key": settings.zap_api_key},
            timeout=30,
            trust_env=False,
        ) as zap:

            async def call(path: str, **params: Any) -> dict[str, Any]:
                r = await zap.get(f"/JSON/{path}/", params=params)
                r.raise_for_status()
                return r.json()

            try:
                await call("core/action/newSession", overwrite="true")
            except httpx.ConnectError as exc:
                raise ScannerUnavailable("OWASP ZAP isn't reachable") from exc
            await call("spider/action/setOptionMaxDuration", Integer=settings.zap_spider_minutes)
            await call("spider/action/setOptionMaxDepth", Integer=5)
            await call("spider/action/setOptionThreadCount", Integer=2)
            await call("spider/action/setOptionMaxChildren", Integer=50)
            scan_id = (await call("spider/action/scan", url=url, subtreeOnly="true"))["scan"]

            deadline = time.monotonic() + settings.zap_spider_minutes * 60 + 60
            while time.monotonic() < deadline:
                if int((await call("spider/view/status", scanId=scan_id))["status"]) >= 100:
                    break
                await asyncio.sleep(2)
            else:
                await call("spider/action/stop", scanId=scan_id)

            # Let the passive scanner finish reading every recorded response.
            deadline = time.monotonic() + 180
            while time.monotonic() < deadline:
                if int((await call("pscan/view/recordsToScan"))["recordsToScan"]) == 0:
                    break
                await asyncio.sleep(2)

            alerts: list[dict[str, Any]] = []
            start = 0
            while True:
                page = (await call("alert/view/alerts", baseurl=url, start=start, count=500))[
                    "alerts"
                ]
                alerts.extend(page)
                if len(page) < 500:
                    break
                start += 500
            return aggregate(alerts, url)
