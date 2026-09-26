"""Claude reviews a scan's findings: likely real or not, real-world severity, a plain
explanation and concrete fix steps for the site's stack, plus an executive summary.

Scanner output comes from the scanned site and is untrusted: it's redacted, wrapped as
data, and the model's answer is constrained to a schema. The A-F grade stays computed from
the scanners' own severities, so nothing in a site's content can talk the grade up."""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import anthropic
from pydantic import BaseModel

from app.ai.redact import redact
from app.core.config import get_settings
from app.scanning.normalize import SEVERITY_ORDER, RawFinding

log = logging.getLogger(__name__)
PROMPT_VERSION = "2026-09-25"

SYSTEM_PROMPT = (Path(__file__).parent / "system_prompt.md").read_text().strip()


class CodeExample(BaseModel):
    language: str
    code: str


class FindingAnalysis(BaseModel):
    id: str
    verdict: Literal["likely_real", "needs_review", "likely_false_positive"]
    severity: Literal["critical", "high", "medium", "low", "info"]
    explanation: str
    impact: str
    fix_steps: list[str]
    code_example: CodeExample | None


class ScanAnalysis(BaseModel):
    executive_summary: str
    top_priorities: list[str]
    findings: list[FindingAnalysis]


@dataclass
class AnalysisResult:
    status: Literal["ok", "skipped", "declined", "incomplete", "failed"]
    reason: str | None = None
    by_fingerprint: dict[str, dict[str, Any]] = field(default_factory=dict)
    executive_summary: str | None = None
    top_priorities: list[str] = field(default_factory=list)  # fingerprints
    model: str | None = None
    usage: dict[str, int] = field(default_factory=dict)

    def summary(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason": self.reason,
            "executive_summary": self.executive_summary,
            "top_priorities": self.top_priorities,
            "model": self.model,
            "usage": self.usage,
            "prompt_version": PROMPT_VERSION,
        }


def get_client() -> anthropic.AsyncAnthropic:
    return anthropic.AsyncAnthropic(api_key=get_settings().ai_api_key, max_retries=3)


def build_payload(
    url: str, observations: dict[str, Any], findings: list[RawFinding]
) -> tuple[str, dict[str, str]]:
    """The user message and a map of the ids used in it back to finding fingerprints."""
    refs: dict[str, str] = {}
    items = []
    for i, f in enumerate(findings, start=1):
        ref = f"F{i}"
        refs[ref] = f.fingerprint
        items.append(
            {
                "id": ref,
                "tool": f.tool,
                "rule": f.rule_id,
                "title": redact(f.title, 300),
                "scanner_severity": f.severity.value,
                "cwe": f.cwe,
                "location": redact(f.url + (f" (parameter: {f.param})" if f.param else ""), 300),
                "evidence": redact(f.evidence, 600),
                "scanner_description": redact(f.description, 600),
                "scanner_recommendation": redact(f.recommendation, 400),
            }
        )
    facts = {k: redact(str(v), 200) for k, v in sorted(observations.items())}
    data = json.dumps(
        {"website": url, "observed": facts, "findings": items}, indent=1, sort_keys=True
    )
    message = (
        f"Analyse the scan of {url}.\n\n<scan_data>\n{data}\n</scan_data>\n\n"
        "Return an analysis for every finding id above."
    )
    return message, refs


async def analyze(
    url: str, observations: dict[str, Any], findings: list[RawFinding]
) -> AnalysisResult:
    settings = get_settings()
    if not settings.ai_api_key:
        return AnalysisResult(
            status="skipped", reason="AI analysis isn't configured on this instance"
        )
    if not findings:
        return AnalysisResult(status="skipped", reason="No findings to analyse")

    chosen = sorted(findings, key=lambda f: SEVERITY_ORDER[f.severity])[: settings.ai_max_findings]
    message, refs = build_payload(url, observations, chosen)
    extra: dict[str, Any] = {}
    if settings.ai_fallbacks:
        # If a safety classifier declines (security content can trip the cyber category),
        # the API retries on the model Anthropic recommends for that category.
        extra = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}

    try:
        async with get_client().beta.messages.stream(
            model=settings.ai_model,
            max_tokens=32000,
            thinking={"type": "adaptive"},
            output_config={"effort": settings.ai_effort},
            system=[
                {"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}
            ],
            messages=[{"role": "user", "content": message}],
            output_format=ScanAnalysis,
            **extra,
        ) as stream:
            response = await stream.get_final_message()
    except anthropic.AuthenticationError:
        return AnalysisResult(status="failed", reason="The Anthropic API key was rejected")
    except anthropic.RateLimitError:
        return AnalysisResult(status="failed", reason="The Anthropic API rate limit was reached")
    except anthropic.APIStatusError as exc:
        log.warning("AI analysis failed: %s %s", exc.status_code, exc.message)
        return AnalysisResult(
            status="failed", reason=f"The Anthropic API returned an error ({exc.status_code})"
        )
    except anthropic.APIConnectionError:
        return AnalysisResult(status="failed", reason="The Anthropic API couldn't be reached")

    usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "cache_read_input_tokens": response.usage.cache_read_input_tokens or 0,
    }
    if response.stop_reason == "refusal":
        return AnalysisResult(
            status="declined",
            reason="The model declined to analyse this scan",
            model=response.model,
            usage=usage,
        )
    if response.stop_reason == "max_tokens":
        return AnalysisResult(
            status="incomplete",
            reason="The analysis was cut off",
            model=response.model,
            usage=usage,
        )
    parsed = response.parsed_output
    if parsed is None:
        return AnalysisResult(
            status="failed",
            reason="The analysis couldn't be read",
            model=response.model,
            usage=usage,
        )

    by_fp: dict[str, dict[str, Any]] = {}
    for item in parsed.findings:
        fp = refs.get(item.id)
        if fp:
            by_fp[fp] = item.model_dump(exclude={"id"})
    return AnalysisResult(
        status="ok",
        by_fingerprint=by_fp,
        executive_summary=parsed.executive_summary,
        top_priorities=[refs[r] for r in parsed.top_priorities if r in refs][:5],
        model=response.model,
        usage=usage,
    )
