import logging
import secrets

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.payment import Payment
from app.models.recharge_code import RechargeCode
from app.models.user import User
from app.schemas.admin import RechargeCodeGenerate

logger = logging.getLogger(__name__)


async def create_recharge_codes(
    db: AsyncSession, admin: User, data: RechargeCodeGenerate
) -> list[dict]:
    # Support both "count" and "quantity" fields
    count = getattr(data, 'quantity', None) or data.count or 1
    codes = []
    for _ in range(count):
        code = secrets.token_urlsafe(16)[:24].upper()
        recharge = RechargeCode(
            code=code,
            amount=data.amount,
            created_by=admin.id,
        )
        db.add(recharge)
        codes.append({"code": code, "amount": data.amount})

    await db.commit()
    logger.info(f"Admin {admin.username} generated {count} recharge codes")
    return codes


async def list_recharge_codes(
    db: AsyncSession, page: int = 1, page_size: int = 20
) -> list[dict]:
    total = (await db.execute(select(func.count(RechargeCode.id)))).scalar() or 0
    offset = (page - 1) * page_size
    result = await db.execute(
        select(RechargeCode)
        .order_by(RechargeCode.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    codes = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "code": c.code,
            "amount": float(c.amount),
            "status": "used" if c.used_by is not None else "unused",
            "used_by": c.used_by,
            "used_at": c.used_at.isoformat() if c.used_at else None,
            "created_by": c.created_by,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in codes
    ]


async def list_payments(
    db: AsyncSession, page: int = 1, page_size: int = 20
) -> list[dict]:
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Payment)
        .order_by(Payment.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    payments = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "user_id": p.user_id,
            "amount": float(p.amount),
            "method": p.method,
            "status": p.status,
            "ref_id": p.ref_id,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in payments
    ]
