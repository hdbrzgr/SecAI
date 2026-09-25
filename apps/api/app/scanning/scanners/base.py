from dataclasses import dataclass, field
from typing import Any, Protocol

from app.scanning.normalize import RawFinding


class ScannerUnavailable(Exception):
    """The tool isn't installed on this worker; the scan continues without it."""


@dataclass
class ScanContext:
    url: str  # the target origin, like https://example.com/
    hostname: str
    # Facts scanners learn about the site (server software, frameworks) for the AI step.
    observations: dict[str, Any] = field(default_factory=dict)


class Scanner(Protocol):
    name: str
    label: str  # what the progress line says while it runs

    async def run(self, ctx: ScanContext) -> list[RawFinding]: ...
