"""Amazon Bedrock AI service (design §8).

Thin, configurable wrapper around Bedrock via boto3. Two use cases:
  1. interpret_interview_answers  — natural-language interview -> ProposedRecords
  2. generate_recommendations     — risk profile -> list[Recommendation]

Both raise AIError on any failure (disabled, unavailable, permission/model
error, malformed output, invalid enums) so callers fall back to the non-AI
path. The model ID is read from configuration and never hard-coded as
mandatory. The application must remain fully usable without Bedrock.
"""

import json

from app.config import settings
from app.models.asset import ASSET_CATEGORIES, CRITICALITY_LEVELS
from app.models.asset_documentation import DOCUMENTATION_STATUSES
from app.models.responsibility import BACKUP_STATUSES, RESPONSIBILITY_TYPES
from app.schemas.interview import ProposedRecords, ProposedResponsibility
from app.schemas.recommendation import Recommendation

PRIORITIES = ("critical", "high", "medium", "low")


class AIError(Exception):
    """Raised when the AI path cannot produce a valid result. Callers fall back."""


# --- System prompts ---

INTERVIEW_SYSTEM_PROMPT = (
    "You are a continuity-planning assistant for a small community organization. "
    "Extract structured technology dependency information from the user's plain-language "
    "answer about one category of technology.\n"
    "RULES:\n"
    "- Never request or output passwords, API keys, tokens, Wi-Fi passwords, recovery "
    "codes, or any credential. If the user mentions one, omit it.\n"
    f"- responsibility_type must be one of: {', '.join(RESPONSIBILITY_TYPES)}.\n"
    f"- backup_status must be one of: {', '.join(BACKUP_STATUSES)}. Use 'backup_unknown' "
    "when coverage is unclear.\n"
    f"- documentation_status must be one of: {', '.join(DOCUMENTATION_STATUSES)}. Use "
    "'unknown' when documentation status is unclear.\n"
    "- Default asset_criticality to 'medium'.\n"
    f"- asset_category must be the provided category key.\n"
    "- Return ONLY a JSON object with keys: asset_name, asset_category, asset_criticality, "
    "asset_description, people (list of {name, role_title}), responsibilities (list of "
    "{primary_person_name, responsibility_type, backup_status, backup_people_names}), "
    "documentation_status, documentation_location, depends_on_personal_account (bool), "
    "depends_on_single_device (bool). No prose, no code fences."
)

RECOMMENDATION_SYSTEM_PROMPT = (
    "You are a continuity-planning assistant for a small community organization. "
    "Given a risk profile, produce specific, practical recommendations to reduce "
    "technology dependency risks.\n"
    "RULES:\n"
    "- Each recommendation must reference a specific asset by name, and a person by name "
    "when relevant.\n"
    "- Be specific and actionable (e.g., 'Train James to operate the Sunday Livestream so "
    "Dami is not the only person who can run it'), never generic like 'improve redundancy'.\n"
    "- Never reference passwords, keys, tokens, or credentials.\n"
    f"- priority must be one of: {', '.join(PRIORITIES)}. Order Critical/High first.\n"
    "- Return ONLY a JSON array; each item has keys: priority, asset_name, person_name "
    "(or null), risk_description, recommendation, rationale. No prose, no code fences."
)


def _get_client():
    """Create a Bedrock runtime client. Raises AIError if unavailable."""
    try:
        import boto3  # imported lazily so the app runs without AWS libs configured
        return boto3.client("bedrock-runtime", region_name=settings.BEDROCK_REGION)
    except Exception as e:  # noqa: BLE001
        raise AIError(f"Bedrock client unavailable: {e}") from e


def _invoke_model(system_prompt: str, user_content: str) -> str:
    """Invoke the configured Bedrock model and return the text output.

    Uses the Anthropic Messages format on Bedrock. Raises AIError on any failure.
    """
    if not settings.AI_ENABLED:
        raise AIError("AI is disabled")

    client = _get_client()
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1500,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_content}],
    }
    try:
        response = client.invoke_model(
            modelId=settings.BEDROCK_MODEL_ID,
            body=json.dumps(body),
        )
        payload = json.loads(response["body"].read())
        # Anthropic Messages response shape: {"content": [{"type": "text", "text": "..."}]}
        return payload["content"][0]["text"]
    except AIError:
        raise
    except Exception as e:  # noqa: BLE001
        raise AIError(f"Bedrock invocation failed: {e}") from e


def _parse_json(text: str):
    """Parse JSON from model text, tolerating surrounding whitespace/code fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # strip a leading ```json / ``` fence and trailing fence
        cleaned = cleaned.split("```", 2)
        cleaned = cleaned[1] if len(cleaned) > 1 else cleaned[0]
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip().rstrip("`").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise AIError(f"Malformed JSON from model: {e}") from e


# --- Use case 1: interview interpretation ---

def interpret_interview_answers(category_key: str, answers: dict) -> ProposedRecords:
    """Interpret a natural-language interview answer into ProposedRecords.

    Raises AIError on any failure so the caller falls back to structured mapping.
    The caller is responsible for running secret validation BEFORE calling this.
    """
    free_text = answers.get("free_text") or answers.get("narrative") or ""
    user_content = (
        f"Category key: {category_key}\n"
        f"User's answer: {free_text}\n"
        "Extract the structured records as specified."
    )
    raw = _invoke_model(INTERVIEW_SYSTEM_PROMPT, user_content)
    data = _parse_json(raw)
    return _validate_proposed_records(category_key, data)


def _validate_proposed_records(category_key: str, data: dict) -> ProposedRecords:
    if not isinstance(data, dict):
        raise AIError("Interview output is not an object")

    asset_name = (data.get("asset_name") or "").strip()
    if not asset_name:
        raise AIError("Missing asset_name")

    asset_category = data.get("asset_category") or category_key
    if asset_category not in ASSET_CATEGORIES:
        asset_category = category_key if category_key in ASSET_CATEGORIES else "other"

    criticality = data.get("asset_criticality") or "medium"
    if criticality not in CRITICALITY_LEVELS:
        raise AIError(f"Invalid criticality: {criticality}")

    doc_status = data.get("documentation_status") or "unknown"
    if doc_status not in DOCUMENTATION_STATUSES:
        raise AIError(f"Invalid documentation_status: {doc_status}")

    responsibilities = []
    for r in data.get("responsibilities") or []:
        rtype = r.get("responsibility_type")
        bstatus = r.get("backup_status")
        if rtype not in RESPONSIBILITY_TYPES:
            raise AIError(f"Invalid responsibility_type: {rtype}")
        if bstatus not in BACKUP_STATUSES:
            raise AIError(f"Invalid backup_status: {bstatus}")
        responsibilities.append(
            ProposedResponsibility(
                primary_person_name=(r.get("primary_person_name") or "").strip(),
                responsibility_type=rtype,
                backup_status=bstatus,
                backup_people_names=[n for n in (r.get("backup_people_names") or []) if n],
            )
        )
    if not responsibilities:
        raise AIError("No valid responsibilities in interview output")

    return ProposedRecords(
        category_key=category_key,
        asset_name=asset_name,
        asset_category=asset_category,
        asset_criticality=criticality,
        asset_description=(data.get("asset_description") or None),
        people=[p for p in (data.get("people") or []) if p.get("name")],
        responsibilities=responsibilities,
        documentation_status=doc_status,
        documentation_location=(data.get("documentation_location") or None),
        depends_on_personal_account=bool(data.get("depends_on_personal_account")),
        depends_on_single_device=bool(data.get("depends_on_single_device")),
    )


# --- Use case 2: recommendations ---

def generate_recommendations(risk_profile: dict) -> list[Recommendation]:
    """Generate recommendations from a secret-free risk profile.

    Raises AIError on any failure so the caller falls back to rule-based output.
    """
    user_content = json.dumps(risk_profile)
    raw = _invoke_model(RECOMMENDATION_SYSTEM_PROMPT, user_content)
    data = _parse_json(raw)
    if not isinstance(data, list):
        raise AIError("Recommendation output is not a list")

    recommendations = []
    for item in data:
        priority = item.get("priority")
        if priority not in PRIORITIES:
            raise AIError(f"Invalid priority: {priority}")
        asset_name = (item.get("asset_name") or "").strip()
        if not asset_name:
            raise AIError("Recommendation missing asset_name")
        recommendations.append(
            Recommendation(
                priority=priority,
                asset_name=asset_name,
                person_name=(item.get("person_name") or None),
                risk_description=(item.get("risk_description") or "").strip(),
                recommendation=(item.get("recommendation") or "").strip(),
                rationale=(item.get("rationale") or "").strip(),
            )
        )
    if not recommendations:
        raise AIError("No valid recommendations in output")
    return recommendations
