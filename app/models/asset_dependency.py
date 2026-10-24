"""AssetDependency model — one-to-one with Asset.

Flags whether an asset depends on a personal account or a single device.
Note fields never store secrets.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AssetDependency(Base):
    __tablename__ = "asset_dependencies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    asset_id: Mapped[int] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    depends_on_personal_account: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    personal_account_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    depends_on_single_device: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    single_device_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    asset: Mapped["Asset"] = relationship("Asset", back_populates="dependency")
