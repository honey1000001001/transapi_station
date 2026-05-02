from datetime import datetime

from pydantic import BaseModel


class KeyCreate(BaseModel):
    name: str
    rpm_limit: int = 0
    tpm_limit: int = 0


class KeyUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    rpm_limit: int | None = None
    tpm_limit: int | None = None


class KeyOut(BaseModel):
    id: str
    key_prefix: str
    name: str
    is_active: bool
    rpm_limit: int
    tpm_limit: int
    total_requests: int
    total_tokens: int
    created_at: datetime

    model_config = {"from_attributes": True}


class KeyCreated(BaseModel):
    id: str
    key: str
    key_prefix: str
    name: str
    is_active: bool
    rpm_limit: int
    tpm_limit: int
    created_at: datetime

    model_config = {"from_attributes": True}
