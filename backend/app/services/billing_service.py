import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment
from app.models.recharge_code import RechargeCode
from app.models.request_log import RequestLog
from app.models.user import User
from app.schemas.billing import InvoiceSummary, LogOut, UsageDetail, UsageStats

logger = logging.getLogger(__name__)


async def get_usage_stats(db: AsyncSession, user: User) -> UsageStats:
    result = await db.execute(
        select(
            func.count(RequestLog.id).label("total_requests"),
            func.coalesce(func.sum(RequestLog.prompt_tokens + RequestLog.completion_tokens), 0).label("total_tokens"),
            func.coalesce(func.sum(RequestLog.cost), 0).label("total_cost"),
            func.coalesce(func.sum(RequestLog.prompt_tokens), 0).label("prompt_tokens"),
            func.coalesce(func.sum(RequestLog.completion_tokens), 0).label("completion_tokens"),
            func.coalesce(func.sum(RequestLog.reasoning_tokens), 0).label("reasoning_tokens"),
        ).where(RequestLog.user_id == user.id)
    )
    row = result.one()
    return UsageStats(
        total_requests=row.total_requests or 0,
        total_tokens=int(row.total_tokens or 0),
        total_cost=float(row.total_cost or 0),
        prompt_tokens=int(row.prompt_tokens or 0),
        completion_tokens=int(row.completion_tokens or 0),
        reasoning_tokens=int(row.reasoning_tokens or 0),
    )


async def get_logs(
    db: AsyncSession, user: User, page: int = 1, page_size: int = 20
) -> list[LogOut]:
    offset = (page - 1) * page_size
    result = await db.execute(
        select(RequestLog)
        .where(RequestLog.user_id == user.id)
        .order_by(RequestLog.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    logs = result.scalars().all()
    return [
        LogOut(
            id=str(l.id),
            model=l.model,
            prompt_tokens=l.prompt_tokens,
            completion_tokens=l.completion_tokens,
            reasoning_tokens=l.reasoning_tokens,
            cost=float(l.cost),
            latency_ms=l.latency_ms,
            status=l.status,
            error_message=l.error_message,
            created_at=l.created_at,
        )
        for l in logs
    ]


async def get_balance(db: AsyncSession, user: User) -> dict:
    # Refresh user to get latest balance
    await db.refresh(user)
    return {"balance": float(user.balance)}


async def recharge(db: AsyncSession, user: User, code: str) -> dict:
    result = await db.execute(select(RechargeCode).where(RechargeCode.code == code))
    recharge_code = result.scalar_one_or_none()

    if not recharge_code:
        raise ValueError("Invalid recharge code")
    if recharge_code.used_by is not None:
        raise ValueError("Recharge code already used")

    amount = Decimal(str(recharge_code.amount))
    user.balance = Decimal(str(user.balance)) + amount

    # Mark code as used
    recharge_code.used_by = user.id
    recharge_code.used_at = datetime.now(timezone.utc)

    # Create payment record
    payment = Payment(
        user_id=user.id,
        amount=float(amount),
        method="recharge_code",
        status="completed",
        ref_id=recharge_code.id,
    )
    db.add(payment)

    await db.commit()
    await db.refresh(user)

    logger.info(f"User {user.username} recharged {amount}, new balance: {user.balance}")
    return {"balance": float(user.balance), "amount": float(amount)}


async def get_invoices(
    db: AsyncSession, user: User, period: str = "daily"
) -> list[InvoiceSummary]:
    if period == "daily":
        date_format = "%Y-%m-%d"
    elif period == "weekly":
        date_format = "%Y-W%W"
    elif period == "monthly":
        date_format = "%Y-%m"
    else:
        date_format = "%Y-%m-%d"

    # Use SQLite-compatible date truncation
    from app.config import settings
    if "sqlite" in settings.DATABASE_URL:
        period_expr = func.strftime(date_format, RequestLog.created_at)
    else:
        period_expr = func.to_char(RequestLog.created_at, date_format)

    result = await db.execute(
        select(
            period_expr.label("period"),
            func.count(RequestLog.id).label("total_requests"),
            func.coalesce(func.sum(RequestLog.prompt_tokens + RequestLog.completion_tokens), 0).label("total_tokens"),
            func.coalesce(func.sum(RequestLog.cost), 0).label("total_cost"),
        )
        .where(RequestLog.user_id == user.id)
        .group_by(period_expr)
        .order_by(period_expr.desc())
    )
    rows = result.all()
    return [
        InvoiceSummary(
            period=str(r.period or "unknown"),
            total_requests=r.total_requests or 0,
            total_tokens=int(r.total_tokens or 0),
            total_cost=float(r.total_cost or 0),
        )
        for r in rows
    ]
