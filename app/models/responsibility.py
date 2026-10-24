"""Responsibility and ResponsibilityBackup models.

A Responsibility links a primary Person to an Asset with a type and a backup
status. When backup_status is 'has_backup', one or more ResponsibilityBackup
records name the people who can fill in.
"""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

RESPONSIBILITY_TYPES = ("manages", "understands", "administers")
BACKUP_STATUSES = ("has_backup", "no_backup", "backup_unknown")


class Responsibility(Base):
    __tablename__ = "responsibilities"
    __table_args__ = (
        CheckConstraint(
            "responsibility_type IN ('manages', 'understands', 'administers')",
            name="ck_responsibility_type",
        ),
        CheckConstraint(
            "backup_status IN ('has_backup', 'no_backup', 'backup_unknown')",
            name="ck_responsibility_backup_status",
        ),
        UniqueConstraint(
            "asset_id",
            "primary_person_id",
            "responsibility_type",
            name="uq_responsibility_asset_person_type",
        ),
        Index("ix_responsibility_asset_id", "asset_id"),
        Index("ix_responsibility_primary_person_id", "primary_person_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), nullable=False
    )
    primary_person_id: Mapped[int] = mapped_column(
        ForeignKey("people.id", ondelete="CASCADE"), nullable=False
    )
    responsibility_type: Mapped[str] = mapped_column(String(20), nullable=False)
    backup_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="backup_unknown"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    asset: Mapped["Asset"] = relationship("Asset", back_populates="responsibilities")
    primary_person: Mapped["Person"] = relationship(
        "Person",
        back_populates="primary_responsibilities",
        foreign_keys=[primary_person_id],
    )
    backup_people: Mapped[list["ResponsibilityBackup"]] = relationship(
        "ResponsibilityBackup",
        back_populates="responsibility",
        cascade="all, delete-orphan",
    )


class ResponsibilityBackup(Base):
    __tablename__ = "responsibility_backups"
    __table_args__ = (
        UniqueConstraint(
            "responsibility_id",
            "backup_person_id",
            name="uq_responsibility_backup_person",
        ),
        Index("ix_resp_backup_responsibility_id", "responsibility_id"),
        Index("ix_resp_backup_person_id", "backup_person_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    responsibility_id: Mapped[int] = mapped_column(
        ForeignKey("responsibilities.id", ondelete="CASCADE"), nullable=False
    )
    backup_person_id: Mapped[int] = mapped_column(
        ForeignKey("people.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    responsibility: Mapped["Responsibility"] = relationship(
        "Responsibility", back_populates="backup_people"
    )
    backup_person: Mapped["Person"] = relationship(
        "Person", back_populates="backup_roles", foreign_keys=[backup_person_id]
    )
