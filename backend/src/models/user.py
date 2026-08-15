import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    engineer = "engineer"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, default=UserRole.engineer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    work_orders_assigned: Mapped[list["WorkOrder"]] = relationship(
        "WorkOrder", foreign_keys="WorkOrder.assigned_to", back_populates="assigned_user"
    )
    work_orders_created: Mapped[list["WorkOrder"]] = relationship(
        "WorkOrder", foreign_keys="WorkOrder.created_by", back_populates="created_by_user"
    )
    diagnostic_sessions: Mapped[list["DiagnosticSession"]] = relationship(
        "DiagnosticSession", back_populates="user"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
