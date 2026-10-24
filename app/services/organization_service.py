"""Organization service — single-organization access for the MVP.

The MVP uses a single organization (the first one created, or the demo seed
data). These helpers read and update that organization.
"""

from sqlalchemy.orm import Session

from app.models import Organization


def get_organization(db: Session) -> Organization | None:
    """Return the current (first) organization, or None if none exists."""
    return db.query(Organization).order_by(Organization.id).first()


def organization_exists(db: Session) -> bool:
    """Return True if any organization exists."""
    return get_organization(db) is not None


def create_organization(
    db: Session,
    name: str,
    org_type: str,
    size: str | None = None,
    description: str | None = None,
) -> Organization:
    """Create a new organization and return it."""
    org = Organization(
        name=name,
        org_type=org_type,
        size=size or None,
        description=description or None,
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    return org


def update_organization(
    db: Session,
    org: Organization,
    name: str,
    org_type: str,
    size: str | None = None,
    description: str | None = None,
) -> Organization:
    """Update an existing organization and return it."""
    org.name = name
    org.org_type = org_type
    org.size = size or None
    org.description = description or None
    db.commit()
    db.refresh(org)
    return org
