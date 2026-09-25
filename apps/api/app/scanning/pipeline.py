"""Runs every scanner for one scan, stores normalized findings and the summary."""

import logging
import time
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.ai.analysis import analyze
from app.core.netguard import TargetNotAllowed
from app.models import Finding, Scan, ScanStatus, Target
from app.scanning.normalize import RawFinding, dedupe, grade
from app.scanning.scanners.base import ScanContext, Scanner, ScannerUnavailable
from app.scanning.scanners.exposure import ExposureScanner
from app.scanning.scanners.headers import HeadersScanner
from app.scanning.scanners.nuclei import NucleiScanner
from app.scanning.scanners.tls import TlsScanner
from app.scanning.scanners.zap import ZapScanner

log = logging.getLogger(__name__)


def default_scanners() -> list[Scanner]:
    return [HeadersScanner(), TlsScanner(), ExposureScanner(), NucleiScanner(), ZapScanner()]


async def run_scan(
    sessionmaker: async_sessionmaker[AsyncSession],
    scan_id: uuid.UUID,
    scanners: list[Scanner] | None = None,
) -> None:
    scanners = scanners if scanners is not None else default_scanners()
    async with sessionmaker() as db:
        scan = await db.get(Scan, scan_id)
        if scan is None or scan.status != ScanStatus.queued:
            return
        target = await db.get(Target, scan.target_id) if scan.target_id else None
        if target is None or target.verified_at is None:
            scan.status = ScanStatus.failed
            scan.error = "The website is no longer verified"
            scan.finished_at = datetime.now(UTC)
            await db.commit()
            return
        scan.status = ScanStatus.running
        scan.started_at = datetime.now(UTC)
        scan.progress = 1
        await db.commit()

        ctx = ScanContext(url=target.url, hostname=target.hostname)
        collected: list[RawFinding] = []
        tools = []
        started = time.monotonic()
        for i, scanner in enumerate(scanners):
            scan.current_step = scanner.label
            scan.progress = max(scan.progress, int(100 * i / len(scanners)))
            await db.commit()
            t0 = time.monotonic()
            entry = {"name": scanner.name}
            try:
                found = await scanner.run(ctx)
                collected.extend(found)
                entry.update(status="ok", findings=len(found))
            except ScannerUnavailable as exc:
                entry.update(status="skipped", reason=str(exc))
            except TargetNotAllowed as exc:
                entry.update(status="blocked", reason=str(exc))
            except Exception as exc:
                log.exception("scanner %s failed for scan %s", scanner.name, scan_id)
                entry.update(status="failed", reason=type(exc).__name__)
            entry["seconds"] = round(time.monotonic() - t0, 1)
            tools.append(entry)

        findings = dedupe(collected)
        ai = None
        if any(t["status"] == "ok" for t in tools):
            scan.current_step = "Reviewing findings with AI"
            scan.progress = max(scan.progress, 90)
            await db.commit()
            t0 = time.monotonic()
            try:
                ai = await analyze(ctx.url, ctx.observations, findings)
            except Exception:
                log.exception("AI analysis failed for scan %s", scan_id)
                ai = None
            tools.append(
                {
                    "name": "ai",
                    "status": {"ok": "ok", "skipped": "skipped"}.get(ai.status, "failed")
                    if ai
                    else "failed",
                    "reason": ai.reason if ai else "Unexpected error",
                    "seconds": round(time.monotonic() - t0, 1),
                }
            )
        for f in findings:
            db.add(
                Finding(
                    scan_id=scan.id,
                    fingerprint=f.fingerprint,
                    tool=f.tool,
                    rule_id=f.rule_id,
                    title=f.title[:500],
                    severity=f.severity,
                    cwe=f.cwe,
                    location=f.location,
                    evidence=f.evidence,
                    description=f.description,
                    recommendation=f.recommendation,
                    references=f.references,
                    raw=f.raw,
                    ai=ai.by_fingerprint.get(f.fingerprint) if ai else None,
                )
            )
        score, letter, counts = grade(findings)
        ran = [t for t in tools if t["status"] == "ok" and t["name"] != "ai"]
        scan.summary = {
            "score": score,
            "grade": letter,
            "counts": counts,
            "tools": tools,
            "seconds": round(time.monotonic() - started, 1),
            "ai": ai.summary() if ai else None,
        }
        scan.progress = 100
        scan.finished_at = datetime.now(UTC)
        if ran:
            scan.status = ScanStatus.succeeded
            scan.current_step = None
        else:
            scan.status = ScanStatus.failed
            scan.error = "No scanner could reach the website"
            scan.current_step = None
        await db.commit()
