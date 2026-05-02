from datetime import datetime

from pydantic import BaseModel


class AdminUserOut(BaseModel):
    id: str
    username: str
    email: str
    role: str
    balance: float
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminUserUpdate(BaseModel):
    username: str | None = None
    email: str | None = None
    role: str | None = None
    balance: float | None = None
    is_active: bool | None = None


class RateLimitUpdate(BaseModel):
    rpm_limit: int | None = None
    tpm_limit: int | None = None


class UpstreamAccountCreate(BaseModel):
    """创建上游账号：支持两种模式
    模式1 - 直连Token模式：填 token，邮箱可选（用于标识）
    模式2 - 账号池模式：填 email + password，系统自动登录获取token
    """
    email: str | None = None  # 直连Token模式下可选，系统自动生成
    mobile: str | None = None
    password: str | None = None  # 前端传入的明文密码，后端加密存储
    token: str | None = None     # 浏览器直接提取的DeepSeek token
    weight: int = 50


class UpstreamAccountUpdate(BaseModel):
    email: str | None = None
    mobile: str | None = None
    password: str | None = None  # 更新密码（明文，后端加密）
    token: str | None = None     # 更新token
    status: str | None = None
    health: str | None = None
    weight: int | None = None


class UpstreamAccountOut(BaseModel):
    id: str
    email: str
    mobile: str | None
    has_password: bool = False    # 是否配置了密码
    has_token: bool = False       # 是否配置了token
    auth_mode: str = "unknown"    # "pool" (账号池) / "direct" (直连Token)
    status: str
    health: str
    weight: int
    total_requests: int
    last_used_at: datetime | None
    last_error: str | None
    token_preview: str | None = None  # token前8位预览
    created_at: datetime

    model_config = {"from_attributes": True}


class RechargeCodeGenerate(BaseModel):
    amount: float
    count: int = 1
    quantity: int = 1  # frontend sends "quantity"


class StatsResponse(BaseModel):
    total_users: int
    active_users: int
    total_requests: int
    total_tokens: int
    total_revenue: float
    total_balance: float
    active_keys: int
    active_upstream_accounts: int
