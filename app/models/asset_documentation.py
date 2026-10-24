"""AssetDocumentation model — one-to-one with Asset.

Records whether documentation exists and optionally where it is located.
Never stores the documentation content itself or any secrets.
"""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

DOCUMENTATION_STATUSES = ("yes", "no", "unknown")


class AssetDocumentation(Base):
    __tablename__ = "asset_documentation"
    __table_args__ = (
        CheckConstraint(
            "status IN ('yes', 'no', 'unknown')",
            name="ck_asset_documentation_status",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="unknown")
    location_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    asset: Mapped["Asset"] = relationship("Asset", back_populates="documentation")
