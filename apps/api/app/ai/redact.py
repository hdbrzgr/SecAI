"""Strip secrets from scanner output before it leaves the instance."""

import re

_PATTERNS = [
    (re.compile(r"\b(AKIA|ASIA)[0-9A-Z]{16}\b"), "[redacted-aws-key]"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"), "[redacted-github-token]"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"), "[redacted-api-key]"),
    (
        re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
        "[redacted-jwt]",
    ),
    (
        re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
        "[redacted-private-key]",
    ),
    # key=value / key: value where the key names a secret
    (
        re.compile(
            r"(?i)\b([A-Z0-9_]*(?:secret|passw(?:or)?d|token|api[_-]?key|private[_-]?key|credential)[A-Z0-9_]*)"
            r"(\s*[=:]\s*)([^\s,;&\"']+)"
        ),
        r"\1\2[redacted]",
    ),
    (re.compile(r"(?i)(authorization:\s*(?:bearer|basic)\s+)\S+"), r"\1[redacted]"),
    # Long opaque strings (keys, session ids)
    (re.compile(r"\b[A-Za-z0-9+/_-]{40,}={0,2}\b"), "[redacted-token]"),
]


def redact(text: str | None, limit: int = 800) -> str | None:
    if not text:
        return text
    for pattern, repl in _PATTERNS:
        text = pattern.sub(repl, text)
    return text if len(text) <= limit else text[:limit] + " …[truncated]"
