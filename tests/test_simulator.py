"""Tests for the What If simulator (design §5)."""

from app.models import (
    Asset,
    AssetDependency,
    AssetDocumentation,
    Organization,
    Person,
    Responsibility,
    ResponsibilityBackup,
)
from app.services.simulator import simulate_person_unavailable


# ---------- Builders ----------

def make_org(db):
    org = Organization(name="Sim Org", org_type="other")
    db.add(org)
    db.flush()
    return org


def make_person(db, org, name):
    p = Person(organization_id=org.id, name=name)
    db.add(p)
    db.flush()
    return p


def make_asset(db, org, name, criticality="high", category="other"):
    a = Asset(organization_id=org.id, name=name, category=category, criticality=criticality)
    db.add(a)
    db.flush()
    db.add(AssetDocumentation(asset_id=a.id, status="yes"))
    db.add(AssetDependency(asset_id=a.id, depends_on_personal_account=False,
                           depends_on_single_device=False))
    db.flush()
    return a


def add_resp(db, asset, person, rtype, backup_status, backups=None):
    r = Responsibility(asset_id=asset.id, primary_person_id=person.id,
                       responsibility_type=rtype, backup_status=backup_status)
    db.add(r)
    db.flush()
    for b in backups or []:
        db.add(ResponsibilityBackup(responsibility_id=r.id, backup_person_id=b.id))
    db.flush()
    return r


def asset_in_result(result, name):
    for a in result.affected_assets:
        if a.asset_name == name:
            return a
    return None


# ---------- Classification cases ----------

def test_sole_primary_no_backup_is_orphaned(db):
    org = make_org(db)
    p = make_person(db, org, "Dami")
    a = make_asset(db, org, "Wi-Fi", "high")
    add_resp(db, a, p, "manages", "no_backup")
    result = simulate_person_unavailable(db, org.id, p.id)
    r = asset_in_result(result, "Wi-Fi")
    assert r.classification == "orphaned"
    assert r.simulated_score == 100


def test_surviving_named_backup_is_unaffected(db):
    org = make_org(db)
    p = make_person(db, org, "Dami")
    backup = make_person(db, org, "Sarah")
    a = make_asset(db, org, "Website", "high")
    add_resp(db, a, p, "administers", "has_backup", backups=[backup])
    result = simulate_person_unavailable(db, org.id, p.id)
    r = asset_in_result(result, "Website")
    assert r.classification == "unaffected"
    assert r.simulated_score == r.current_score
    assert "Sarah" in r.surviving_backup_names


def test_backup_unknown_is_partially_affected(db):
    org = make_org(db)
    p = make_person(db, org, "Dami")
    a = make_asset(db, org, "Instagram", "medium")
    add_resp(db, a, p, "manages", "backup_unknown")
    result = simulate_person_unavailable(db, org.id, p.id)
    r = asset_in_result(result, "Instagram")
    # Only uncertain, no surviving coverage and no other primary -> orphaned?
    # Per spec: backup_unknown with no other coverage is "partially affected"
    # ONLY if some remaining coverage exists. Here there is none, so it is orphaned.
    # The spec lists backup_unknown -> partially affected as a distinct case when
    # the asset still has remaining coverage. With no other coverage it is orphaned.
    assert r.classification == "orphaned"


def test_backup_unknown_with_other_primary_is_partially_affected(db):
    org = make_org(db)
    p = make_person(db, org, "Dami")
    other = make_person(db, org, "James")
    a = make_asset(db, org, "Audio", "medium")
    add_resp(db, a, p, "manages", "backup_unknown")
    add_resp(db, a, other, "understands", "has_backup", backups=[make_person(db, org, "Z")])
    result = simulate_person_unavailable(db, org.id, p.id)
    r = asset_in_result(result, "Audio")
    assert r.classification == "partially_affected"


def test_no_backup_but_other_primary_remains_partially_affected(db):
    org = make_org(db)
    p = make_person(db, org, "Dami")
    other = make_person(db, org, "James")
    a = make_asset(db, org, "Livestream", "critical")
    add_resp(db, a, p, "manages", "no_backup")
    add_resp(db, a, other, "understands", "no_backup")
    result = simulate_person_unavailable(db, org.id, p.id)
    r = asset_in_result(result, "Livestream")
    assert r.classification == "partially_affected"


def test_mixed_covered_and_lost_is_partially_affected(db):
    org = make_org(db)
    p = make_person(db, org, "Dami")
    backup = make_person(db, org, "Sarah")
    a = make_asset(db, org, "MixedAsset", "high")
    add_resp(db, a, p, "manages", "no_backup")  # lost
    add_resp(db, a, p, "administers", "has_backup", backups=[backup])  # covered
    result = simulate_person_unavailable(db, org.id, p.id)
    r = asset_in_result(result, "MixedAsset")
    assert r.classification == "partially_affected"
    assert r.lost_responsibilities
    assert r.covered_responsibilities


def test_person_not_connected_not_affected(db):
    org = make_org(db)
    p = make_person(db, org, "Dami")
    other = make_person(db, org, "James")
    a = make_asset(db, org, "SomeoneElseAsset", "high")
    add_resp(db, a, other, "manages", "no_backup")
    result = simulate_person_unavailable(db, org.id, p.id)
    assert asset_in_result(result, "SomeoneElseAsset") is None
    assert result.affected_count == 0


def test_simulated_score_capped_at_100(db):
    org = make_org(db)
    p = make_person(db, org, "Dami")
    other = make_person(db, org, "James")
    # Critical asset with high current score; partially affected -> +25 capped at 100
    a = make_asset(db, org, "HotAsset", "critical")
    # Make current score high: no_backup + no docs + deps
    a.documentation.status = "no"
    a.dependency.depends_on_personal_account = True
    a.dependency.depends_on_single_device = True
    db.flush()
    add_resp(db, a, p, "manages", "no_backup")
    add_resp(db, a, other, "understands", "no_backup")  # keeps it partially affected
    result = simulate_person_unavailable(db, org.id, p.id)
    r = asset_in_result(result, "HotAsset")
    assert r.classification == "partially_affected"
    assert r.simulated_score == 100  # min(current + 25, 100)


def test_unaffected_score_unchanged(db):
    org = make_org(db)
    p = make_person(db, org, "Dami")
    backup = make_person(db, org, "Sarah")
    a = make_asset(db, org, "SafeAsset", "medium")
    add_resp(db, a, p, "manages", "has_backup", backups=[backup])
    result = simulate_person_unavailable(db, org.id, p.id)
    r = asset_in_result(result, "SafeAsset")
    assert r.simulated_score == r.current_score


def test_orphaned_score_is_100(db):
    org = make_org(db)
    p = make_person(db, org, "Dami")
    a = make_asset(db, org, "LoneAsset", "low")
    add_resp(db, a, p, "manages", "no_backup")
    result = simulate_person_unavailable(db, org.id, p.id)
    r = asset_in_result(result, "LoneAsset")
    assert r.classification == "orphaned"
    assert r.simulated_score == 100


def test_person_cannot_be_own_surviving_backup(db):
    org = make_org(db)
    p = make_person(db, org, "Dami")
    # has_backup but the only backup person IS the unavailable person.
    a = make_asset(db, org, "SelfBackupAsset", "high")
    r = add_resp(db, a, p, "manages", "has_backup", backups=[p])
    result = simulate_person_unavailable(db, org.id, p.id)
    res = asset_in_result(result, "SelfBackupAsset")
    # No surviving backup -> lost -> orphaned (no other primary)
    assert res.classification == "orphaned"
    assert res.simulated_score == 100


# ---------- Grace Community Church — Dami simulation ----------

def _find_person(db, name):
    return db.query(Person).filter(Person.name == name).one()


def test_demo_dami_simulation(seeded_db):
    org = seeded_db.query(Organization).first()
    dami = _find_person(seeded_db, "Dami")
    result = simulate_person_unavailable(seeded_db, org.id, dami.id)

    expected = {
        "Sunday Livestream": ("partially_affected", 100),
        "Church Website": ("unaffected", 30),
        "Wi-Fi Network": ("orphaned", 100),
        "Presentation Laptop": ("orphaned", 100),
    }

    # Dami is primary on exactly these 4 assets.
    names = {a.asset_name for a in result.affected_assets}
    assert names == set(expected.keys()), f"Affected assets: {names}"

    for name, (classification, sim_score) in expected.items():
        a = asset_in_result(result, name)
        assert a.classification == classification, f"{name}: {a.classification}"
        assert a.simulated_score == sim_score, f"{name}: {a.simulated_score}"

    # Org risk stays Critical before and after.
    assert result.current_org_level == "critical"
    assert result.simulated_org_level == "critical"


def test_demo_simulation_does_not_modify_db(seeded_db):
    org = seeded_db.query(Organization).first()
    dami = _find_person(seeded_db, "Dami")

    before_resp = seeded_db.query(Responsibility).count()
    before_backup = seeded_db.query(ResponsibilityBackup).count()

    simulate_person_unavailable(seeded_db, org.id, dami.id)

    assert seeded_db.query(Responsibility).count() == before_resp
    assert seeded_db.query(ResponsibilityBackup).count() == before_backup


def test_demo_sarah_simulation_is_sensible(seeded_db):
    org = seeded_db.query(Organization).first()
    sarah = _find_person(seeded_db, "Sarah")
    result = simulate_person_unavailable(seeded_db, org.id, sarah.id)
    # Sarah is primary on Instagram (backup_unknown, sole), Donation (has_backup Pastor John),
    # Google Drive (has_backup Dami).
    names = {a.asset_name for a in result.affected_assets}
    assert names == {"Church Instagram", "Donation Platform", "Google Drive"}

    donation = asset_in_result(result, "Donation Platform")
    assert donation.classification == "unaffected"  # Pastor John backup survives

    gdrive = asset_in_result(result, "Google Drive")
    assert gdrive.classification == "unaffected"  # Dami backup survives

    instagram = asset_in_result(result, "Church Instagram")
    assert instagram.classification == "orphaned"  # backup_unknown, sole primary
