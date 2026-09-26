import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Overview(BaseModel):
    users: int
    active_users: int
    workspaces: int
    websites: int
    verified_websites: int
    scans_total: int
    scans_last_24h: int
    scans_running: int
    ai_tokens_last_30d: int
    scanning_paused: bool
    smtp_configured: bool
    ai_configured: bool
    zap_configured: bool


class AdminUser(BaseModel):
    id: uuid.UUID
    email: str
    name: str | None
    is_active: bool
    is_superuser: bool
    mfa_enabled: bool
    email_verified: bool
    created_at: datetime
    websites: int
    scans: int


class AdminUserPatch(BaseModel):
    is_active: bool | None = None
    is_superuser: bool | None = None


class InstanceSettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    registration_open: bool
    scans_per_day_per_org: int
    max_targets_per_org: int
    scanning_paused: bool
    scanning_paused_reason: str | None
    updated_at: datetime


class InstanceSettingsPatch(BaseModel):
    registration_open: bool | None = None
    scans_per_day_per_org: int | None = Field(default=None, ge=0, le=10_000)
    max_targets_per_org: int | None = Field(default=None, ge=0, le=10_000)
    scanning_paused: bool | None = None
    scanning_paused_reason: str | None = Field(default=None, max_length=300)


class BlockedDomainIn(BaseModel):
    domain: str = Field(max_length=253)
    reason: str | None = Field(default=None, max_length=300)


class BlockedDomainOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    domain: str
    reason: str | None
    created_at: datetime


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    actor_email: str | None = None
    action: str
    subject: str | None
    ip: str | None
    details: dict[str, Any]
