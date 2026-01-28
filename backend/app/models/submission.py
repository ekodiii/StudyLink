import uuid
from datetime import datetime, timezone
import enum

from sqlalchemy import String, DateTime, Enum, ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class SubmissionStatus(str, enum.Enum):
    unsubmitted = "unsubmitted"
    submitted = "submitted"
    late = "late"
    missing = "missing"
    graded = "graded"


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (UniqueConstraint("assignment_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    assignment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assignments.id", ondelete="CASCADE"))
    status: Mapped[SubmissionStatus] = mapped_column(Enum(SubmissionStatus, name="submission_status", native_enum=False), default=SubmissionStatus.unsubmitted)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
