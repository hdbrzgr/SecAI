"""The one shape every scanner's output is converted into, plus dedupe and grading."""

import hashlib
from dataclasses import dataclass, field
from typing import Any

from app.models import Severity

SEVERITY_ORDER = {
    Severity.critical: 0,
    Severity.high: 1,
    Severity.medium: 2,
    Severity.low: 3,
    Severity.info: 4,
}
_PENALTY = {
    Severity.critical: 40,
    Severity.high: 15,
    Severity.medium: 6,
    Severity.low: 2,
    Severity.info: 0,
}


@dataclass
class RawFinding:
    tool: str
    rule_id: str
    title: str
    severity: Severity
    url: str
    cwe: str | None = None
    param: str | None = None
    evidence: str | None = None
    description: str | None = None
    recommendation: str | None = None
    references: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def location(self) -> dict[str, Any]:
        loc: dict[str, Any] = {"url": self.url}
        if self.param:
            loc["param"] = self.param
        return loc

    @property
    def fingerprint(self) -> str:
        # Same rule at the same place is the same finding, across tools and across scans.
        key = "|".join(
            [self.rule_id.lower(), self.url.rstrip("/").lower(), (self.param or "").lower()]
        )
        return hashlib.sha256(key.encode()).hexdigest()


def dedupe(findings: list[RawFinding]) -> list[RawFinding]:
    best: dict[str, RawFinding] = {}
    for f in findings:
        current = best.get(f.fingerprint)
        if current is None or SEVERITY_ORDER[f.severity] < SEVERITY_ORDER[current.severity]:
            best[f.fingerprint] = f
    return sorted(best.values(), key=lambda f: (SEVERITY_ORDER[f.severity], f.title))


def grade(findings: list[RawFinding]) -> tuple[int, str, dict[str, int]]:
    counts = {s.value: 0 for s in Severity}
    for f in findings:
        counts[f.severity.value] += 1
    score = 100
    for sev, n in counts.items():
        score -= _PENALTY[Severity(sev)] * n
    score = max(0, score)
    if counts["critical"]:
        score = min(score, 49)  # Any critical finding means an F.
    elif counts["high"]:
        score = min(score, 79)  # Any high finding caps the grade at C.
    letter = (
        "A"
        if score >= 90
        else "B"
        if score >= 80
        else "C"
        if score >= 65
        else "D"
        if score >= 50
        else "F"
    )
    return score, letter, counts
