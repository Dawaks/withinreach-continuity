"""Phase 10 security controls tests."""

import pytest

from app.models import Asset, Organization, Person, Responsibility, ResponsibilityBackup
from app.security import input_validation, secret_check
from app.services import interview_service, responsibility_service
from app.services.responsibility_service import ValidationError


# ---------- Secret value detection (blocked) ----------

@pytest.mark.parametrize(
    "text",
    [
        "password: mypassword",
        "password is hunter2",
        "Wi-Fi password = abc123",
        "API key: xyz",
        "token: abc",
        "access code: 1234",
        "recovery code: 998877",
        "client secret = xyz",
    ],
)
def test_secret_values_blocked(text):
    assert secret_check.check_for_secrets(text).blocked, text


# ---------- Benign security vocabulary (allowed) ----------

@pytest.mark.parametrize(
    "text",
    [
        "Password reset procedure is documented.",
        "The API key rotation process is in the IT binder.",
        "Users contact the administrator for password resets.",
        "Recovery codes are stored according to company policy.",
    ],
)
def test_benign_security_sentences_allowed(text):
    assert not secret_check.check_for_secrets(text).blocked, text


# ---------- Length limits ----------

def test_overlong_text_rejected():
    long_desc = "x" * 3000
    err = input_validation.validate_length(long_desc, "description")
    assert err is not None
    long_name = "y" * 300
    assert input_validation.validate_length(long_name, "name") is not None


def test_reasonable_text_allowed():
    assert input_validation.validate_length("Sunday Livestream", "asset_name") is None
    assert input_validation.validate_length("A normal note.", "note") is None


def test_validate_fields_reports_length_and_secret():
    result = input_validation.validate_fields(
        {
            "desc": ("x" * 3000, "description"),
            "note": ("the password is hunter2", "note"),
            "name": ("Fine", "name"),
        }
    )
    assert not result.valid
    assert "desc" in result.errors
    assert "note" in result.errors
    assert "name" not in result.errors


# ---------- Route-level: block vs allow in a note field (XSS + secret + benign) ----------

def test_dependency_note_secret_blocked_via_route(client):
    session = client._test_session_factory()
    asset = session.query(Asset).first()
    asset_id = asset.id
    session.close()

    resp = client.post(
        f"/assets/{asset_id}/dependency",
        data={
            "personal_account": "on",
            "personal_account_note": "the wifi password is hunter2",
            "single_device": "off",
            "single_device_note": "",
        },
        follow_redirects=False,
    )
    # Redirects back with an error, and the secret is NOT saved.
    assert resp.status_code == 303
    assert "error=" in resp.headers.get("location", "")

    session = client._test_session_factory()
    asset = session.query(Asset).get(asset_id)
    note = (asset.dependency.personal_account_note or "") if asset.dependency else ""
    session.close()
    assert "hunter2" not in note


def test_documentation_benign_note_allowed_via_route(client):
    session = client._test_session_factory()
    asset_id = session.query(Asset).first().id
    session.close()

    resp = client.post(
        f"/assets/{asset_id}/documentation",
        data={
            "status": "yes",
            "location_note": "Password reset procedure is documented in the IT binder.",
        },
        follow_redirects=False,
    )
    assert resp.status_code == 303
    assert "error=" not in resp.headers.get("location", "")

    session = client._test_session_factory()
    asset = session.query(Asset).get(asset_id)
    note = asset.documentation.location_note or ""
    session.close()
    assert "IT binder" in note


# ---------- XSS / template escaping ----------

def test_html_input_is_escaped(client, seeded_db):
    # Create a person with HTML-like name (no redirect follow).
    create = client.post(
        "/people/new",
        data={"name": '<script>alert("x")</script>', "role_title": "", "email": ""},
        follow_redirects=False,
    )
    assert create.status_code == 303
    page = client.get("/people").text
    # The raw script tag must not appear unescaped.
    assert '<script>alert("x")</script>' not in page
    # It should appear escaped.
    assert "&lt;script&gt;" in page


# ---------- Invalid IDs / enums handled safely ----------

def test_invalid_person_id_returns_404(client):
    resp = client.get("/people/999999")
    assert resp.status_code == 404


def test_invalid_asset_id_returns_404(client):
    resp = client.get("/assets/999999")
    assert resp.status_code == 404


def test_invalid_category_rejected(client):
    resp = client.post(
        "/assets/new",
        data={"name": "Bad", "category": "not_a_category", "criticality": "high", "description": ""},
        follow_redirects=False,
    )
    assert resp.status_code == 400  # controlled validation error, not a 500


def test_invalid_criticality_rejected(client):
    resp = client.post(
        "/assets/new",
        data={"name": "Bad", "category": "other", "criticality": "urgent", "description": ""},
        follow_redirects=False,
    )
    assert resp.status_code == 400


# ---------- Responsibility integrity ----------

def test_duplicate_responsibility_rejected(db):
    org = Organization(name="O", org_type="other")
    db.add(org); db.flush()
    p = Person(organization_id=org.id, name="P"); db.add(p); db.flush()
    a = Asset(organization_id=org.id, name="A", category="other", criticality="high")
    db.add(a); db.flush()
    responsibility_service.create_responsibility(db, a.id, p.id, "manages", "no_backup")
    with pytest.raises(ValidationError):
        responsibility_service.create_responsibility(db, a.id, p.id, "manages", "no_backup")


def test_self_backup_rejected(db):
    org = Organization(name="O", org_type="other")
    db.add(org); db.flush()
    p = Person(organization_id=org.id, name="P"); db.add(p); db.flush()
    a = Asset(organization_id=org.id, name="A", category="other", criticality="high")
    db.add(a); db.flush()
    with pytest.raises(ValidationError):
        responsibility_service.create_responsibility(
            db, a.id, p.id, "manages", "has_backup", backup_person_ids=[p.id]
        )


# ---------- FK / cascade integrity ----------

def test_delete_asset_cascades(db):
    org = Organization(name="O", org_type="other")
    db.add(org); db.flush()
    p = Person(organization_id=org.id, name="P"); db.add(p); db.flush()
    backup = Person(organization_id=org.id, name="B"); db.add(backup); db.flush()
    a = Asset(organization_id=org.id, name="A", category="other", criticality="high")
    db.add(a); db.flush()
    r = responsibility_service.create_responsibility(
        db, a.id, p.id, "manages", "has_backup", backup_person_ids=[backup.id]
    )
    rid = r.id
    db.delete(a)
    db.commit()
    assert db.query(Responsibility).filter_by(id=rid).first() is None
    assert db.query(ResponsibilityBackup).filter_by(responsibility_id=rid).count() == 0


def test_delete_person_removes_backup_references(db):
    org = Organization(name="O", org_type="other")
    db.add(org); db.flush()
    p = Person(organization_id=org.id, name="P"); db.add(p); db.flush()
    backup = Person(organization_id=org.id, name="B"); db.add(backup); db.flush()
    a = Asset(organization_id=org.id, name="A", category="other", criticality="high")
    db.add(a); db.flush()
    r = responsibility_service.create_responsibility(
        db, a.id, p.id, "manages", "has_backup", backup_person_ids=[backup.id]
    )
    db.delete(backup)
    db.commit()
    # No dangling backup reference remains.
    assert db.query(ResponsibilityBackup).filter_by(backup_person_id=backup.id).count() == 0
    # The responsibility itself survives.
    assert db.query(Responsibility).filter_by(id=r.id).first() is not None


# ---------- Interview save blocks secrets before persistence ----------

def test_interview_save_blocks_secret(seeded_db):
    org = seeded_db.query(Organization).first()
    rec = {
        "asset_name": "Secret Asset",
        "asset_category": "other",
        "asset_criticality": "medium",
        "primary_person_name": "Tester",
        "responsibility_type": "manages",
        "backup_status": "no_backup",
        "documentation_status": "yes",
        "documentation_location": "api key = abc123",
    }
    with pytest.raises(interview_service.SaveError):
        interview_service.save_confirmed_records(seeded_db, org.id, [rec])
    assert interview_service.find_existing_asset(seeded_db, org.id, "Secret Asset") is None
