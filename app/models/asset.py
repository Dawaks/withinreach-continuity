"""Asset model — a technology or service the organization depends on."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

ASSET_CATEGORIES = (
    "livestream",
    "website",
    "social_media",
    "network_wifi",
    "data_storage",
    "communication",
    "payment",
    "other",
)
CRITICALITY_LEVELS = ("critical", "high", "medium", "low")


class Asset(Base):
    __tablename__ = "assets"
    __table_args__ = (
        CheckConstraint(
            "category IN ('livestream', 'website', 'social_media', 'network_wifi', "
            "'data_storage', 'communication', 'payment', 'other')",
            name="ck_asset_category",
        ),
        CheckConstraint(
            "criticality IN ('critical', 'high', 'medium', 'low')",
            name="ck_asset_criticality",
        ),
        Index("ix_asset_organization_id", "organization_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    criticality: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="assets"
    )
    responsibilities: Mapped[list["Responsibility"]] = relationship(
        "Responsibility", back_populates="asset", cascade="all, delete-orphan"
    )
    documentation: Mapped["AssetDocumentation | None"] = relationship(
        "AssetDocumentation",
        back_populates="asset",
        uselist=False,
        cascade="all, delete-orphan",
    )
    dependency: Mapped["AssetDependency | None"] = relationship(
        "AssetDependency",
        back_populates="asset",
        uselist=False,
        cascade="all, delete-orphan",
    )
