"""Demo data reset helper.

Wipes all application data and reseeds the Grace Community Church dataset so
the database can be restored to the approved demo state at any time.
"""

from sqlalchemy.orm import Session

from app.models import (
    Asset,
    AssetDependency,
    AssetDocumentation,
    Organization,
    Person,
    Responsibility,
    ResponsibilityBackup,
)
from app.demo.seed import seed_demo_data


def wipe_all_data(db: Session) -> None:
    """Delete all records from every table.

    Deletes children before parents to respect foreign keys. Deleting the
    organization would cascade, but we delete explicitly for clarity and so
    the behaviour does not depend on cascade configuration.
    """
    db.query(ResponsibilityBackup).delete()
    db.query(Responsibility).delete()
    db.query(AssetDocumentation).delete()
    db.query(AssetDependency).delete()
    db.query(Asset).delete()
    db.query(Person).delete()
    db.query(Organization).delete()
    db.commit()


def reset_demo_data(db: Session) -> Organization | None:
    """Wipe all data and reseed the Grace Community Church demo dataset.

    Returns the newly created Organization.
    """
    wipe_all_data(db)
    return seed_demo_data(db)
