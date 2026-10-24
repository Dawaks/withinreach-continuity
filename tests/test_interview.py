"""Tests for the non-AI guided discovery interview (Phase 8)."""

from app.models import Asset, Organization, Person, Responsibility
from app.services import interview_service, risk_scoring
from app.services.dependency_map_service import build_graph_data


# ---------- Categories ----------

def test_category_definitions():
    assert interview_service.CATEGORY_COUNT == 8
    keys = [c["key"] for c in interview_service.CATEGORIES]
    assert keys == [
        "livestream", "website", "social_media", "network_wifi",
        "data_storage", "payment", "communication", "other",
    ]
    for c in interview_service.CATEGORIES:
        assert c["label"] and c["asset_category"]


def test_get_category_bounds():
    assert interview_service.get_category(0)["key"] == "livestream"
    assert interview_service.get_category(7)["key"] == "other"
    assert interview_service.get_category(8) is None
    assert interview_service.get_category(-1) is None


# ---------- Structured mapping ----------

def test_structured_mapping_full_example():
    answers = {
        "uses": "yes",
        "asset_name": "Sunday Livestream",
        "person_name": "Dami",
        "role_title": "Technology Coordinator",
        "responsibility_type": "manages",
        "backup": "no",
        "docs": "no",
        "single_device": "yes",
        "account": "org",
    }
    p = interview_service.structured_form_fallback("livestream", answers)
    assert p is not None
    assert p.asset_name == "Sunday Livestream"
    assert p.asset_category == "livestream"
    assert p.asset_criticality == "medium"
    assert p.people[0]["name"] == "Dami"
    assert p.responsibilities[0].responsibility_type == "manages"
    assert p.responsibilities[0].backup_status == "no_backup"
    assert p.documentation_status == "no"
    assert p.depends_on_single_device is True
    assert p.depends_on_personal_account is False


def test_backup_yes_no_notsure_mapping():
    base = {"uses": "yes", "asset_name": "A", "person_name": "P", "docs": "no"}
    yes = interview_service.structured_form_fallback(
        "website", {**base, "backup": "yes", "backup_person_name": "Sarah"}
    )
    assert yes.responsibilities[0].backup_status == "has_backup"
    assert yes.responsibilities[0].backup_people_names == ["Sarah"]

    no = interview_service.structured_form_fallback("website", {**base, "backup": "no"})
    assert no.responsibilities[0].backup_status == "no_backup"

    unsure = interview_service.structured_form_fallback("website", {**base, "backup": "not_sure"})
    assert unsure.responsibilities[0].backup_status == "backup_unknown"


def test_backup_yes_without_name_downgrades_to_unknown():
    p = interview_service.structured_form_fallback(
        "website",
        {"uses": "yes", "asset_name": "A", "person_name": "P", "backup": "yes", "backup_person_name": ""},
    )
    assert p.responsibilities[0].backup_status == "backup_unknown"
    assert p.responsibilities[0].backup_people_names == []


def test_documentation_mapping():
    base = {"uses": "yes", "asset_name": "A", "person_name": "P", "backup": "no"}
    yes = interview_service.structured_form_fallback(
        "website", {**base, "docs": "yes", "doc_location": "Drive > IT"}
    )
    assert yes.documentation_status == "yes"
    assert yes.documentation_location == "Drive > IT"
    assert interview_service.structured_form_fallback("website", {**base, "docs": "no"}).documentation_status == "no"
    assert interview_service.structured_form_fallback("website", {**base, "docs": "not_sure"}).documentation_status == "unknown"


def test_dependency_flag_mapping():
    base = {"uses": "yes", "asset_name": "A", "person_name": "P", "backup": "no", "docs": "no"}
    personal = interview_service.structured_form_fallback("website", {**base, "account": "personal"})
    assert personal.depends_on_personal_account is True
    org = interview_service.structured_form_fallback("website", {**base, "account": "org"})
    assert org.depends_on_personal_account is False
    dev = interview_service.structured_form_fallback("website", {**base, "single_device": "yes"})
    assert dev.depends_on_single_device is True


def test_skip_and_no_produce_no_records():
    assert interview_service.structured_form_fallback("website", {"uses": "skip"}) is None
    assert interview_service.structured_form_fallback("website", {"uses": "no"}) is None
    assert interview_service.structured_form_fallback("website", {"uses": ""}) is None


# ---------- Duplicate detection ----------

def test_duplicate_person_detection(seeded_db):
    org = seeded_db.query(Organization).first()
    assert interview_service.find_existing_person(seeded_db, org.id, "Dami") is not None
    assert interview_service.find_existing_person(seeded_db, org.id, "  dami ") is not None  # normalized
    assert interview_service.find_existing_person(seeded_db, org.id, "Nobody") is None


def test_duplicate_asset_detection(seeded_db):
    org = seeded_db.query(Organization).first()
    assert interview_service.find_existing_asset(seeded_db, org.id, "Sunday Livestream") is not None
    assert interview_service.find_existing_asset(seeded_db, org.id, "sunday livestream") is not None
    assert interview_service.find_existing_asset(seeded_db, org.id, "Unknown Asset") is None


# ---------- Saving ----------

def _new_record(**over):
    rec = {
        "asset_name": "Projector System",
        "asset_category": "other",
        "asset_criticality": "high",
        "asset_description": None,
        "asset_existing_id": "",
        "primary_person_name": "Taylor",
        "primary_person_role": "Volunteer",
        "primary_person_existing_id": "",
        "responsibility_type": "manages",
        "backup_status": "no_backup",
        "backup_person_name": "",
        "backup_person_existing_id": "",
        "documentation_status": "no",
        "documentation_location": None,
        "depends_on_personal_account": False,
        "personal_account_note": None,
        "depends_on_single_device": True,
        "single_device_note": None,
    }
    rec.update(over)
    return rec


def test_save_new_records(seeded_db):
    org = seeded_db.query(Organization).first()
    before_people = seeded_db.query(Person).count()
    before_assets = seeded_db.query(Asset).count()
    interview_service.save_confirmed_records(seeded_db, org.id, [_new_record()])
    assert seeded_db.query(Person).count() == before_people + 1  # Taylor
    assert seeded_db.query(Asset).count() == before_assets + 1   # Projector System
    asset = interview_service.find_existing_asset(seeded_db, org.id, "Projector System")
    assert asset is not None
    assert asset.responsibilities[0].primary_person.name == "Taylor"
    assert asset.dependency.depends_on_single_device is True


def test_reuse_existing_person_and_asset(seeded_db):
    org = seeded_db.query(Organization).first()
    dami = interview_service.find_existing_person(seeded_db, org.id, "Dami")
    website = interview_service.find_existing_asset(seeded_db, org.id, "Church Website")
    before_people = seeded_db.query(Person).count()
    before_assets = seeded_db.query(Asset).count()

    # Reuse existing Dami + existing Website, add a new 'understands' responsibility.
    rec = _new_record(
        asset_existing_id=str(website.id),
        primary_person_existing_id=str(dami.id),
        primary_person_name="Dami",
        responsibility_type="understands",
    )
    interview_service.save_confirmed_records(seeded_db, org.id, [rec])

    # No new person or asset created.
    assert seeded_db.query(Person).count() == before_people
    assert seeded_db.query(Asset).count() == before_assets


def test_newly_saved_records_affect_risk(seeded_db):
    org = seeded_db.query(Organization).first()
    before = risk_scoring.calculate_org_risk(seeded_db, org.id)
    before_count = len(before.asset_risks)
    interview_service.save_confirmed_records(seeded_db, org.id, [_new_record()])
    after = risk_scoring.calculate_org_risk(seeded_db, org.id)
    assert len(after.asset_risks) == before_count + 1
    names = {r.asset_name for r in after.asset_risks}
    assert "Projector System" in names


def test_newly_saved_records_appear_in_map(seeded_db):
    org = seeded_db.query(Organization).first()
    interview_service.save_confirmed_records(seeded_db, org.id, [_new_record()])
    graph = build_graph_data(seeded_db, org.id)
    asset_labels = {n["data"]["label"] for n in graph["nodes"] if n["data"]["type"] == "asset"}
    person_labels = {n["data"]["label"] for n in graph["nodes"] if n["data"]["type"] == "person"}
    assert "Projector System" in asset_labels
    assert "Taylor" in person_labels


def test_save_blocks_secret(seeded_db):
    org = seeded_db.query(Organization).first()
    rec = _new_record(documentation_location="the wifi password is hunter2")
    import pytest
    with pytest.raises(interview_service.SaveError):
        interview_service.save_confirmed_records(seeded_db, org.id, [rec])
    # Nothing persisted.
    assert interview_service.find_existing_asset(seeded_db, org.id, "Projector System") is None


def test_save_allows_benign_password_mention(seeded_db):
    org = seeded_db.query(Organization).first()
    rec = _new_record(documentation_location="Password reset procedure is in the IT binder.")
    interview_service.save_confirmed_records(seeded_db, org.id, [rec])
    asset = interview_service.find_existing_asset(seeded_db, org.id, "Projector System")
    assert asset is not None
    assert "IT binder" in asset.documentation.location_note
