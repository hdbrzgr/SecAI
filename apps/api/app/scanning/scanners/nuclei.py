"""ProjectDiscovery Nuclei (MIT), run as a subprocess with a conservative template set."""

import asyncio
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.core.netguard import resolve
from app.models import Severity
from app.scanning.normalize import RawFinding
from app.scanning.scanners.base import ScanContext, ScannerUnavailable

# Templates that can harm a site or hammer a login are never run.
EXCLUDED_TAGS = "dos,fuzz,bruteforce,intrusive,brute-force"
_SEVERITY = {
    "critical": Severity.critical,
    "high": Severity.high,
    "medium": Severity.medium,
    "low": Severity.low,
    "info": Severity.info,
    "unknown": Severity.info,
}


def parse_line(line: str) -> RawFinding | None:
    try:
        item: dict[str, Any] = json.loads(line)
    except json.JSONDecodeError:
        return None
    info = item.get("info") or {}
    classification = info.get("classification") or {}
    cwe_ids = classification.get("cwe-id") or []
    refs = info.get("reference") or []
    if isinstance(refs, str):
        refs = [refs]
    extracted = item.get("extracted-results") or []
    evidence_parts = []
    if item.get("matcher-name"):
        evidence_parts.append(f"Matched: {item['matcher-name']}")
    if extracted:
        evidence_parts.append("Extracted: " + ", ".join(str(e) for e in extracted[:5]))
    url = item.get("matched-at") or item.get("url") or item.get("host") or ""
    return RawFinding(
        tool="Nuclei",
        rule_id=f"nuclei.{item.get('template-id', 'unknown')}",
        title=info.get("name") or item.get("template-id", "Nuclei finding"),
        severity=_SEVERITY.get(str(info.get("severity", "info")).lower(), Severity.info),
        url=url,
        cwe=str(cwe_ids[0]).upper() if cwe_ids else None,
        evidence="\n".join(evidence_parts) or None,
        description=(info.get("description") or "").strip() or None,
        recommendation=(info.get("remediation") or "").strip() or None,
        references=[str(r) for r in refs[:5]],
        raw={k: item.get(k) for k in ("template-id", "matcher-name", "type", "matched-at")},
    )


class NucleiScanner:
    name = "nuclei"
    label = "Running Nuclei templates"

    async def run(self, ctx: ScanContext) -> list[RawFinding]:
        settings = get_settings()
        binary = shutil.which(settings.nuclei_path)
        if binary is None:
            raise ScannerUnavailable("Nuclei isn't installed on this worker")
        # Re-check right before handing the target to an external tool.
        await resolve(ctx.hostname, 443)
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "results.jsonl"
            args = [
                binary,
                "-u",
                ctx.url,
                "-jsonl",
                "-o",
                str(out),
                "-silent",
                "-no-color",
                "-disable-update-check",
                "-no-interactsh",
                "-etags",
                EXCLUDED_TAGS,
                "-severity",
                "info,low,medium,high,critical",
                "-rate-limit",
                "50",
                "-concurrency",
                "10",
                "-timeout",
                "10",
                "-retries",
                "1",
                "-H",
                "User-Agent: SecAI-Scanner/0.1 (+https://github.com/hdbrzgr/SecAI)",
            ]
            if settings.nuclei_templates:
                args += ["-t", settings.nuclei_templates]
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                _, stderr = await asyncio.wait_for(
                    proc.communicate(), settings.scan_tool_timeout_seconds
                )
            except TimeoutError:
                proc.kill()
                await proc.wait()
                raise
            if proc.returncode not in (0, None) and not out.exists():
                raise RuntimeError(
                    f"Nuclei exited with {proc.returncode}: {stderr.decode()[-300:]}"
                )
            lines = out.read_text().splitlines() if out.exists() else []
        return [f for f in (parse_line(line) for line in lines) if f]
