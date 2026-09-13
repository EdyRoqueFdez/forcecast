"""Report model for HU-V08 — Abusive vote/comment reporting."""

from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Enum as SAEnum
from app.db.session import Base


class Report(Base):
    """Report for abusive votes or comments."""

    __tablename__ = "reports"

    id = Column(String(36), primary_key=True)
    target_id = Column(String(36), nullable=False, index=True)
    target_type = Column(String(20), nullable=False)  # "vote" or "comment"
    reporter_id = Column(String(36), nullable=False, index=True)
    reason = Column(
        SAEnum("spam", "offensive", "false", "duplicate", "other", name="report_reason"),
        nullable=False,
    )
    details = Column(Text, nullable=True)
    status = Column(
        SAEnum("pending", "approved", "rejected", name="report_status"),
        nullable=False,
        default="pending",
    )
    reviewed_by = Column(String(36), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<Report {self.id} target={self.target_type}:{self.target_id} reason={self.reason}>"
