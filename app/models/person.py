"""Person model — a lightweight record of someone involved with the organization.

A Person is NOT a login account. Email is optional contact info only and is
never used for authentication.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Person(Base):
    __tablename__ = "people"
    __table_args__ = (
        Index("ix_person_organization_id", "organization_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    role_title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="people"
    )
    primary_responsibilities: Mapped[list["Responsibility"]] = relationship(
        "Responsibility",
        back_populates="primary_person",
        foreign_keys="Responsibility.primary_person_id",
        cascade="all, delete-orphan",
    )
    backup_roles: Mapped[list["ResponsibilityBackup"]] = relationship(
        "ResponsibilityBackup",
        back_populates="backup_person",
        foreign_keys="ResponsibilityBackup.backup_person_id",
        cascade="all, delete-orphan",
    )
