import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class RoleEnum(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"


class ProviderEnum(str, enum.Enum):
    GOOGLE = "google"
    GITHUB = "github"
    EMAIL = "email"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None)
    role: Mapped[RoleEnum] = mapped_column(SAEnum(RoleEnum, name="role_enum"), default=RoleEnum.USER, nullable=False)
    # Spec says default 0.0 but anti-bot & design use 5.0 as initial healthy score
    reputation_score: Mapped[float] = mapped_column(Float, default=5.0, nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
