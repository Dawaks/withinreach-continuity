"""Tests for AI integration and graceful fallback (Phase 9). Bedrock is mocked."""

import json

import pytest

from app.models import Organization
from app.services import ai_service, interview_service, recommendation_service
from app.services.ai_service import AIError


# ---------- Helpers ----------

VALID_INTERVIEW_JSON = {
    "asset_name": "Sunday Livestream",
    "asset_category": "livestream",
    "asset_criticality": "medium",
    "asset_description": "Weekly livestream",
    "people": [{"name": "Dami", "role_title": "Technology Coordinator"}],
    "responsibilities": [
        {
            "primary_person_name": "Dami",
            "responsibility_type": "manages",
            "backup_status": "backup_unknown",
            "backup_people_names": [],
        }
    ],
    "documentation_status": "no",
    "documentation_location": None,
    "depends_on_personal_account": False,
    "depends_on_single_device": True,
}

VALID_REC_JSON = [
    {
        "priority": "critical",
        "asset_name": "Sunday Livestream",
        "person_name": "Dami",
        "risk_description": "Only Dami can run it",
        "recommendation": "Train James to operate the Sunday Livestream.",
        "rationale": "Removes a single point of failure.",
    }
]

NARRATIVE = {
    "free_text": (
        "Dami normally runs the livestream every Sunday. James knows some of it but "
        "cannot fully take over. There are no written instructions and everything is "
        "done from the sound booth laptop."
    )
}


def enable_ai(monkeypatch):
    monkeypatch.setattr(ai_service.settings, "AI_ENABLED", True)
    monkeypatch.setattr(interview_service.settings, "AI_ENABLED", True)
    monkeypatch.setattr(recommendation_service.settings, "AI_ENABLED", True)


def disable_ai(monkeypatch):
    monkeypatch.setattr(ai_service.settings, "AI_ENABLED", False)
    monkeypatch.setattr(interview_service.settings, "AI_ENABLED", False)
    monkeypatch.setattr(recommendation_service.settings, "AI_ENABLED", False)


# ---------- AI disabled -> fallback ----------

def test_interview_fallback_when_ai_disabled(monkeypatch):
    disable_ai(monkeypatch)
    # structured answers (not narrative) should map directly
    answers = {
        "uses": "yes", "asset_name": "A", "person_name": "P",
        "backup": "no", "docs": "no",
    }
    result = interview_service.interpret_answers("website", answers, ai_enabled=False)
    assert result is not None
    assert result.asset_name == "A"


def test_recommendations_fallback_when_ai_disabled(monkeypatch, seeded_db):
    disable_ai(monkeypatch)
    org = seeded_db.query(Organization).first()
    mode, recs = recommendation_service.get_recommendations(seeded_db, org.id)
    assert mode == "rule_based"
    assert recs


# ---------- Bedrock exception -> fallback ----------

def test_interview_fallback_on_bedrock_exception(monkeypatch):
    enable_ai(monkeypatch)
    monkeypatch.setattr(ai_service, "_invoke_model", lambda *a, **k: (_ for _ in ()).throw(AIError("boom")))
    answers = {"uses": "yes", "asset_name": "A", "person_name": "P", "backup": "no", "docs": "no"}
    result = interview_service.interpret_answers("website", answers, ai_enabled=True)
    assert result is not None  # fell back to structured mapping
    assert result.asset_name == "A"


def test_recommendations_fallback_on_bedrock_exception(monkeypatch, seeded_db):
    enable_ai(monkeypatch)
    monkeypatch.setattr(ai_service, "_invoke_model", lambda *a, **k: (_ for _ in ()).throw(AIError("boom")))
    org = seeded_db.query(Organization).first()
    mode, recs = recommendation_service.get_recommendations(seeded_db, org.id)
    assert mode == "rule_based"
    assert recs


# ---------- Malformed / invalid output -> fallback ----------

def test_interview_malformed_json_falls_back(monkeypatch):
    enable_ai(monkeypatch)
    monkeypatch.setattr(ai_service, "_invoke_model", lambda *a, **k: "not json at all")
    answers = {"uses": "yes", "asset_name": "A", "person_name": "P", "backup": "no", "docs": "no"}
    result = interview_service.interpret_answers("website", answers, ai_enabled=True)
    assert result.asset_name == "A"  # structured fallback used


def test_interview_invalid_enum_falls_back(monkeypatch):
    enable_ai(monkeypatch)
    bad = dict(VALID_INTERVIEW_JSON)
    bad["responsibilities"] = [dict(VALID_INTERVIEW_JSON["responsibilities"][0], responsibility_type="bogus")]
    monkeypatch.setattr(ai_service, "_invoke_model", lambda *a, **k: json.dumps(bad))
    answers = {"uses": "yes", "asset_name": "Fallback Asset", "person_name": "P", "backup": "no", "docs": "no"}
    result = interview_service.interpret_answers("website", answers, ai_enabled=True)
    assert result.asset_name == "Fallback Asset"  # fell back, not the AI value


def test_recommendations_malformed_json_falls_back(monkeypatch, seeded_db):
    enable_ai(monkeypatch)
    monkeypatch.setattr(ai_service, "_invoke_model", lambda *a, **k: "{ not valid")
    org = seeded_db.query(Organization).first()
    mode, recs = recommendation_service.get_recommendations(seeded_db, org.id)
    assert mode == "rule_based"


def test_recommendations_invalid_priority_falls_back(monkeypatch, seeded_db):
    enable_ai(monkeypatch)
    bad = [dict(VALID_REC_JSON[0], priority="urgent")]
    monkeypatch.setattr(ai_service, "_invoke_model", lambda *a, **k: json.dumps(bad))
    org = seeded_db.query(Organization).first()
    mode, recs = recommendation_service.get_recommendations(seeded_db, org.id)
    assert mode == "rule_based"


# ---------- Secret blocks BEFORE Bedrock ----------

def test_secret_blocks_before_bedrock(monkeypatch):
    enable_ai(monkeypatch)
    calls = {"n": 0}

    def spy(*a, **k):
        calls["n"] += 1
        return json.dumps(VALID_INTERVIEW_JSON)

    monkeypatch.setattr(ai_service, "_invoke_model", spy)
    answers = {
        "uses": "yes",
        "asset_name": "A",
        "free_text": "the wifi password is hunter2",
    }
    with pytest.raises(interview_service.SecretBlockedError):
        interview_service.interpret_answers("website", answers, ai_enabled=True)
    assert calls["n"] == 0  # Bedrock was never called


def test_benign_answer_reaches_ai(monkeypatch):
    enable_ai(monkeypatch)
    calls = {"n": 0}

    def spy(system, user):
        calls["n"] += 1
        # The secret must never appear; benign text is fine.
        assert "hunter2" not in user
        return json.dumps(VALID_INTERVIEW_JSON)

    monkeypatch.setattr(ai_service, "_invoke_model", spy)
    answers = {
        "uses": "yes",
        "free_text": "Dami runs the livestream from the sound booth laptop.",
    }
    result = interview_service.interpret_answers("livestream", answers, ai_enabled=True)
    assert calls["n"] == 1
    assert result.asset_name == "Sunday Livestream"  # AI result used


# ---------- Valid AI output validates ----------

def test_valid_ai_interview_validates(monkeypatch):
    enable_ai(monkeypatch)
    monkeypatch.setattr(ai_service, "_invoke_model", lambda *a, **k: json.dumps(VALID_INTERVIEW_JSON))
    result = interview_service.interpret_answers("livestream", NARRATIVE, ai_enabled=True)
    assert result.asset_name == "Sunday Livestream"
    assert result.responsibilities[0].backup_status == "backup_unknown"
    assert result.depends_on_single_device is True


def test_valid_ai_recommendations_validate(monkeypatch, seeded_db):
    enable_ai(monkeypatch)
    monkeypatch.setattr(ai_service, "_invoke_model", lambda *a, **k: json.dumps(VALID_REC_JSON))
    org = seeded_db.query(Organization).first()
    mode, recs = recommendation_service.get_recommendations(seeded_db, org.id)
    assert mode == "ai"
    assert recs[0].asset_name == "Sunday Livestream"
    assert "Train James" in recs[0].recommendation


# ---------- Rule-based quality ----------

def test_fallback_recommendations_reference_specific_assets(seeded_db):
    org = seeded_db.query(Organization).first()
    profile = recommendation_service.build_risk_profile(seeded_db, org.id)
    recs = recommendation_service._rule_based_recommendations(profile)
    # Every recommendation references a real asset name.
    asset_names = {a["asset_name"] for a in profile["assets"]}
    for r in recs:
        assert r.asset_name in asset_names
    # At least one references Sunday Livestream (a known no-backup critical asset).
    assert any(r.asset_name == "Sunday Livestream" for r in recs)


def test_fallback_recommendations_prioritized(seeded_db):
    org = seeded_db.query(Organization).first()
    mode, recs = recommendation_service.get_recommendations(seeded_db, org.id)
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    priorities = [order[r.priority] for r in recs]
    assert priorities == sorted(priorities)


# ---------- Secret-free payload ----------

def test_risk_profile_has_no_emails_or_secret_fields(seeded_db):
    org = seeded_db.query(Organization).first()
    profile = recommendation_service.build_risk_profile(seeded_db, org.id)
    blob = json.dumps(profile).lower()
    # Demo people have @gracecommunity.example emails — must not appear.
    assert "@" not in blob
    assert "gracecommunity.example" not in blob
    # No secret-ish keys.
    for forbidden in ["password", "token", "api_key", "apikey", "credential", "secret"]:
        assert forbidden not in blob
