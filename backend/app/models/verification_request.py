import uuid
import enum
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Enum, ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class VerificationStatus(str, enum.Enum):
    pending = "pending"
    verified = "verified"
    cancelled = "cancelled"
    revoked = "revoked"


class VerificationRequest(Base):
    __tablename__ = "verification_requests"
    __table_args__ = (UniqueConstraint("assignment_id", "requester_id", "group_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    assignment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"))
    group_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("groups.id", ondelete="CASCADE"))
    requester_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    verifier_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    status: Mapped[VerificationStatus] = mapped_column(
        Enum(VerificationStatus, name="verification_status", native_enum=False),
        default=VerificationStatus.pending,
    )
    verification_word: Mapped[str] = mapped_column(String(20))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
