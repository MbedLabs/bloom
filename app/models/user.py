"""
User model and role enum.
"""

import base64
import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime
from sqlalchemy import Enum as SaEnum
from sqlalchemy import ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    maintainer = "maintainer"
    external = "external"


class User(Base):
    """An account. session_version increases on a password change or reset and on a confirmed email
    change. pending_email holds a requested address until it is confirmed: an administrator's own
    change needs authorization from the current mailbox, other roles need administrator approval,
    and every change needs verification from the new mailbox.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    profile_picture: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SaEnum(UserRole), default=UserRole.external, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    session_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    invited_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    invited_by_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    last_invite_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    invite_accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    password_set_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    pending_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email_change_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    email_change_requested_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    api_token_jti: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    @property
    def has_profile_picture(self) -> bool:
        """Whether the account has a stored profile image."""
        return bool(self.profile_picture)

    @property
    def profile_picture_url(self) -> str | None:
        """The normalized account picture as a PNG data URL, or no picture."""
        if not self.profile_picture:
            return None
        return "data:image/png;base64," + base64.b64encode(self.profile_picture).decode("ascii")
