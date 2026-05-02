import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UpstreamAccount(Base):
    __tablename__ = "upstream_accounts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(100), nullable=False)
    mobile: Mapped[str | None] = mapped_column(String(20), nullable=True)
    password_enc: Mapped[str | None] = mapped_column(String(255), nullable=True)
    token: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("active", "disabled", "error", name="upstream_status"),
        default="active",
        nullable=False,
    )
    health: Mapped[str] = mapped_column(String(20), default="healthy", nullable=False)
    weight: Mapped[int] = mapped_column(Integer, default=50, nullable=False)
    total_requests: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
