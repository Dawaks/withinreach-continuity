"""Tests for the deterministic risk scoring engine (design §4)."""

from app.models import (
    Asset,
    AssetDependency,
    AssetDocumentation,
    Organization,
    Person,
    Responsibility,
    ResponsibilityBackup,
)
from app.services.risk_scoring import calculate_asset_risk, calculate_org_risk


# ---------- Helpers for building ad-hoc assets in memory ----------

def make_asset(db, criticality="medium", name="Test Asset", category="other"):
    org = db.query(Organization).first()
    if org is None:
        org = Organization(name="Test Org", org_type="other")
        db.add(org)
        db.flush()
    asset = Asset(
        organization_id=org.id,
        name=name,
        category=category,
        criticality=criticality,
        description=None,
    )
    db.add(asset)
    db.flush()
    return asset


def make_person(db, name):
    org = db.query(Organization).first()
    p = Person(organization_id=org.id, name=name)
    db.add(p)
    db.flush()
    return p


def add_responsibility(db, asset, person, resp_type, backup_status, backups=None):
    r = Responsibility(
        asset_id=asset.id,
        primary_person_id=person.id,
        responsibility_type=resp_type,
        backup_status=backup_status,
    )
    db.add(r)
    db.flush()
    for b in backups or []:
        db.add(ResponsibilityBackup(responsibility_id=r.id, backup_person_id=b.id))
    db.flush()
    return r


def set_docs(db, asset, status):
    d = AssetDocumentation(asset_id=asset.id, status=status)
    db.add(d)
    db.flush()
    return d


def set_deps(db, asset, personal=False, device=False):
    dep = AssetDependency(
        asset_id=asset.id,
        depends_on_personal_account=personal,
        depends_on_single_device=device,
    )
    db.add(dep)
    db.flush()
    return dep


def score_asset(db, asset):
    return calculate_asset_risk(
        asset, asset.responsibilities, asset.documentation, asset.dependency
    )


# ---------- Per-asset scoring cases ----------

def test_critical_no_backup_no_docs_all_deps(db):
    asset = make_asset(db, "critical")
    person = make_person(db, "Dami")
    add_responsibility(db, asset, person, "manages", "no_backup")
    set_docs(db, asset, "no")
    set_deps(db, asset, personal=True, device=True)
    result = score_asset(db, asset)
    # 45 + 15 + 15 + 15 + 10 = 100
    assert result.score == 100
    assert result.risk_level == "critical"


def test_low_full_coverage(db):
    asset = make_asset(db, "low")
    primary = make_person(db, "Sarah")
    backup = make_person(db, "James")
    add_responsibility(db, asset, primary, "manages", "has_backup", backups=[backup])
    set_docs(db, asset, "yes")
    set_deps(db, asset, personal=False, device=False)
    result = score_asset(db, asset)
    # 8 + 0 + 0 + 0 + 0 = 8
    assert result.score == 8
    assert result.risk_level == "low"


def test_high_backup_unknown_no_docs(db):
    asset = make_asset(db, "high")
    person = make_person(db, "Dami")
    add_responsibility(db, asset, person, "manages", "backup_unknown")
    set_docs(db, asset, "no")
    set_deps(db, asset)
    result = score_asset(db, asset)
    # 30 + 7 + 15 = 52
    assert result.score == 52
    assert result.risk_level == "high"


def test_critical_full_coverage(db):
    asset = make_asset(db, "critical")
    primary = make_person(db, "Dami")
    backup = make_person(db, "Sarah")
    add_responsibility(db, asset, primary, "manages", "has_backup", backups=[backup])
    set_docs(db, asset, "yes")
    set_deps(db, asset)
    result = score_asset(db, asset)
    # 45 + 0 + 0 = 45 -> Medium
    assert result.score == 45
    assert result.risk_level == "medium"


def test_medium_no_backup_single_device(db):
    asset = make_asset(db, "medium")
    person = make_person(db, "Dami")
    add_responsibility(db, asset, person, "manages", "no_backup")
    set_docs(db, asset, "no")
    set_deps(db, asset, device=True)
    result = score_asset(db, asset)
    # 18 + 15 + 15 + 10 = 58 -> High
    assert result.score == 58
    assert result.risk_level == "high"


def test_backup_penalty_cap_at_30(db):
    asset = make_asset(db, "low")  # base 8
    p1 = make_person(db, "A")
    p2 = make_person(db, "B")
    p3 = make_person(db, "C")
    add_responsibility(db, asset, p1, "manages", "no_backup")
    add_responsibility(db, asset, p2, "understands", "no_backup")
    add_responsibility(db, asset, p3, "administers", "no_backup")
    set_docs(db, asset, "yes")
    set_deps(db, asset)
    result = score_asset(db, asset)
    # 3 x 15 = 45 backup penalty, capped at 30. 8 + 30 = 38
    assert result.score == 38
    # Displayed backup factor points should sum to the cap (30)
    backup_points = sum(
        f.points for f in result.contributing_factors if "backup" in f.label.lower()
    )
    assert backup_points == 30


def test_score_capped_at_100(db):
    asset = make_asset(db, "critical")  # base 45
    p1 = make_person(db, "A")
    p2 = make_person(db, "B")
    add_responsibility(db, asset, p1, "manages", "no_backup")
    add_responsibility(db, asset, p2, "administers", "no_backup")
    set_docs(db, asset, "no")
    set_deps(db, asset, personal=True, device=True)
    result = score_asset(db, asset)
    # 45 + 30(cap) + 15 + 15 + 10 = 115 -> capped at 100
    assert result.score == 100
    assert result.risk_level == "critical"


def test_risk_thresholds(db):
    # Build assets whose raw scores land exactly on boundaries using criticality + docs.
    # Low boundary: score 24 -> low, 25 -> medium
    # We use base + single doc/dep combinations.

    # score 24 (low): medium base 18 + unknown docs 7 = 25 -> that's medium.
    # Instead verify via direct level mapping of known cases:
    from app.services.risk_scoring import _risk_level_from_score
    assert _risk_level_from_score(0) == "low"
    assert _risk_level_from_score(24) == "low"
    assert _risk_level_from_score(25) == "medium"
    assert _risk_level_from_score(49) == "medium"
    assert _risk_level_from_score(50) == "high"
    assert _risk_level_from_score(74) == "high"
    assert _risk_level_from_score(75) == "critical"
    assert _risk_level_from_score(100) == "critical"


def test_contributing_factors_output(db):
    asset = make_asset(db, "critical")
    person = make_person(db, "Dami")
    add_responsibility(db, asset, person, "manages", "no_backup")
    set_docs(db, asset, "no")
    set_deps(db, asset, device=True)
    result = score_asset(db, asset)
    labels = [f.label for f in result.contributing_factors]
    # Base criticality factor present
    assert any("Critical asset" == l for l in labels)
    # Backup factor references the person and responsibility
    assert any("Dami" in l and "backup" in l.lower() for l in labels)
    # Documentation and single-device factors present
    assert any("No documentation" == l for l in labels)
    assert any("single device" in l.lower() for l in labels)
    # Each factor has points and a detail
    for f in result.contributing_factors:
        assert f.points >= 0
        assert f.detail


# ---------- Organization aggregation ----------

def _org_with_criticalities(db, specs):
    """Create assets that will land at given risk levels.

    specs: list of target levels. We engineer each asset to reach the level.
    """
    org = Organization(name="Agg Org", org_type="other")
    db.add(org)
    db.flush()
    for i, level in enumerate(specs):
        if level == "critical":
            crit, docs, personal, device, backup = "critical", "no", True, True, "no_backup"
        elif level == "high":
            crit, docs, personal, device, backup = "high", "no", False, False, "backup_unknown"
        elif level == "medium":
            # medium base 18 + no documentation 15 = 33 -> Medium band (25-49)
            crit, docs, personal, device, backup = "medium", "no", False, False, "has_backup"
        else:  # low
            crit, docs, personal, device, backup = "low", "yes", False, False, "has_backup"
        asset = Asset(organization_id=org.id, name=f"A{i}", category="other", criticality=crit)
        db.add(asset)
        db.flush()
        p = Person(organization_id=org.id, name=f"P{i}")
        db.add(p)
        db.flush()
        backups = []
        if backup == "has_backup":
            b = Person(organization_id=org.id, name=f"B{i}")
            db.add(b)
            db.flush()
            backups = [b]
        r = Responsibility(asset_id=asset.id, primary_person_id=p.id,
                           responsibility_type="manages", backup_status=backup)
        db.add(r)
        db.flush()
        for bk in backups:
            db.add(ResponsibilityBackup(responsibility_id=r.id, backup_person_id=bk.id))
        db.add(AssetDocumentation(asset_id=asset.id, status=docs))
        db.add(AssetDependency(asset_id=asset.id, depends_on_personal_account=personal,
                               depends_on_single_device=device))
        db.flush()
    return org


def test_org_one_critical(db):
    org = _org_with_criticalities(db, ["critical", "medium", "low"])
    result = calculate_org_risk(db, org.id)
    assert result.risk_level == "critical"
    assert result.score_distribution["critical"] == 1


def test_org_three_high_no_critical(db):
    org = _org_with_criticalities(db, ["high", "high", "high"])
    result = calculate_org_risk(db, org.id)
    assert result.score_distribution["critical"] == 0
    assert result.score_distribution["high"] == 3
    assert result.risk_level == "critical"


def test_org_one_high(db):
    org = _org_with_criticalities(db, ["high", "medium", "low"])
    result = calculate_org_risk(db, org.id)
    assert result.risk_level == "high"


def test_org_one_medium(db):
    org = _org_with_criticalities(db, ["medium", "low"])
    result = calculate_org_risk(db, org.id)
    assert result.risk_level == "medium"


def test_org_all_low(db):
    org = _org_with_criticalities(db, ["low", "low"])
    result = calculate_org_risk(db, org.id)
    assert result.risk_level == "low"


# ---------- Exact Grace Community Church demo scores ----------

EXPECTED_DEMO_SCORES = {
    "Sunday Livestream": (85, "critical"),
    "Church Website": (30, "medium"),
    "Church Instagram": (40, "medium"),
    "Wi-Fi Network": (75, "critical"),
    "Donation Platform": (70, "high"),
    "Google Drive": (30, "medium"),
    "Audio System": (40, "medium"),
    "Presentation Laptop": (58, "high"),
}


def test_demo_exact_scores(seeded_db):
    org = seeded_db.query(Organization).first()
    result = calculate_org_risk(seeded_db, org.id)
    by_name = {r.asset_name: r for r in result.asset_risks}
    for name, (score, level) in EXPECTED_DEMO_SCORES.items():
        assert by_name[name].score == score, f"{name}: got {by_name[name].score}, expected {score}"
        assert by_name[name].risk_level == level, f"{name}: got {by_name[name].risk_level}, expected {level}"


def test_demo_distribution_and_org_risk(seeded_db):
    org = seeded_db.query(Organization).first()
    result = calculate_org_risk(seeded_db, org.id)
    assert result.score_distribution == {"critical": 2, "high": 2, "medium": 4, "low": 0}
    assert result.risk_level == "critical"


def test_demo_top_three(seeded_db):
    org = seeded_db.query(Organization).first()
    result = calculate_org_risk(seeded_db, org.id)
    top = [(r.asset_name, r.score) for r in result.top_risks]
    assert top == [
        ("Sunday Livestream", 85),
        ("Wi-Fi Network", 75),
        ("Donation Platform", 70),
    ]
