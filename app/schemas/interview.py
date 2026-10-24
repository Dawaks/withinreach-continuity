"""Guided discovery interview schemas (design §6)."""

from pydantic import BaseModel


class ProposedResponsibility(BaseModel):
    primary_person_name: str
    responsibility_type: str                 # manages | understands | administers
    backup_status: str                       # has_backup | no_backup | backup_unknown
    backup_people_names: list[str] = []


class ProposedRecords(BaseModel):
    """Structured records proposed from one interview category's answers."""

    category_key: str
    asset_name: str
    asset_category: str
    asset_criticality: str = "medium"
    asset_description: str | None = None
    people: list[dict] = []                  # [{name, role_title}]
    responsibilities: list[ProposedResponsibility] = []
    documentation_status: str = "unknown"    # yes | no | unknown
    documentation_location: str | None = None
    depends_on_personal_account: bool = False
    personal_account_note: str | None = None
    depends_on_single_device: bool = False
    single_device_note: str | None = None
