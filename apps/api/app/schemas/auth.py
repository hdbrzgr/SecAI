import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterIn(BaseModel):
    email: EmailStr
    # The minimum is enforced in the route so it follows SECAI_PASSWORD_MIN_LENGTH.
    password: str = Field(max_length=128)
    name: str | None = Field(default=None, max_length=200)

    @field_validator("email")
    @classmethod
    def _normalize(cls, v: str) -> str:
        return v.strip().lower()


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)

    @field_validator("email")
    @classmethod
    def _normalize(cls, v: str) -> str:
        return v.strip().lower()


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    name: str | None
    is_superuser: bool
    mfa_enabled: bool


class LoginOut(BaseModel):
    mfa_required: bool
    user: UserOut | None = None


class TotpCodeIn(BaseModel):
    code: str = Field(min_length=6, max_length=8)


class MfaSetupOut(BaseModel):
    secret: str
    otpauth_uri: str


class MfaDisableIn(BaseModel):
    password: str = Field(max_length=128)
    code: str = Field(min_length=6, max_length=8)
