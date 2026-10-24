"""Tests for the backup-person data model and responsibility service."""

import pytest

from app.models import Asset, Organization, Person, Responsibility, ResponsibilityBackup
from app.services import responsibility_service
from app.services.responsibility_service import ValidationError


def _org(db):
    o = Organization(name="BR Org", org_type="other")
    db.add(o)
    db.flush()
    return o


def _person(db, org, name):
    p = Person(organization_id=org.id, name=name)
    db.add(p)
    db.flush()
    return p


def _asset(db, org, name="Asset"):
    a = Asset(organization_id=org.id, name=name, category="other", criticality="high")
    db.add(a)
    db.flush()
    return a


def test_create_with_backup(db):
    org = _org(db)
    primary = _person(db, org, "Dami")
    backup = _person(db, org, "Sarah")
    asset = _asset(db, org)
    r = responsibility_service.create_responsibility(
        db, asset.id, primary.id, "manages", "has_backup", backup_person_ids=[backup.id]
    )
    assert len(r.backup_people) == 1
    assert r.backup_people[0].backup_person_id == backup.id


def test_create_no_backup(db):
    org = _org(db)
    primary = _person(db, org, "Dami")
    asset = _asset(db, org)
    r = responsibility_service.create_responsibility(
        db, asset.id, primary.id, "manages", "no_backup"
    )
    assert r.backup_people == []


def test_create_backup_unknown(db):
    org = _org(db)
    primary = _person(db, org, "Dami")
    asset = _asset(db, org)
    r = responsibility_service.create_responsibility(
        db, asset.id, primary.id, "manages", "backup_unknown"
    )
    assert r.backup_people == []


def test_change_to_no_backup_removes_backups(db):
    org = _org(db)
    primary = _person(db, org, "Dami")
    backup = _person(db, org, "Sarah")
    asset = _asset(db, org)
    r = responsibility_service.create_responsibility(
        db, asset.id, primary.id, "manages", "has_backup", backup_person_ids=[backup.id]
    )
    responsibility_service.update_responsibility(db, r, "manages", "no_backup")
    assert db.query(ResponsibilityBackup).filter_by(responsibility_id=r.id).count() == 0


def test_multiple_backup_people(db):
    org = _org(db)
    primary = _person(db, org, "Dami")
    b1 = _person(db, org, "Sarah")
    b2 = _person(db, org, "James")
    asset = _asset(db, org)
    r = responsibility_service.create_responsibility(
        db, asset.id, primary.id, "manages", "has_backup",
        backup_person_ids=[b1.id, b2.id],
    )
    assert len(r.backup_people) == 2


def test_primary_and_backup_on_different_responsibilities(db):
    org = _org(db)
    a_person = _person(db, org, "A")
    b_person = _person(db, org, "B")
    asset1 = _asset(db, org, "Asset1")
    asset2 = _asset(db, org, "Asset2")
    # A is primary on asset1 with B as backup
    responsibility_service.create_responsibility(
        db, asset1.id, a_person.id, "manages", "has_backup", backup_person_ids=[b_person.id]
    )
    # A is a backup on asset2 where B is primary
    responsibility_service.create_responsibility(
        db, asset2.id, b_person.id, "manages", "has_backup", backup_person_ids=[a_person.id]
    )
    assert len(a_person.primary_responsibilities) == 1
    assert len(a_person.backup_roles) == 1


def test_duplicate_responsibility_rejected(db):
    org = _org(db)
    primary = _person(db, org, "Dami")
    asset = _asset(db, org)
    responsibility_service.create_responsibility(
        db, asset.id, primary.id, "manages", "no_backup"
    )
    with pytest.raises(ValidationError):
        responsibility_service.create_responsibility(
            db, asset.id, primary.id, "manages", "no_backup"
        )


def test_self_backup_rejected(db):
    org = _org(db)
    primary = _person(db, org, "Dami")
    asset = _asset(db, org)
    with pytest.raises(ValidationError):
        responsibility_service.create_responsibility(
            db, asset.id, primary.id, "manages", "has_backup",
            backup_person_ids=[primary.id],
        )


def test_has_backup_requires_a_person(db):
    org = _org(db)
    primary = _person(db, org, "Dami")
    asset = _asset(db, org)
    with pytest.raises(ValidationError):
        responsibility_service.create_responsibility(
            db, asset.id, primary.id, "manages", "has_backup", backup_person_ids=[]
        )


def test_delete_person_removes_links(db, seeded_db=None):
    org = _org(db)
    primary = _person(db, org, "Dami")
    backup = _person(db, org, "Sarah")
    asset = _asset(db, org)
    r = responsibility_service.create_responsibility(
        db, asset.id, primary.id, "manages", "has_backup", backup_person_ids=[backup.id]
    )
    # Delete the backup person -> the backup association is removed by cascade.
    db.delete(backup)
    db.commit()
    assert db.query(ResponsibilityBackup).filter_by(responsibility_id=r.id).count() == 0
    # The responsibility itself still exists (primary unchanged).
    assert db.query(Responsibility).filter_by(id=r.id).first() is not None
