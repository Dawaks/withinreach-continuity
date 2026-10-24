"""Asset service — CRUD, documentation and dependency setters, read helpers."""

from sqlalchemy.orm import Session

from app.models import Asset, AssetDependency, AssetDocumentation
from app.models.asset import ASSET_CATEGORIES, CRITICALITY_LEVELS
from app.models.asset_documentation import DOCUMENTATION_STATUSES

# Ordering so Critical assets sort first in the list view.
_CRITICALITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

# Human-friendly labels for asset categories.
CATEGORY_LABELS = {
    "livestream": "Livestream / A-V",
    "website": "Website / Domain",
    "social_media": "Social Media",
    "network_wifi": "Wi-Fi / Network",
    "data_storage": "Shared Files / Storage",
    "communication": "Email / Communication",
    "payment": "Payment / Donation",
    "other": "Other",
}


def count_assets(db: Session, organization_id: int) -> int:
    """Return the number of assets in the organization."""
    return (
        db.query(Asset)
        .filter(Asset.organization_id == organization_id)
        .count()
    )


def get_all_assets(db: Session, organization_id: int) -> list[Asset]:
    """Return all assets, Critical first then by name."""
    assets = (
        db.query(Asset)
        .filter(Asset.organization_id == organization_id)
        .all()
    )
    return sorted(
        assets,
        key=lambda a: (_CRITICALITY_ORDER.get(a.criticality, 99), a.name.lower()),
    )


def get_asset(db: Session, organization_id: int, asset_id: int) -> Asset | None:
    """Return an asset by id within the organization, or None."""
    return (
        db.query(Asset)
        .filter(Asset.organization_id == organization_id, Asset.id == asset_id)
        .first()
    )


def category_label(category: str) -> str:
    """Return a human-friendly label for an asset category."""
    return CATEGORY_LABELS.get(category, category.replace("_", " ").title())


def is_valid_category(category: str) -> bool:
    return category in ASSET_CATEGORIES


def is_valid_criticality(criticality: str) -> bool:
    return criticality in CRITICALITY_LEVELS


def create_asset(
    db: Session,
    organization_id: int,
    name: str,
    category: str,
    criticality: str,
    description: str | None = None,
) -> Asset:
    """Create an asset with empty documentation and dependency records."""
    asset = Asset(
        organization_id=organization_id,
        name=name.strip(),
        category=category,
        criticality=criticality,
        description=(description or "").strip() or None,
    )
    db.add(asset)
    db.flush()
    # Create default documentation and dependency records so the detail page
    # always has something to edit.
    db.add(AssetDocumentation(asset_id=asset.id, status="unknown"))
    db.add(
        AssetDependency(
            asset_id=asset.id,
            depends_on_personal_account=False,
            depends_on_single_device=False,
        )
    )
    db.commit()
    db.refresh(asset)
    return asset


def update_asset(
    db: Session,
    asset: Asset,
    name: str,
    category: str,
    criticality: str,
    description: str | None = None,
) -> Asset:
    """Update an asset's core fields."""
    asset.name = name.strip()
    asset.category = category
    asset.criticality = criticality
    asset.description = (description or "").strip() or None
    db.commit()
    db.refresh(asset)
    return asset


def delete_asset(db: Session, asset: Asset) -> None:
    """Delete an asset. Cascade removes responsibilities (and their backups),
    documentation, and dependency records."""
    db.delete(asset)
    db.commit()


def set_documentation(
    db: Session,
    asset: Asset,
    status: str,
    location_note: str | None = None,
) -> AssetDocumentation:
    """Set the asset's documentation status and optional location note."""
    doc = asset.documentation
    if doc is None:
        doc = AssetDocumentation(asset_id=asset.id, status="unknown")
        db.add(doc)
    doc.status = status
    doc.location_note = (location_note or "").strip() or None
    db.commit()
    db.refresh(asset)
    return doc


def set_dependency(
    db: Session,
    asset: Asset,
    depends_on_personal_account: bool,
    personal_account_note: str | None,
    depends_on_single_device: bool,
    single_device_note: str | None,
) -> AssetDependency:
    """Set the asset's personal-account and single-device dependency flags."""
    dep = asset.dependency
    if dep is None:
        dep = AssetDependency(asset_id=asset.id)
        db.add(dep)
    dep.depends_on_personal_account = depends_on_personal_account
    dep.personal_account_note = (personal_account_note or "").strip() or None
    dep.depends_on_single_device = depends_on_single_device
    dep.single_device_note = (single_device_note or "").strip() or None
    db.commit()
    db.refresh(asset)
    return dep


def is_valid_documentation_status(status: str) -> bool:
    return status in DOCUMENTATION_STATUSES
