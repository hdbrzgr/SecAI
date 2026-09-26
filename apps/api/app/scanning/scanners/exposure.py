"""Files that should never be public: VCS metadata, env files, backups, debug pages."""

import re
from collections.abc import Callable
from dataclasses import dataclass

from app.core.netguard import fetch
from app.models import Severity
from app.scanning.normalize import RawFinding
from app.scanning.scanners.base import ScanContext


@dataclass
class Probe:
    path: str
    title: str
    severity: Severity
    cwe: str
    # Content check that confirms the real file, not a catch-all 200 page.
    matches: Callable[[str], bool]
    recommendation: str


PROBES = [
    Probe(
        "/.git/HEAD",
        "Git repository metadata is public (/.git/)",
        Severity.high,
        "CWE-538",
        lambda t: t.startswith("ref: refs/") or bool(re.fullmatch(r"[0-9a-f]{40}\s*", t)),
        "Block access to /.git/ in your web server and don't deploy the .git folder. Anyone can download your source code and history, including secrets ever committed.",
    ),
    Probe(
        "/.env",
        "Environment file is public (/.env)",
        Severity.critical,
        "CWE-538",
        lambda t: bool(re.search(r"^[A-Z][A-Z0-9_]{2,}=", t, re.M)) and "<html" not in t.lower(),
        "Remove .env from the web root and block dotfiles. Rotate every secret in the file: it must be treated as leaked.",
    ),
    Probe(
        "/.svn/entries",
        "Subversion metadata is public (/.svn/)",
        Severity.high,
        "CWE-538",
        lambda t: t.strip().split("\n", 1)[0].strip().isdigit() or "svn:" in t,
        "Block access to /.svn/ and don't deploy VCS folders.",
    ),
    Probe(
        "/.DS_Store",
        "macOS .DS_Store file is public",
        Severity.low,
        "CWE-538",
        lambda t: t.startswith("\x00\x00\x00\x01Bud1"),
        "Delete .DS_Store files from the deployment and block dotfiles; they list the folder's file names.",
    ),
    Probe(
        "/phpinfo.php",
        "phpinfo() page is public",
        Severity.medium,
        "CWE-200",
        lambda t: "phpinfo()" in t or ("PHP Version" in t and "<table" in t),
        "Delete phpinfo.php. It reveals versions, paths and environment variables.",
    ),
    Probe(
        "/server-status",
        "Apache server-status page is public",
        Severity.medium,
        "CWE-200",
        lambda t: "Apache Server Status" in t,
        "Restrict /server-status to localhost or remove mod_status.",
    ),
    Probe(
        "/wp-config.php.bak",
        "WordPress config backup is public",
        Severity.critical,
        "CWE-530",
        lambda t: "DB_PASSWORD" in t,
        "Delete the backup file and rotate the database password and WordPress salts.",
    ),
    Probe(
        "/.aws/credentials",
        "AWS credentials file is public",
        Severity.critical,
        "CWE-538",
        lambda t: "aws_access_key_id" in t.lower(),
        "Remove the file, block dotfiles, and deactivate the exposed AWS keys immediately.",
    ),
]


class ExposureScanner:
    name = "exposure"
    label = "Looking for exposed files"

    async def run(self, ctx: ScanContext) -> list[RawFinding]:
        out = []
        base = ctx.url.rstrip("/")
        for probe in PROBES:
            url = base + probe.path
            try:
                res = await fetch(url, follow_redirects=False, max_bytes=16_000, timeout=8)
            except Exception:
                continue
            if res.status != 200:
                continue
            text = res.body.decode("latin-1")
            if not probe.matches(text):
                continue
            preview = text[:160].replace("\x00", "")
            # Never store the contents of secrets files; show only that they exist.
            evidence = (
                f"GET {url} → 200"
                if probe.severity == Severity.critical
                else f"GET {url} → 200\n{preview}"
            )
            out.append(
                RawFinding(
                    tool="Exposure",
                    rule_id=f"exposure{probe.path}",
                    title=probe.title,
                    severity=probe.severity,
                    url=url,
                    cwe=probe.cwe,
                    evidence=evidence,
                    description="This file is served to anyone who asks for it.",
                    recommendation=probe.recommendation,
                    references=[
                        "https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/04-Review_Old_Backup_and_Unreferenced_Files_for_Sensitive_Information"
                    ],
                )
            )
        return out
