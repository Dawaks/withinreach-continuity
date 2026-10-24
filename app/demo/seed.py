"""Grace Community Church demo data seeder.

Creates the full demo dataset from design §10. The seeder is idempotent:
if the organization already exists (matched by name), it does nothing, so
restarting the app does not create duplicate records.

This module only creates records. It does not compute risk scores or
implement any Phase 3+ feature.
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

DEMO_ORG_NAME = "Grace Community Church"

# --- Organization (design §10.1) ---
_ORGANIZATION = {
    "name": DEMO_ORG_NAME,
    "org_type": "church",
    "size": "~200 members",
    "description": (
        "A community church with weekly Sunday services, an active social "
        "media presence, and online giving."
    ),
}

# --- People (design §10.2) ---
_PEOPLE = [
    {"name": "Dami", "role_title": "Technology Coordinator", "email": "dami@gracecommunity.example"},
    {"name": "James", "role_title": "Media Volunteer", "email": "james@gracecommunity.example"},
    {"name": "Sarah", "role_title": "Church Administrator", "email": "sarah@gracecommunity.example"},
    {"name": "Pastor John", "role_title": "Pastor", "email": "john@gracecommunity.example"},
]

# --- Assets (design §10.3) ---
_ASSETS = [
    {"name": "Sunday Livestream", "category": "livestream", "criticality": "critical",
     "description": "Weekly Sunday service livestream via OBS"},
    {"name": "Church Website", "category": "website", "criticality": "high",
     "description": "WordPress site with sermon archives and event calendar"},
    {"name": "Church Instagram", "category": "social_media", "criticality": "medium",
     "description": "Official Instagram account for announcements and outreach"},
    {"name": "Wi-Fi Network", "category": "network_wifi", "criticality": "high",
     "description": "Office and guest Wi-Fi, router configuration"},
    {"name": "Donation Platform", "category": "payment", "criticality": "critical",
     "description": "Online giving platform (Stripe-based)"},
    {"name": "Google Drive", "category": "data_storage", "criticality": "high",
     "description": "Shared files: bulletins, service plans, financial records"},
    {"name": "Audio System", "category": "livestream", "criticality": "medium",
     "description": "Sound board and speakers for in-person service"},
    {"name": "Presentation Laptop", "category": "other", "criticality": "medium",
     "description": "Laptop used for slides and announcements during service"},
]

# --- Responsibilities and backup (design §10.4) ---
# Each tuple: (asset_name, primary_name, responsibility_type, backup_status, [backup_names])
_RESPONSIBILITIES = [
    ("Sunday Livestream", "Dami", "manages", "no_backup", []),
    ("Sunday Livestream", "James", "understands", "has_backup", ["Sarah"]),
    ("Church Website", "Dami", "administers", "has_backup", ["Sarah"]),
    ("Church Instagram", "Sarah", "manages", "backup_unknown", []),
    ("Wi-Fi Network", "Dami", "manages", "no_backup", []),
    ("Donation Platform", "Sarah", "administers", "has_backup", ["Pastor John"]),
    ("Google Drive", "Sarah", "manages", "has_backup", ["Dami"]),
    ("Audio System", "James", "manages", "has_backup", ["Dami"]),
    ("Audio System", "James", "understands", "no_backup", []),
    ("Presentation Laptop", "Dami", "manages", "no_backup", []),
]

# --- Documentation status (design §10.5) ---
# asset_name: (status, location_note)
_DOCUMENTATION = {
    "Sunday Livestream": ("no", None),
    "Church Website": ("yes", "Google Drive > IT folder"),
    "Church Instagram": ("no", None),
    "Wi-Fi Network": ("no", None),
    "Donation Platform": ("no", None),
    "Google Drive": ("yes", "Google Drive > Admin folder"),
    "Audio System": ("unknown", None),
    "Presentation Laptop": ("no", None),
}

# --- Dependency flags (design §10.6) ---
# asset_name: (personal_account, personal_note, single_device, device_note)
_DEPENDENCIES = {
    "Sunday Livestream": (False, None, True, "Livestream laptop in the sound booth"),
    "Church Website": (False, None, False, None),
    "Church Instagram": (False, None, False, None),
    "Wi-Fi Network": (True, "Router admin under Dami's personal email", False, None),
    "Donation Platform": (False, None, True, "Only accessible from the office laptop"),
    "Google Drive": (False, None, False, None),
    "Audio System": (False, None, False, None),
    "Presentation Laptop": (False, None, True, "The laptop itself is the single device"),
}


def demo_data_exists(db: Session) -> bool:
    """Return True if the Grace Community Church organization already exists."""
    return (
        db.query(Organization).filter(Organization.name == DEMO_ORG_NAME).first()
        is not None
    )


def seed_demo_data(db: Session) -> Organization | None:
    """Create the Grace Community Church demo dataset.

    Idempotent: if the demo organization already exists, returns None and makes
    no changes. Otherwise creates all records and returns the new Organization.
    """
    if demo_data_exists(db):
        return None

    # Organization
    org = Organization(**_ORGANIZATION)
    db.add(org)
    db.flush()  # assign org.id

    # People — keyed by name for relationship wiring
    people_by_name: dict[str, Person] = {}
    for person_data in _PEOPLE:
        person = Person(organization_id=org.id, **person_data)
        db.add(person)
        people_by_name[person.name] = person
    db.flush()  # assign person ids

    # Assets — keyed by name
    assets_by_name: dict[str, Asset] = {}
    for asset_data in _ASSETS:
        asset = Asset(organization_id=org.id, **asset_data)
        db.add(asset)
        assets_by_name[asset.name] = asset
    db.flush()  # assign asset ids

    # Responsibilities + backup people
    for asset_name, primary_name, resp_type, backup_status, backup_names in _RESPONSIBILITIES:
        responsibility = Responsibility(
            asset_id=assets_by_name[asset_name].id,
            primary_person_id=people_by_name[primary_name].id,
            responsibility_type=resp_type,
            backup_status=backup_status,
        )
        db.add(responsibility)
        db.flush()  # assign responsibility id
        for backup_name in backup_names:
            db.add(
                ResponsibilityBackup(
                    responsibility_id=responsibility.id,
                    backup_person_id=people_by_name[backup_name].id,
                )
            )

    # Documentation records
    for asset_name, (status, location_note) in _DOCUMENTATION.items():
        db.add(
            AssetDocumentation(
                asset_id=assets_by_name[asset_name].id,
                status=status,
                location_note=location_note,
            )
        )

    # Dependency records
    for asset_name, (personal, personal_note, device, device_note) in _DEPENDENCIES.items():
        db.add(
            AssetDependency(
                asset_id=assets_by_name[asset_name].id,
                depends_on_personal_account=personal,
                personal_account_note=personal_note,
                depends_on_single_device=device,
                single_device_note=device_note,
            )
        )

    db.commit()
    db.refresh(org)
    return org
