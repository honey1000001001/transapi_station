from datetime import datetime

from pydantic import BaseModel


class UsageStats(BaseModel):
    total_requests: int
    total_tokens: int
    total_cost: float
    prompt_tokens: int
    completion_tokens: int
    reasoning_tokens: int


class UsageDetail(BaseModel):
    model: str
    requests: int
    prompt_tokens: int
    completion_tokens: int
    reasoning_tokens: int
    cost: float


class LogOut(BaseModel):
    id: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    reasoning_tokens: int
    cost: float
    latency_ms: int
    status: str
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class RechargeRequest(BaseModel):
    code: str


class InvoiceSummary(BaseModel):
    period: str
    total_requests: int
    total_tokens: int
    total_cost: float
