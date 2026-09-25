import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models import ScanStatus, Severity, VerificationMethod


class TargetIn(BaseModel):
    url: str = Field(max_length=2048)


class VerifyIn(BaseModel):
    method: VerificationMethod


class ScanBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: ScanStatus
    progress: int
    current_step: str | None
    summary: dict[str, Any]
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None


class TargetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    hostname: str
    verification_token: str
    verification_method: VerificationMethod | None
    verified_at: datetime | None
    verification_expired: bool = False
    created_at: datetime
    last_scan: ScanBrief | None = None


class ScanIn(BaseModel):
    # The user confirms, for this scan, that they own the site or may test it.
    authorized: bool


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tool: str
    rule_id: str
    title: str
    severity: Severity
    cwe: str | None
    location: dict[str, Any]
    evidence: str | None
    description: str | None
    recommendation: str | None
    references: list[str]


class ScanOut(ScanBrief):
    target_id: uuid.UUID | None
    target_url: str | None = None
    error: str | None
    findings: list[FindingOut] = []
