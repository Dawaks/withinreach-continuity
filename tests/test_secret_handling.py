"""Tests for the blocking secret-detection boundary (design §9)."""

from app.security import secret_check


def test_password_value_blocked():
    assert secret_check.check_for_secrets("the password is hunter2").blocked


def test_wifi_password_value_blocked():
    assert secret_check.check_for_secrets("Wi-Fi password: abc123").blocked


def test_api_key_value_blocked():
    assert secret_check.check_for_secrets("API key = xyz789").blocked


def test_token_value_blocked():
    assert secret_check.check_for_secrets("token: abc").blocked


def test_benign_password_mention_allowed():
    assert not secret_check.check_for_secrets(
        "Password reset procedure is in the IT binder."
    ).blocked


def test_no_keyword_allowed():
    assert not secret_check.check_for_secrets("Google Drive > IT folder").blocked


def test_empty_allowed():
    assert not secret_check.check_for_secrets("").blocked
    assert not secret_check.check_for_secrets(None).blocked


def test_validate_free_text_fields_reports_offending_field():
    result = secret_check.validate_free_text_fields(
        {
            "location": "Google Drive > IT folder",
            "note": "the password is hunter2",
        }
    )
    assert result.valid is False
    assert "note" in result.errors
    assert "location" not in result.errors
    assert result.errors["note"] == secret_check.USER_MESSAGE


def test_validate_free_text_fields_all_clean():
    result = secret_check.validate_free_text_fields(
        {"a": "office laptop", "b": "registered under a personal email"}
    )
    assert result.valid is True
    assert result.errors == {}
