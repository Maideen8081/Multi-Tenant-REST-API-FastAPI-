from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class TenantCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    plan: str = Field(default="free", pattern=r"^(free|pro|enterprise)$")
    contact_email: EmailStr | None = None
    rate_limit_override: int | None = Field(default=None, ge=1)


class TenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    plan: str
    status: str
    contact_email: str | None
    rate_limit_override: int | None
    created_at: datetime
    updated_at: datetime


class TenantProvisionResponse(TenantResponse):
    """Returned on onboarding — includes API key (shown once)."""
    api_key: str


class TenantUpdate(BaseModel):
    name: str | None = None
    plan: str | None = Field(default=None, pattern=r"^(free|pro|enterprise)$")
    status: str | None = Field(default=None, pattern=r"^(active|suspended)$")
    contact_email: EmailStr | None = None
    rate_limit_override: int | None = None
