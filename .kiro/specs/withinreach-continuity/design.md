# WithinReach Continuity — Design Document

**Status:** Approved requirements → Design phase
**Scope:** Hackathon MVP (Tier 1 features only unless noted)
**Reference:** [requirements.md](./requirements.md)

---

## 1. Application Architecture

### 1.1 Overview

A single-process FastAPI application with server-rendered Jinja2 templates. No microservices, containers, message queues, or background workers. The architecture follows a clean three-layer separation:

```
Browser (Jinja2 + Cytoscape.js)
      │  HTTP (form posts + JSON endpoints)
      ▼
┌─────────────────────────────────────┐
│  Routes (FastAPI routers)            │  ← Request handling, template rendering, JSON responses
│      │                               │
│      ▼                               │
│  Services (business logic)           │  ← Risk scoring, simulation, AI, interview, recommendations
│      │                               │
│      ▼                               │
│  Data / Models (SQLAlchemy + SQLite) │  ← ORM models, DB session
└─────────────────────────────────────┘
      │  boto3 (optional)
      ▼
  Amazon Bedrock (AI)
```

### 1.2 Layer Responsibilities

| Layer | Responsibility | What it does NOT do |
|---|---|---|
| **Routes** | Parse requests, call services, render templates or return JSON. Thin handlers — no business logic. | Does not compute risk scores, does not call Bedrock directly. |
| **Services** | All business logic: CRUD operations, risk scoring, simulation, AI orchestration, interview flow, recommendation generation, secret checking. | Does not render templates, does not define DB schema. |
| **Data / Models** | SQLAlchemy ORM models, database engine, session factory, table definitions. | Does not contain business logic. |

### 1.3 Key Design Decisions

1. **Single-process, no async complexity.** FastAPI runs synchronously for the MVP. The only async call is to Bedrock, which uses `boto3` (synchronous) wrapped in `run_in_executor` or simply called directly — latency is acceptable for a hackathon demo.

2. **SQLite file-based database.** Zero configuration. A single `continuity.db` file in the project root. No database server to install or manage.

3. **Server-rendered templates with progressive enhancement.** Jinja2 renders all pages server-side. JavaScript is used only for: (a) the Cytoscape.js dependency map, (b) AJAX calls for the interview AI interpretation and simulation, and (c) client-side secret-detection feedback (immediate warning before submit — server-side validation is authoritative). Pages work without JavaScript for core flows (form posts with redirects).

4. **Risk scoring is deterministic and server-side.** No AI involvement in scoring. The scoring engine is a pure Python function that takes asset data as input and returns a score plus a breakdown of contributing factors. This makes it testable, explainable, and instant.

5. **AI is an enhancement, not a dependency.** Both the guided interview and the recommendation engine have rule-based fallbacks that work without Bedrock. If Bedrock is down or not configured, the app degrades gracefully.

6. **No authentication for the MVP.** Single shared organization access. The data model includes `organization_id` foreign keys so multi-tenancy can be added later without schema changes, but the MVP uses a single hardcoded organization (the first one created, or the demo seed data).

### 1.4 Request Flow Examples

**Example 1 — Dashboard page:**
```
GET / → routes.pages.dashboard()
  → services.asset_service.count_assets(org_id)
  → services.person_service.count_people(org_id)
  → services.risk_scoring.calculate_org_risk(org_id)
  → render dashboard.html with {org, people_count, asset_count, risk_level, top_risks}
```

**Example 2 — What If simulation (AJAX):**
```
POST /api/simulate  {person_id: 3}
  → services.simulator.simulate_person_unavailable(org_id, person_id)
    → loads all responsibilities where person_id is primary
    → classifies each affected asset (orphaned / partially_affected / unaffected)
    → computes simulated per-asset and org risk scores
  → return JSON {affected_assets[], simulated_org_risk, current_org_risk}
  → JS renders results in the simulator panel
```

**Example 3 — Guided discovery interview (AI-assisted):**
```
POST /api/interview/interpret  {category: "livestream", answers: {...}}
  → services.interview_service.interpret_answers(category, answers)
    → services.secret_check.validate_answers(answers)
      → if likely secret detected: return 400 with user-friendly message, do NOT call Bedrock
    → if AI enabled: services.ai_service.interpret_interview_answers(category, answers)
      → Bedrock call with structured prompt (answers already validated secret-free)
      → parse JSON response → proposed records
    → if AI unavailable: structured_form_fallback(category, answers)
  → return JSON {proposed: {asset, people[], responsibilities[], documentation, dependencies}}
  → JS renders proposed records in review panel
```

---

## 2. Proposed Project Structure

```
withinreach-continuity/
│
├── app/
│   ├── __init__.py
│   ├── main.py                          # FastAPI app creation, middleware, router registration, static mount
│   ├── database.py                      # Engine, SessionLocal, Base, get_db() dependency
│   ├── config.py                        # Settings from env vars (Bedrock model ID, DB path, AI toggle)
│   │
│   ├── models/                          # SQLAlchemy ORM models
│   │   ├── __init__.py                  # Re-export all models
│   │   ├── organization.py
│   │   ├── person.py
│   │   ├── asset.py
│   │   ├── responsibility.py            # Responsibility + ResponsibilityBackup
│   │   ├── asset_documentation.py
│   │   └── asset_dependency.py
│   │
│   ├── schemas/                         # Pydantic schemas (request/response validation)
│   │   ├── __init__.py
│   │   ├── organization.py
│   │   ├── person.py
│   │   ├── asset.py
│   │   ├── responsibility.py
│   │   ├── risk.py                       # AssetRiskResult, OrgRiskResult, SimulationResult
│   │   ├── interview.py                 # InterviewAnswer, ProposedRecords, InterviewQuestion
│   │   └── recommendation.py            # Recommendation, RecommendationRequest
│   │
│   ├── routes/                          # FastAPI routers
│   │   ├── __init__.py
│   │   ├── pages.py                     # Jinja2 page routes (dashboard, people, assets, risk, map, etc.)
│   │   ├── organization.py              # Organization CRUD
│   │   ├── people.py                    # People CRUD
│   │   ├── assets.py                    # Asset CRUD
│   │   ├── responsibilities.py          # Responsibility + backup CRUD
│   │   ├── risk.py                      # Risk score endpoints (JSON)
│   │   ├── simulation.py               # What If simulator (JSON)
│   │   ├── interview.py                # Guided discovery interview (pages + JSON API)
│   │   ├── recommendations.py          # Recommendation generation (JSON)
│   │   └── dependency_map.py           # Graph data endpoint (JSON for Cytoscape)
│   │
│   ├── services/                        # Business logic
│   │   ├── __init__.py
│   │   ├── organization_service.py
│   │   ├── person_service.py
│   │   ├── asset_service.py
│   │   ├── responsibility_service.py
│   │   ├── risk_scoring.py              # Deterministic scoring engine (NO AI)
│   │   ├── simulator.py                # What If simulation logic
│   │   ├── ai_service.py               # Bedrock wrapper (interview + recommendations)
│   │   ├── interview_service.py        # Interview flow, question definitions, AI orchestration
│   │   ├── recommendation_service.py   # AI + rule-based fallback recommendations
│   │   ├── dependency_map_service.py   # Builds Cytoscape graph JSON from DB data
│   │   └── secret_check.py             # Secret detection — BLOCKING before DB save or AI transmission
│   │
│   └── demo/
│       ├── __init__.py
│       └── seed.py                      # Grace Community Church demo data seeder
│
├── templates/                           # Jinja2 templates
│   ├── base.html                        # Base layout: nav bar, CSS includes, flash messages
│   ├── dashboard.html
│   ├── organization_setup.html
│   ├── interview/
│   │   ├── intro.html
│   │   ├── category.html                # Per-category question form
│   │   └── review.html                  # Review proposed records
│   ├── people/
│   │   ├── list.html
│   │   ├── detail.html
│   │   └── form.html                    # Add/edit person
│   ├── assets/
│   │   ├── list.html
│   │   ├── detail.html
│   │   └── form.html                    # Add/edit asset
│   ├── risk/
│   │   └── overview.html
│   ├── dependency_map.html
│   ├── simulator.html
│   └── recommendations.html
│
├── static/
│   ├── css/
│   │   └── style.css                    # Custom styles layered on Pico CSS
│   └── js/
│       └── dependency_map.js            # Cytoscape.js initialization and styling
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                      # Fixtures: in-memory SQLite, test client, seed data
│   ├── test_risk_scoring.py
│   ├── test_backup_relationships.py
│   ├── test_simulator.py
│   ├── test_secret_handling.py
│   └── test_ai_fallback.py
│
├── .env.example                         # Environment variable template
├── requirements.txt
└── README.md
```

### File Purpose Summary

| Path | Purpose |
|---|---|
| `app/main.py` | App factory: create FastAPI, include routers, mount static, configure Jinja2 |
| `app/database.py` | SQLAlchemy engine (`create_engine`), `SessionLocal` factory, `Base`, `get_db()` FastAPI dependency |
| `app/config.py` | Pydantic `Settings` reading from env: `DATABASE_URL`, `BEDROCK_MODEL_ID`, `AI_ENABLED`, `BEDROCK_REGION` |
| `app/models/*.py` | One SQLAlchemy model class per file; `__init__.py` re-exports for easy imports |
| `app/schemas/*.py` | Pydantic models for API request/response validation; keep separate from ORM models |
| `app/routes/pages.py` | All `GET` routes that render Jinja2 templates (thin: call service, pass data to template) |
| `app/routes/*.py` | API routes (`POST`/`GET` returning JSON); thin handlers calling services |
| `app/services/risk_scoring.py` | Pure functions: `calculate_asset_risk(asset, responsibilities, docs, deps) → AssetRiskResult`, `calculate_org_risk(org_id) → OrgRiskResult` |
| `app/services/simulator.py` | `simulate_person_unavailable(org_id, person_id) → SimulationResult` |
| `app/services/ai_service.py` | `interpret_interview_answers(category, answers) → ProposedRecords`, `generate_recommendations(risk_profile) → list[Recommendation]` |
| `app/services/interview_service.py` | Interview category definitions, question templates, flow control, AI orchestration with fallback |
| `app/services/recommendation_service.py` | `get_recommendations(org_id) → list[Recommendation]`; calls AI service, falls back to rule-based |
| `app/services/dependency_map_service.py` | `build_graph_data(org_id) → dict` (nodes + edges for Cytoscape JSON) |
| `app/services/secret_check.py` | `check_for_secrets(text) → SecretCheckResult` (keyword + pattern detection, **blocking** before persistence or AI transmission) |
| `app/demo/seed.py` | `seed_demo_data(db)` — creates Grace Community Church with all demo records |

---

## 3. Database Schema

### 3.1 Overview

Seven tables. SQLite via SQLAlchemy ORM. Risk scores are computed on demand, never stored. The schema is designed so that all risk-relevant data lives in the tables below and can be recalculated at any time.

For the MVP, tables are created with `Base.metadata.create_all(engine)` on startup. No Alembic migrations needed for the hackathon — the schema is small and stable. Alembic can be added post-hackathon for future schema evolution.

### 3.2 ER Diagram (Conceptual)

```
Organization (1)
    │
    ├──< Person (N)
    │       │
    │       │ (primary_person)    (backup_person)
    │       │        │                   │
    │       ▼        ▼                   ▼
    ├──< Asset (N)  ──< Responsibility (N) >──< ResponsibilityBackup (N)
    │       │
    │       ├──1:1── AssetDocumentation
    │       │
    │       └──1:1── AssetDependency
    │
    (org_id FK on Person, Asset)
    (asset_id FK on Responsibility, AssetDocumentation, AssetDependency)
    (primary_person_id FK on Responsibility → Person)
    (responsibility_id FK on ResponsibilityBackup → Responsibility)
    (backup_person_id FK on ResponsibilityBackup → Person)
```

### 3.3 Table Definitions

#### Organization

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | Integer | PK, autoincrement | |
| `name` | String(200) | NOT NULL | e.g., "Grace Community Church" |
| `org_type` | String(50) | NOT NULL, CHECK in set | Enum: `church`, `nonprofit`, `student_org`, `family_business`, `other` |
| `size` | String(100) | nullable | Free text, e.g., "150 members" |
| `description` | Text | nullable | Short org description |
| `created_at` | DateTime | default utcnow | |
| `updated_at` | DateTime | default utcnow, onupdate utcnow | |

**Relationships:** `people` (one-to-many → Person), `assets` (one-to-many → Asset)

#### Person

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | Integer | PK, autoincrement | |
| `organization_id` | Integer | FK → Organization.id, NOT NULL | |
| `name` | String(200) | NOT NULL | Display name |
| `role_title` | String(200) | nullable | e.g., "Technology Coordinator" |
| `email` | String(255) | nullable | Optional contact email — never used for login |
| `created_at` | DateTime | default utcnow | |

**Relationships:** `primary_responsibilities` (one-to-many → Responsibility via `primary_person_id`), `backup_roles` (one-to-many → ResponsibilityBackup via `backup_person_id`)

**Index:** `ix_person_organization_id` on `organization_id`

#### Asset

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | Integer | PK, autoincrement | |
| `organization_id` | Integer | FK → Organization.id, NOT NULL | |
| `name` | String(200) | NOT NULL | e.g., "Sunday Livestream" |
| `category` | String(50) | NOT NULL, CHECK in set | Enum: `livestream`, `website`, `social_media`, `network_wifi`, `data_storage`, `communication`, `payment`, `other` |
| `description` | Text | nullable | What this asset is / does |
| `criticality` | String(20) | NOT NULL, CHECK in set, default `medium` | Enum: `critical`, `high`, `medium`, `low` |
| `created_at` | DateTime | default utcnow | |

**Relationships:** `responsibilities` (one-to-many → Responsibility), `documentation` (one-to-one → AssetDocumentation), `dependency` (one-to-one → AssetDependency)

**Index:** `ix_asset_organization_id` on `organization_id`

#### Responsibility

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | Integer | PK, autoincrement | |
| `asset_id` | Integer | FK → Asset.id, NOT NULL | Cascade delete with asset |
| `primary_person_id` | Integer | FK → Person.id, NOT NULL | The person primarily responsible |
| `responsibility_type` | String(20) | NOT NULL, CHECK in set | Enum: `manages`, `understands`, `administers` |
| `backup_status` | String(20) | NOT NULL, CHECK in set, default `backup_unknown` | Enum: `has_backup`, `no_backup`, `backup_unknown` |
| `created_at` | DateTime | default utcnow | |

**Relationships:** `backup_people` (one-to-many → ResponsibilityBackup)

**Constraint:** Unique constraint on `(asset_id, primary_person_id, responsibility_type)` — a person can only have one responsibility of a given type per asset.

**Index:** `ix_responsibility_asset_id`, `ix_responsibility_primary_person_id`

#### ResponsibilityBackup

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | Integer | PK, autoincrement | |
| `responsibility_id` | Integer | FK → Responsibility.id, NOT NULL | Cascade delete with responsibility |
| `backup_person_id` | Integer | FK → Person.id, NOT NULL | The person who can fill in |
| `created_at` | DateTime | default utcnow | |

**Constraint:** Unique constraint on `(responsibility_id, backup_person_id)` — no duplicate backup assignments.

**Index:** `ix_resp_backup_responsibility_id`, `ix_resp_backup_person_id`

**Business rule:** Records only exist when the parent Responsibility has `backup_status = has_backup`. If backup_status changes to `no_backup` or `backup_unknown`, all ResponsibilityBackup rows for that responsibility are deleted.

#### AssetDocumentation

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | Integer | PK, autoincrement | |
| `asset_id` | Integer | FK → Asset.id, NOT NULL, UNIQUE | One-to-one with Asset |
| `status` | String(20) | NOT NULL, CHECK in set, default `unknown` | Enum: `yes`, `no`, `unknown` |
| `location_note` | String(500) | nullable | e.g., "Google Drive > IT folder" — never stores document content or secrets |
| `created_at` | DateTime | default utcnow | |

#### AssetDependency

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | Integer | PK, autoincrement | |
| `asset_id` | Integer | FK → Asset.id, NOT NULL, UNIQUE | One-to-one with Asset |
| `depends_on_personal_account` | Boolean | NOT NULL, default False | True if asset relies on a personal (not org-owned) account |
| `personal_account_note` | String(500) | nullable | e.g., "Domain registered under Dami's personal email" — no secrets |
| `depends_on_single_device` | Boolean | NOT NULL, default False | True if asset relies on one specific device |
| `single_device_note` | String(500) | nullable | e.g., "Office laptop in the sound booth" |
| `created_at` | DateTime | default utcnow | |

### 3.4 Enum Reference

All enums are stored as strings (not Python Enum types) for SQLite simplicity. Validated by CHECK constraints.

| Enum | Values |
|---|---|
| `org_type` | `church`, `nonprofit`, `student_org`, `family_business`, `other` |
| `asset_category` | `livestream`, `website`, `social_media`, `network_wifi`, `data_storage`, `communication`, `payment`, `other` |
| `criticality` | `critical`, `high`, `medium`, `low` |
| `responsibility_type` | `manages`, `understands`, `administers` |
| `backup_status` | `has_backup`, `no_backup`, `backup_unknown` |
| `documentation_status` | `yes`, `no`, `unknown` |

### 3.5 What is NOT stored

- **Risk scores.** Computed on demand by `risk_scoring.py`. Never persisted as table data. This ensures scores are always consistent with current data.
- **Secrets.** No column in any table is designed to hold passwords, keys, tokens, or credentials. Free-text note fields are explicitly labeled with "do not enter secrets" guidance.
- **User accounts / passwords.** No auth for the MVP. Person records are lightweight contact info, not login accounts.

---

## 4. Risk Scoring Design

### 4.1 Principles

- **Deterministic.** Same input always produces the same output. No randomness, no AI.
- **Explainable.** Every score comes with a list of contributing factors and their individual point values. A judge or user can trace exactly how the number was derived.
- **Per-asset first, then aggregated to organization.** Each asset gets a 0–100 score. The organization score is derived from the distribution of asset scores.
- **No stored scores.** Always recomputed from current data.

### 4.2 Per-Asset Risk Score (0–100)

Each asset starts with a **criticality base score**, then accumulates **penalties** from risk factors. The final score is capped at 100.

#### Step 1: Criticality Base Score

| Criticality | Base Score |
|---|---|
| Critical | 45 |
| High | 30 |
| Medium | 18 |
| Low | 8 |

Rationale: Criticality is the foundation. A critical asset with perfect coverage still carries baseline risk because its loss would severely impact the organization. A low-criticality asset with no backup is less urgent.

#### Step 2: Backup Penalty (per responsibility)

For each responsibility on the asset, add a penalty based on its backup status:

| Backup Status | Penalty per Responsibility |
|---|---|
| `no_backup` | +15 |
| `backup_unknown` | +7 |
| `has_backup` | +0 |

**Cap:** Total backup penalty is capped at **30 points**. This prevents an asset with many no_backup responsibilities from dominating the score unrealistically — the point is that one missing backup is already a problem; ten missing backups is the same problem, not ten times worse.

#### Step 3: Documentation Penalty

| Documentation Status | Penalty |
|---|---|
| `no` | +15 |
| `unknown` | +7 |
| `yes` | +0 |

#### Step 4: Dependency Penalties

| Factor | Penalty |
|---|---|
| `depends_on_personal_account = True` | +15 |
| `depends_on_single_device = True` | +10 |

#### Step 5: Final Score

```
asset_score = min(
    criticality_base
    + backup_penalty_capped_at_30
    + documentation_penalty
    + personal_account_penalty
    + single_device_penalty,
    100
)
```

#### Thresholds

| Score Range | Risk Level |
|---|---|
| 0–24 | Low |
| 25–49 | Medium |
| 50–74 | High |
| 75–100 | Critical |

#### Worked Examples

**Example A — Critical asset, no backup, no docs, personal account, single device:**
```
Base (Critical):     45
Backup (1 × no_backup): +15
Documentation (no):     +15
Personal account:      +15
Single device:         +10
────────────────────────────
Total:               100 → Critical
```

**Example B — Low asset, has backup, documented, no dependencies:**
```
Base (Low):           8
Backup (1 × has_backup): +0
Documentation (yes):     +0
Personal account:       +0
Single device:          +0
────────────────────────────
Total:                 8 → Low
```

**Example C — High asset, backup unknown, no docs, no deps:**
```
Base (High):         30
Backup (1 × backup_unknown): +7
Documentation (no):     +15
Personal account:       +0
Single device:          +0
────────────────────────────
Total:                52 → High
```

**Example D — Critical asset, has backup, documented, no deps:**
```
Base (Critical):     45
Backup (1 × has_backup): +0
Documentation (yes):     +0
Personal account:       +0
Single device:          +0
────────────────────────────
Total:                45 → Medium
```
A critical asset with full coverage is still Medium — the criticality itself carries baseline risk, but good practices bring it down from Critical.

### 4.3 Risk Breakdown (Explainability)

Every per-asset score is returned with a structured breakdown so the UI can display contributing factors:

```python
AssetRiskResult:
    asset_id: int
    asset_name: str
    score: int                    # 0–100
    risk_level: str               # "critical" | "high" | "medium" | "low"
    contributing_factors: list[ContributingFactor]

ContributingFactor:
    label: str        # e.g., "Critical asset"
    points: int       # e.g., 45
    detail: str       # e.g., "This asset is marked as Critical priority"
```

Example breakdown for Example A:
```
[
  {"label": "Critical asset", "points": 45, "detail": "Criticality base score"},
  {"label": "No backup for Manages (Dami)", "points": 15, "detail": "Dami manages this asset with no backup person"},
  {"label": "No documentation", "points": 15, "detail": "No documentation exists for this asset"},
  {"label": "Depends on personal account", "points": 15, "detail": "Registered under a personal account"},
  {"label": "Depends on single device", "points": 10, "detail": "Relies on one specific device"},
]
```

### 4.4 Organization-Level Risk Score

The organization risk is derived from the distribution of per-asset risk levels. It is **not** an average — it is driven by the worst assets, with one accumulation rule.

**Rules (evaluated in order):**

| Rule | Condition | Org Risk Level |
|---|---|---|
| 1 | ≥ 1 asset is Critical | **Critical** |
| 2 | ≥ 3 assets are High (and none Critical) | **Critical** |
| 3 | ≥ 1 asset is High (and none Critical) | **High** |
| 4 | ≥ 1 asset is Medium (and none Critical/High) | **Medium** |
| 5 | All assets are Low | **Low** |

**Explanation for judges:** The organization's risk is driven by its most vulnerable assets. Even one Critical asset makes the organization Critical. If three or more assets are High, the accumulation of risk escalates the organization to Critical. Otherwise, the organization matches the highest single-asset level.

### 4.5 Implementation

The scoring engine lives in `app/services/risk_scoring.py` as pure functions:

```python
def calculate_asset_risk(
    asset: Asset,
    responsibilities: list[Responsibility],
    documentation: AssetDocumentation | None,
    dependency: AssetDependency | None,
) -> AssetRiskResult:
    """Returns score (0-100), risk_level, and contributing factors."""

def calculate_org_risk(
    db: Session,
    organization_id: int,
) -> OrgRiskResult:
    """Loads all assets for the org, computes per-asset scores,
    then applies org-level aggregation rules.
    Returns overall risk level, score distribution, and top risks."""
```

No AI. No database writes. Pure computation from current data. Fully unit-testable.

---

## 5. What If Simulator

### 5.1 Scope (MVP)

Single-person simulation only (Tier 1). Multi-person simulation is Tier 2 stretch.

### 5.2 Algorithm

When a person P becomes unavailable, the simulator evaluates every asset where P is a **primary person** on at least one responsibility.

```
INPUT: organization_id, unavailable_person_id (P)

FOR each asset A where P is primary on ≥1 responsibility:
    p_responsibilities = [r for r in A.responsibilities if r.primary_person_id == P]
    other_responsibilities = [r for r in A.responsibilities if r.primary_person_id != P]

    lost_count = 0       # responsibilities with no surviving coverage
    at_risk_count = 0    # responsibilities with backup_unknown
    covered_count = 0    # responsibilities with surviving backup

    FOR each r in p_responsibilities:
        IF r.backup_status == "no_backup":
            lost_count += 1
        ELIF r.backup_status == "backup_unknown":
            at_risk_count += 1
        ELIF r.backup_status == "has_backup":
            surviving_backups = [bp for bp in r.backup_people if bp.id != P.id]
            IF surviving_backups:
                covered_count += 1
            ELSE:
                # Edge case: backup person IS the same as primary (unusual)
                lost_count += 1

    # Classify the asset
    IF lost_count > 0 AND len(other_responsibilities) == 0 AND covered_count == 0:
        classification = "orphaned"
    ELIF lost_count > 0 OR at_risk_count > 0:
        classification = "partially_affected"
    ELSE:
        classification = "unaffected"

    # Record the affected responsibility details
    affected.append({
        asset: A,
        classification: classification,
        lost_responsibilities: [...],     # names of people/responsibilities lost
        at_risk_responsibilities: [...],
        covered_responsibilities: [...],
        surviving_backup_names: [...],
    })
```

### 5.3 Classification Definitions

| Classification | Meaning | Condition |
|---|---|---|
| **Orphaned** | Nobody left who can handle this asset | All of P's responsibilities are lost (`no_backup`), and no other people have responsibilities on this asset. The asset is completely uncovered. |
| **Partially affected** | Some coverage lost or uncertain | At least one of P's responsibilities is lost or unknown, but either other people still have roles on the asset, or some of P's responsibilities have surviving backups. The asset is degraded but not abandoned. |
| **Unaffected** | Backup covers P's role | All of P's responsibilities have surviving backup people (not P). The asset continues to function with backup coverage. |

### 5.4 Simulated Risk Score

For each affected asset, the simulator computes a **simulated per-asset score**:

| Classification | Simulated Score | Rationale |
|---|---|---|
| Orphaned | **100** (Critical) | Nobody can operate the asset — maximum risk. |
| Partially affected | **min(current_score + 25, 100)** | The hypothetical risk has partially materialized — the score increases to reflect real impact. |
| Unaffected | **current_score** (unchanged) | Backup covers — no change. |

Assets where P is not a primary person keep their current score.

The **simulated organization risk** is then calculated using the same org-level aggregation rules (section 4.4) applied to the modified per-asset scores. This produces a before/after comparison.

### 5.5 Simulation Result Structure

```python
SimulationResult:
    unavailable_person: Person
    current_org_risk: OrgRiskResult        # before simulation
    simulated_org_risk: OrgRiskResult      # after simulation
    affected_assets: list[SimulationAssetResult]

SimulationAssetResult:
    asset: Asset
    classification: str                     # "orphaned" | "partially_affected" | "unaffected"
    lost_responsibilities: list[str]         # e.g., ["Manages (Dami)"]
    at_risk_responsibilities: list[str]     # e.g., ["Administers (Dami) - backup unknown"]
    covered_responsibilities: list[str]     # e.g., ["Manages (Dami) → backup: Sarah"]
    surviving_backup_names: list[str]       # e.g., ["Sarah"]
    current_score: int
    simulated_score: int
    current_level: str
    simulated_level: str
```

### 5.6 Implementation

Lives in `app/services/simulator.py`:

```python
def simulate_person_unavailable(
    db: Session,
    organization_id: int,
    unavailable_person_id: int,
) -> SimulationResult:
    """Simulate one person becoming unavailable.
    Loads all responsibilities for the org, finds those where the
    unavailable person is primary, classifies each affected asset,
    computes simulated scores, and returns the full result."""
```

Pure computation. No writes to the database. Called via AJAX from the simulator page.

---

## 6. Guided Dependency Discovery

### 6.1 Interview Overview

The interview walks a non-technical coordinator through 8 dependency categories, one at a time. For each category, the coordinator answers plain-language questions. The answers are converted into proposed records (people, assets, responsibilities, documentation, dependencies). The user reviews and confirms before anything is saved.

Two modes:
- **AI-assisted:** User answers in natural language. Bedrock interprets the answers and proposes structured records.
- **Structured fallback (no AI):** User fills in labeled form fields (text inputs, dropdowns, radio buttons). Data is already structured — no interpretation needed.

Both modes converge on the same review/confirm page.

### 6.2 Interview Categories

| # | Category Key | Display Name | Example Assets |
|---|---|---|---|
| 1 | `livestream` | Livestream / Audio-Visual | Sunday Livestream, OBS Setup, Audio System |
| 2 | `website` | Website / Domain | Church Website, Domain Registration |
| 3 | `social_media` | Social Media | Instagram, Facebook Page, YouTube Channel |
| 4 | `network_wifi` | Wi-Fi / Network | Office Wi-Fi, Router Configuration |
| 5 | `data_storage` | Shared Files / Cloud Storage | Google Drive, Shared Dropbox |
| 6 | `payment` | Payment / Donation System | Donation Platform, PayPal Account |
| 7 | `communication` | Email / Communication | Org Email, Mailing List, Slack/Discord |
| 8 | `other` | Other Critical Technology | User names it (e.g., "Printing System") |

### 6.3 Question Sequence (Per Category)

The interview presents these questions for each category. In AI-assisted mode, they are conversational prompts. In structured mode, they are labeled form fields.

| Step | Question | Input Type | Maps To |
|---|---|---|---|
| 1 | "Does your organization use {category}?" | Yes / No / Skip | If No or Skip → next category |
| 2 | "What name or label would you use for this?" | Free text | `Asset.name` |
| 3 | "Who normally handles this?" | Free text | `Person.name` |
| 4 | "What is their role or title?" | Free text | `Person.role_title` |
| 5 | "What do they do with it?" | Free text (AI mode) / Dropdown (structured mode) | `Responsibility.responsibility_type` (manages/understands/administers) |
| 6 | "If that person were unavailable tomorrow, could someone else perform the task?" | Yes / No / Not sure | `Responsibility.backup_status` (has_backup/no_backup/backup_unknown) |
| 7 | *(If Yes)* "Who could fill in?" | Free text | `ResponsibilityBackup.backup_person_id` → `Person.name` |
| 8 | "Is there documentation for how this works?" | Yes / No / Not sure | `AssetDocumentation.status` |
| 9 | *(If Yes)* "Where is it located?" | Free text | `AssetDocumentation.location_note` |
| 10 | "Does this rely on one particular device (like a specific laptop)?" | Yes / No / Not sure | `AssetDependency.depends_on_single_device` |
| 11 | "Is an organization-owned account used, or does it depend on someone's personal account?" | Organization / Personal / Not sure | `AssetDependency.depends_on_personal_account` |

**Criticality** is not asked during the interview. It defaults to `medium` and the user can adjust it later on the asset detail page or during review. This keeps the interview fast and non-technical.

### 6.4 AI-Assisted Interpretation

When AI is enabled, the user's free-text answers for a category are sent to Bedrock after the user completes all questions for that category (not per keystroke — NFR-5).

**Pre-transmission secret check (mandatory):**
Before any answers are sent to Bedrock, every free-text answer is passed through `secret_check.validate_answers()`. If likely secret material is detected in any answer, the application does NOT call Bedrock. Instead, it returns a user-friendly validation error asking the user to remove the credential and resubmit. Only answers that pass the secret check are transmitted to Bedrock. The application does NOT rely on the LLM system prompt to remove secrets after they have already been transmitted.

**What is sent to Bedrock (after validation):**
- System prompt (instructions for extraction, format specification, security boundary)
- The category key and display name
- The user's answers to questions 2–11 (free text only, already validated secret-free)

**What is NEVER sent:**
- Passwords, API keys, tokens, recovery codes, Wi-Fi passwords, or any secret (enforced by pre-transmission check)
- Data from other categories
- Existing database records

**Expected JSON output from Bedrock:**

```json
{
  "asset": {
    "name": "Sunday Livestream",
    "category": "livestream",
    "description": "Weekly Sunday service livestream"
  },
  "people": [
    {"name": "Dami", "role_title": "Technology Coordinator"}
  ],
  "responsibilities": [
    {
      "primary_person_name": "Dami",
      "responsibility_type": "manages",
      "backup_status": "no_backup",
      "backup_people_names": []
    }
  ],
  "documentation": {
    "status": "no",
    "location_note": null
  },
  "dependencies": {
    "depends_on_personal_account": false,
    "personal_account_note": null,
    "depends_on_single_device": true,
    "single_device_note": "Livestream laptop in the sound booth"
  }
}
```

The AI may propose multiple people or multiple responsibilities if the user's answers suggest them (e.g., "Dami runs it but James also knows how to set it up" → two responsibilities). The user reviews all proposals.

### 6.5 Structured Fallback (No AI)

When AI is disabled or unavailable, the same questions are presented as a structured form:

- Question 2: `<input type="text" name="asset_name">`
- Question 3: `<input type="text" name="person_name">`
- Question 4: `<input type="text" name="role_title">`
- Question 5: `<select name="responsibility_type"><option>Manages</option>...</select>`
- Question 6: `<input type="radio" name="backup" value="yes|no|not_sure">`
- Question 7 (conditional): `<input type="text" name="backup_person_name">`
- Question 8: `<input type="radio" name="docs" value="yes|no|not_sure">`
- Question 9 (conditional): `<input type="text" name="doc_location">`
- Question 10: `<input type="radio" name="single_device" value="yes|no|not_sure">`
- Question 11: `<input type="radio" name="personal_account" value="org|personal|not_sure">`

The form data maps directly to the same JSON structure as the AI output. No interpretation needed.

### 6.6 Review and Confirm Flow

After completing all categories (or stopping early), the user sees a **review page**:

1. **Proposed records list:** Every proposed person, asset, responsibility, documentation status, and dependency flag is displayed in an editable list.
2. **Per-record controls:** Each proposed record has:
   - An **accept** checkbox (default checked)
   - Editable fields (name, category, criticality, responsibility type, backup status, backup people, documentation status, dependency flags)
   - A **reject** button (removes from the save set)
3. **Duplicate detection:** If a proposed person's name matches an existing person, the UI offers "Use existing [name]" or "Create new." Same for assets.
4. **Save:** When the user clicks "Save Confirmed Records," only accepted records are persisted. Rejected records are discarded.
5. **Security check (blocking):** All free-text fields pass through `secret_check.py` before saving. If likely secret material is detected, the field is rejected — the save is blocked and the user is asked to edit the text and resubmit. A user-friendly message is displayed: "Please remove passwords, access codes, API keys, tokens, recovery codes, or other credentials before continuing. WithinReach only needs to know who manages the system — never the credential itself."

### 6.7 Interview State Management

The interview is stateless across page loads for the MVP. Progress is tracked client-side:
- Current category index (which category the user is on)
- Accumulated proposed records (stored in browser `sessionStorage` as JSON)
- Skipped categories (can be revisited)

When the user clicks "Save Confirmed Records," the accumulated proposed records are sent to the server in a single POST request. The server validates all free-text fields through `secret_check.py` (blocking — rejects fields with likely credential material), checks for duplicates, creates records, and returns the user to the dashboard. If any field fails the secret check, the server returns a validation error for the affected field and the record is not saved.

This avoids server-side interview session management, keeping the backend simple.

### 6.8 Implementation

Lives in `app/services/interview_service.py`:

```python
CATEGORIES = [
    {"key": "livestream", "label": "Livestream / Audio-Visual", ...},
    ...
]

def get_category(index: int) -> dict:
    """Return category definition for the given index."""

def interpret_answers(
    category_key: str,
    answers: dict,
    ai_enabled: bool,
) -> ProposedRecords:
    """Convert answers to proposed records.
    1. Validate all free-text answers through secret_check.validate_answers() (blocking).
       If any answer fails, raise validation error — do NOT call Bedrock.
    2. If ai_enabled: call ai_service.interpret_interview_answers()
    3. Else: structured_form_fallback() — direct field mapping."""

def structured_form_fallback(category_key: str, answers: dict) -> ProposedRecords:
    """Map form fields directly to ProposedRecords without AI."""

def save_confirmed_records(db, org_id, confirmed: list[ConfirmedRecord]):
    """Persist confirmed records. Validate all free-text fields through
    secret_check.validate_free_text_fields() (blocking). Check for duplicate
    people/assets by name. Create new or link to existing.
    If any field fails the secret check, raise a validation error and do not save."""
```

---

## 7. Visual Dependency Map

### 7.1 Library Choice

**Cytoscape.js** loaded via CDN (`<script>` tag, no build step). Chosen because:
- Built-in graph layout algorithms (no manual positioning)
- Simple JSON data format (nodes + edges)
- Built-in styling, zoom, pan, and click events
- Single JS file, no dependencies
- Well-documented, reliable for a hackathon

Loaded in `templates/dependency_map.html`:
```html
<script src="https://cdn.jsdelivr.net/npm/cytoscape@3.28.1/dist/cytoscape.min.js"></script>
<script src="/static/js/dependency_map.js"></script>
```

### 7.2 Graph Data Model

The server endpoint `GET /api/dependency-map` returns JSON consumed by Cytoscape:

```json
{
  "nodes": [
    {
      "data": {
        "id": "person-1",
        "type": "person",
        "label": "Dami",
        "role": "Technology Coordinator",
        "risk_load": "high",
        "critical_asset_count": 2,
        "uncovered_count": 3
      }
    },
    {
      "data": {
        "id": "asset-1",
        "type": "asset",
        "label": "Sunday Livestream",
        "category": "livestream",
        "risk_level": "critical",
        "criticality": "critical"
      }
    },
    {
      "data": {
        "id": "func-livestream",
        "type": "function",
        "label": "Livestream / Audio-Visual"
      }
    }
  ],
  "edges": [
    {
      "data": {
        "id": "e1",
        "source": "person-1",
        "target": "asset-1",
        "label": "Manages",
        "edge_type": "primary",
        "risk_level": "critical",
        "backup_status": "no_backup"
      }
    },
    {
      "data": {
        "id": "e2",
        "source": "asset-1",
        "target": "func-livestream",
        "label": "",
        "edge_type": "category",
        "risk_level": "none"
      }
    }
  ]
}
```

### 7.3 Node Design

| Node Type | Shape | Label Content | Size |
|---|---|---|---|
| **Person** | Circle (ellipse) | Name + role | Larger if connected to multiple critical assets (scaled by `critical_asset_count`) |
| **Asset** | Rounded rectangle | Asset name | Standard size; border thickness by criticality |
| **Function** | Rectangle (bar) | Category display name | Fixed small size |

### 7.4 Edge Design

| Edge Type | Style | Color Logic |
|---|---|---|
| **Person → Asset (primary)** | Solid line | Colored by backup status: red = `no_backup`, orange = `backup_unknown`, green = `has_backup` |
| **Person → Asset (backup)** | Dashed line | Same color logic, but dashed to indicate backup role |
| **Asset → Function** | Thin gray line | Neutral — just shows the category grouping |

Edge labels show the responsibility type abbreviation: **M** (Manages), **U** (Understands), **A** (Administers).

### 7.5 Risk Visual Encoding

| Visual Element | Encoding |
|---|---|
| Asset node border | Red = Critical risk, Orange = High, Yellow = Medium, Green = Low |
| Asset node border thickness | Thick = Critical criticality, Medium = High, Thin = Medium/Low |
| Person node fill | Red if any connected responsibility has `no_backup` on a Critical asset; Orange if `backup_unknown`; Green if all healthy |
| Edge color | Red = `no_backup`, Orange = `backup_unknown`, Green = `has_backup` |
| Person node size | Scaled by number of critical assets connected — a person handling 3 critical assets with no backup appears visibly larger |

### 7.6 Single Point of Failure Visual

A person node that is connected to one or more Critical/High assets via red (no_backup) edges will:
- Have a **red fill** (or red ring)
- Be **larger** than other person nodes
- Have a **badge** showing the count of uncovered critical responsibilities

This makes it immediately obvious to a non-technical reviewer: "This red circle person is a single point of failure for these red-bordered assets."

### 7.7 Interactions

| Action | Behavior |
|---|---|
| Click person node | Navigate to `/people/{id}` (person detail page) |
| Click asset node | Navigate to `/assets/{id}` (asset detail page) |
| Click function node | No action (informational) |
| Hover over node | Tooltip with name, role/category, risk level |
| Hover over edge | Tooltip with responsibility type, backup status, backup person names |

### 7.8 Layout

Use Cytoscape's built-in `cose` layout (Compound Spring Embedder — force-directed). It automatically positions connected nodes near each other and pushes unconnected ones apart. No manual coordinates needed.

```javascript
cy.layout({
  name: 'cose',
  animate: true,
  nodeRepulsion: 8000,
  idealEdgeLength: 100,
  // ... other cose params
}).run();
```

Alternative: `breadthfirst` layout for a left-to-right flow (People → Assets → Functions), but `cose` is more robust for varied graph sizes.

### 7.9 Legend

A static HTML legend is displayed below or beside the graph:

```
Nodes:  ● Person    □ Asset    ▬ Function
Edges:  ── Primary    ┄┄ Backup
Colors: ■ Critical    ■ High    ■ Medium    ■ Low
Risk:   ── No backup (red)    ── Backup unknown (orange)    ── Has backup (green)
```

### 7.10 Implementation

Server side (`app/services/dependency_map_service.py`):
```python
def build_graph_data(db, org_id) -> dict:
    """Load all people, assets, responsibilities, backup associations,
    documentation, and dependencies for the org. Build Cytoscape-compatible
    nodes and edges with risk-level annotations."""
```

Client side (`static/js/dependency_map.js`):
```javascript
// Fetch graph data, initialize Cytoscape with styling and layout,
// bind click events for navigation.
```

---

## 8. AI Integration

### 8.1 Provider

**Amazon Bedrock** via `boto3`. Configured through environment variables:
- `AI_ENABLED` — `true`/`false` (master toggle; when `false`, all AI features use fallbacks)
- `BEDROCK_MODEL_ID` — configurable model ID (e.g., `anthropic.claude-3-haiku-20240307-v1:0`). The `.env.example` contains an example default, but the implementation must not assume that exact model is always available. If the configured model is unavailable or inaccessible, the application must fail gracefully to rule-based / structured fallback.
- `BEDROCK_REGION` — e.g., `us-east-1`
- `AWS_PROFILE` — optional, for local dev credentials

The provider is swappable: `ai_service.py` wraps the Bedrock call behind a clean interface. Swapping to OpenAI or another provider means changing one function.

### 8.2 Use Case 1 — Interview Interpretation

**When:** After the user completes all questions for a category (not per keystroke).

**Pre-transmission secret check (mandatory):**
Before calling Bedrock, the application inspects all user free-text answers with `secret_check.validate_answers()`. If likely secret material is detected, the application does NOT call Bedrock — it asks the user to edit the affected answer and resubmit. Only answers that pass the secret check are transmitted. The application does NOT rely on the LLM system prompt to remove secrets after they have already been transmitted. The AI system prompt still instructs the model not to output or request credentials, as defense in depth.

**What is sent to Bedrock (after validation):**
- System prompt (instructions for extraction, format specification, security boundary)
- The category key and display name
- The user's answers to questions 2–11 (free text, already validated secret-free)

**What is NEVER sent:**
- Passwords, keys, tokens, recovery codes, Wi-Fi passwords
- Data from other categories
- Existing database records

**System prompt (interview):**
```
You are a continuity planning assistant helping a small community organization
map its technology dependencies. You will receive plain-language answers about
the organization's {category} technology and must extract structured records.

RULES:
- NEVER include, request, or reference passwords, API keys, access tokens,
  Wi-Fi passwords, recovery codes, or any secret. If the user mentions one,
  exclude it from your output.
- Infer the responsibility_type from the user's description:
  "manages" = operates/runs/handles day-to-day
  "understands" = knows how it works but may not run it daily
  "administers" = has admin access, configures settings, manages accounts
- If unsure about backup status, use "backup_unknown".
- If unsure about documentation, use "unknown".
- Default criticality to "medium" if not clearly critical.

Return JSON with this exact structure:
{...JSON schema as defined in section 6.4...}
```

**Expected output:** JSON matching the `ProposedRecords` schema (section 6.4).

**Fallback:** If Bedrock fails (timeout, error, or `AI_ENABLED=false`), the interview service uses `structured_form_fallback()` which maps form fields directly to the same JSON structure without AI interpretation. The user experience is the same review/confirm page with slightly less automated interpretation.

### 8.3 Use Case 2 — Recommendation Generation

**When:** User clicks "Generate Recommendations" on the recommendations page.

**What is sent:**
- System prompt (instructions for recommendation generation)
- The organization's risk profile as structured JSON: asset names, categories, criticality, risk scores, contributing factors, backup gaps, documentation status, dependency flags, person names involved

**What is NEVER sent:**
- Passwords, keys, tokens, recovery codes, any secret
- Personal email addresses (person names only, not contact emails)
- The content of documentation or notes that might contain secrets

**System prompt (recommendations):**
```
You are a continuity planning assistant for small community organizations.
Given the organization's technology dependency risk profile, generate specific,
actionable recommendations to reduce continuity risks.

RULES:
- Each recommendation must reference a specific asset and/or person by name.
- Recommendations must be practical for a small volunteer-run organization.
- Prioritize by impact: Critical risks first, then High, then Medium.
- Do not reference passwords, keys, tokens, or secrets.
- Be specific and actionable, not generic (e.g., "Train James to manage the
  Sunday Livestream so that Dami is not the only person who can operate it"
  not "Ensure backup coverage").

Return a JSON array of recommendations:
[
  {
    "priority": "critical",
    "asset_name": "Sunday Livestream",
    "person_name": "Dami",
    "risk_description": "Dami is the only person who can manage the livestream",
    "recommendation": "Train James to operate the livestream system...",
    "rationale": "If Dami is unavailable, the Sunday service livestream cannot run..."
  },
  ...
]
```

**Input JSON (sent as user message):**
```json
{
  "organization": {"name": "Grace Community Church", "type": "church"},
  "risks": [
    {
      "asset_name": "Sunday Livestream",
      "category": "livestream",
      "criticality": "critical",
      "risk_level": "critical",
      "risk_score": 85,
      "contributing_factors": [
        "Critical asset (45 pts)",
        "No backup for Manages - Dami (15 pts)",
        "No documentation (15 pts)",
        "Depends on single device (10 pts)"
      ]
    },
    ...
  ]
}
```

**Expected output:** JSON array of recommendation objects.

### 8.4 Fallback Recommendations (No AI)

When AI is unavailable, `recommendation_service.py` generates rule-based recommendations from the risk data using templates:

| Risk Factor | Template Recommendation |
|---|---|
| `no_backup` on Critical/High asset | "Identify and train a backup person who can {responsibility_type} {asset_name}. Currently only {primary_person_name} has this role with no backup." |
| `backup_unknown` | "Confirm whether someone else can {responsibility_type} {asset_name}. The backup status is currently unknown." |
| `no` documentation | "Create documentation for {asset_name} so that knowledge is not dependent on one person." |
| `depends_on_personal_account` | "Transfer {asset_name} from {primary_person_name}'s personal account to an organization-owned account." |
| `depends_on_single_device` | "Ensure {asset_name} is not dependent on a single device. Consider a backup device or cloud-based alternative." |

Recommendations are sorted by asset risk level (Critical first), then by penalty severity. Each references the specific asset and person by name.

### 8.5 Error Handling

```python
try:
    if settings.AI_ENABLED:
        result = ai_service.generate_recommendations(risk_profile)
    else:
        result = recommendation_service.rule_based_recommendations(risk_profile)
except Exception as e:
    logger.warning(f"Bedrock call failed: {e}. Using fallback.")
    result = recommendation_service.rule_based_recommendations(risk_profile)
```

The user never sees an error — they always get recommendations, whether from AI or fallback. The UI can show a subtle indicator ("AI-assisted" vs "Rule-based") so the demo can showcase both paths.

### 8.6 Implementation

`app/services/ai_service.py`:
```python
def interpret_interview_answers(category_key: str, answers: dict) -> ProposedRecords:
    """Call Bedrock with the interview prompt. Parse JSON response.
    Raise on error so caller can fall back."""

def generate_recommendations(risk_profile: dict) -> list[Recommendation]:
    """Call Bedrock with the recommendation prompt. Parse JSON response.
    Raise on error so caller can fall back."""
```

`app/config.py`:
```python
class Settings(BaseSettings):
    AI_ENABLED: bool = False
    BEDROCK_MODEL_ID: str = "anthropic.claude-3-haiku-20240307-v1:0"
    BEDROCK_REGION: str = "us-east-1"
    DATABASE_URL: str = "sqlite:///./continuity.db"
```

**Model ID is configurable, not hard-coded.** The `BEDROCK_MODEL_ID` default in `.env.example` is an example only. The implementation must not assume that exact model will always be available. If the configured model is unavailable or inaccessible, Bedrock integration must fail gracefully to the rule-based / structured fallback. The `AI_ENABLED` toggle and the try/except fallback in `ai_service.py` ensure the application always works with or without Bedrock.

---

## 9. Security Design

### 9.1 Core Principle

The application never asks for, accepts, stores, or transmits passwords, API keys, access tokens, Wi-Fi passwords, recovery codes, or any other secret. This is enforced through:

1. **Schema design** — no column exists to hold secrets. Free-text note fields are explicitly labeled.
2. **Form design** — no password/key/token input fields. No generic credential fields.
3. **Secret detection (blocking)** — free-text fields are checked for likely credential material BEFORE saving to the database and BEFORE sending to Bedrock. If likely secret material is detected, the text is not persisted or transmitted. The user is asked to edit and resubmit.
4. **AI input boundary** — all user free-text answers are validated before transmission to Bedrock. The application does NOT rely on the LLM system prompt to remove secrets after transmission. The system prompt still instructs the model not to output credentials, as defense in depth.
5. **Visible guidance** — every free-text input has a label or placeholder warning: "Do not enter passwords, keys, or tokens."

### 9.2 Free-Text Field Inventory

These are the only free-text fields in the application:

| Field | Location | Max Length |
|---|---|---|
| `AssetDocumentation.location_note` | Asset detail, interview | 500 chars |
| `AssetDependency.personal_account_note` | Asset detail, interview | 500 chars |
| `AssetDependency.single_device_note` | Asset detail, interview | 500 chars |
| `Asset.description` | Asset form, interview | Free text |
| `Organization.description` | Org setup | Free text |
| Interview free-text answers | Interview (AI mode) | Free text |

No field is labeled "password," "key," "token," "secret," or "credential."

### 9.3 Secret Detection (Blocking, Lightweight)

`app/services/secret_check.py` implements a two-layer check that combines sensitive-context keywords with simple value-supply patterns. The check is **blocking** — if likely secret material is detected, the application does NOT persist the text to the database and does NOT transmit it to Bedrock. The user is asked to edit and resubmit.

#### Layer 1: Sensitive-Context Keywords

These keywords indicate the text may be discussing a credential:

```python
SECRET_KEYWORDS = [
    "password", "passwd", "pwd",
    "api key", "apikey", "api_key",
    "access token", "auth token", "bearer token",
    "secret key", "secretkey",
    "private key", "privatekey",
    "recovery code",
    "wi-fi password", "wifi password", "wifi-password",
    "credential",
    "otp", "2fa code",
]
```

A keyword match alone does NOT block — it activates Layer 2.

#### Layer 2: Value-Supply Patterns

If a sensitive-context keyword is present, the check looks for patterns suggesting an actual value is being supplied (not just mentioning the concept):

```python
SECRET_PATTERNS = [
    r"password\s+(?:is|:|=)\s+\S",          # "password is X", "password: X", "password = X"
    r"passwd\s+(?:is|:|=)\s+\S",
    r"pwd\s+(?:is|:|=)\s+\S",
    r"api\s*key\s*(?:is|:|=)\s+\S",         # "API key is X", "API key: X", "apikey = X"
    r"token\s*(?:is|:|=)\s+\S",             # "token is X", "token: X"
    r"secret\s*key\s*(?:is|:|=)\s+\S",
    r"private\s*key\s*(?:is|:|=)\s+\S",
    r"recovery\s*code\s*(?:is|:|=)\s+\S",
    r"wi-?fi\s*password\s+(?:is|:|=)\s+\S", # "Wi-Fi password is X"
    r"credential\s*(?:is|:|=)\s+\S",
]
```

A field is **blocked** only when BOTH layers match: a sensitive keyword is present AND a value-supply pattern matches. This prevents false positives on harmless statements like "The password reset procedure is documented in the IT binder" (keyword "password" present, but no value-supply pattern — not blocked).

#### Implementation

```python
def check_for_secrets(text: str) -> SecretCheckResult:
    """Two-layer check: keyword presence + value-supply pattern.
    Returns (blocked: bool, matched_keywords: list[str], matched_patterns: list[str]).
    If blocked is True, the caller must NOT persist or transmit the text."""

def validate_free_text_fields(fields: dict[str, str]) -> ValidationResult:
    """Check all free-text fields in a record.
    Returns (valid: bool, errors: dict[field_name, message]).
    If any field is blocked, returns the user-friendly message for each blocked field."""

def validate_answers(answers: dict) -> ValidationResult:
    """Check all free-text answers before AI transmission.
    Returns (valid: bool, errors: dict[question_key, message]).
    If any answer is blocked, the caller must NOT call Bedrock."""
```

#### User-Facing Message (Blocking)

When a field is blocked, the application displays:

> "Please remove passwords, access codes, API keys, tokens, recovery codes, or other credentials before continuing. WithinReach only needs to know who manages the system — never the credential itself."

The user can edit the text and resubmit. The blocked text is never persisted or transmitted.

### 9.4 Application of the Secret Check

The secret check is applied at three boundaries, all **blocking**:

| Boundary | When | Behavior |
|---|---|---|
| **Database save** | Before any free-text field is written to SQLite | Server-side validation is authoritative. If blocked, reject the field and return a validation error instead of saving. |
| **AI transmission** | Before any free-text answer is sent to Bedrock | If blocked, do NOT call Bedrock. Return a validation error asking the user to edit and resubmit. Only validated, secret-free text is transmitted. |
| **Client-side feedback** | On free-text input (JavaScript) | Immediate feedback to the user before they submit. Non-authoritative — the server-side check is the real enforcement point. |

Client-side checking provides immediate UX feedback, but server-side validation is authoritative. If likely credential material is detected server-side, the field is rejected and a validation message is returned instead of saving.

### 9.5 What This Is NOT

- It is not a full secret scanner or DLP system. It does not detect Base64-encoded secrets, environment variable dumps, or obfuscated credentials.
- It does not encrypt stored data (SQLite stores plain text — acceptable for the MVP since no secrets should be entered).
- It does not implement rate limiting or WAF (no auth for the MVP).
- It does not audit-log every action.
- It does not detect every possible secret format — it catches obvious accidental submission ("password is hunter2", "API key: sk-abc123") while allowing legitimate mentions ("password reset instructions are in the binder").

These are deliberate non-goals. The objective is to prevent obvious accidental secret submission, not to build a comprehensive DLP system. Over-engineering detection would not meaningfully improve security for a hackathon MVP.

### 9.6 Security in the AI Path

- **Pre-transmission check (primary defense):** All user free-text answers are inspected by `secret_check.validate_answers()` BEFORE calling Bedrock. If likely secret material is detected, the application does NOT call Bedrock — it asks the user to edit and resubmit.
- **System prompt (defense in depth):** The AI system prompt still instructs the model to never output or request credentials. This is a secondary defense, not the primary one. The application does NOT rely on the LLM to remove secrets after they have already been transmitted.
- **No existing secrets sent:** The application does not send any existing database secrets to Bedrock (because none should exist).
- **Untrusted AI responses:** Bedrock responses are treated as untrusted data — they are validated against the expected JSON schema before being used to create records. Any free-text fields in AI-proposed records are also passed through the secret check before persistence.

---

## 10. Demo Data

### 10.1 Organization

| Field | Value |
|---|---|
| Name | Grace Community Church |
| Type | church |
| Size | ~200 members |
| Description | A community church with weekly Sunday services, an active social media presence, and online giving. |

### 10.2 People

| ID | Name | Role Title | Email |
|---|---|---|---|
| 1 | Dami | Technology Coordinator | dami@gracecommunity.example |
| 2 | James | Media Volunteer | james@gracecommunity.example |
| 3 | Sarah | Church Administrator | sarah@gracecommunity.example |
| 4 | Pastor John | Pastor | john@gracecommunity.example |

### 10.3 Assets

| ID | Name | Category | Criticality | Description |
|---|---|---|---|---|
| 1 | Sunday Livestream | livestream | Critical | Weekly Sunday service livestream via OBS |
| 2 | Church Website | website | High | WordPress site with sermon archives and event calendar |
| 3 | Church Instagram | social_media | Medium | Official Instagram account for announcements and outreach |
| 4 | Wi-Fi Network | network_wifi | High | Office and guest Wi-Fi, router configuration |
| 5 | Donation Platform | payment | Critical | Online giving platform (Stripe-based) |
| 6 | Google Drive | data_storage | High | Shared files: bulletins, service plans, financial records |
| 7 | Audio System | livestream | Medium | Sound board and speakers for in-person service |
| 8 | Presentation Laptop | other | Medium | Laptop used for slides and announcements during service |

### 10.4 Responsibilities and Backup

| Asset | Primary Person | Type | Backup Status | Backup Person(s) |
|---|---|---|---|---|
| Sunday Livestream | Dami | Manages | `no_backup` | — |
| Sunday Livestream | James | Understands | `has_backup` | Sarah |
| Church Website | Dami | Administers | `has_backup` | Sarah |
| Church Instagram | Sarah | Manages | `backup_unknown` | — |
| Wi-Fi Network | Dami | Manages | `no_backup` | — |
| Donation Platform | Sarah | Administers | `has_backup` | Pastor John |
| Google Drive | Sarah | Manages | `has_backup` | Dami |
| Audio System | James | Manages | `has_backup` | Dami |
| Audio System | James | Understands | `no_backup` | — |
| Presentation Laptop | Dami | Manages | `no_backup` | — |

### 10.5 Documentation Status

| Asset | Docs Status | Location Note |
|---|---|---|
| Sunday Livestream | `no` | — |
| Church Website | `yes` | Google Drive > IT folder |
| Church Instagram | `no` | — |
| Wi-Fi Network | `no` | — |
| Donation Platform | `no` | — |
| Google Drive | `yes` | Google Drive > Admin folder |
| Audio System | `unknown` | — |
| Presentation Laptop | `no` | — |

### 10.6 Dependency Flags

| Asset | Personal Account | Note | Single Device | Note |
|---|---|---|---|---|
| Sunday Livestream | No | — | Yes | Livestream laptop in the sound booth |
| Church Website | No | — | No | — |
| Church Instagram | No | — | No | — |
| Wi-Fi Network | Yes | Router admin under Dami's personal email | No | — |
| Donation Platform | No | — | Yes | Only accessible from the office laptop |
| Google Drive | No | — | No | — |
| Audio System | No | — | No | — |
| Presentation Laptop | No | — | Yes | The laptop itself is the single device |

### 10.7 Intentional Continuity Problems (For Demo Impact)

| Problem | Where It Shows Up |
|---|---|
| Dami is the only person who can Manage the livestream | Critical risk, What If shows orphaned if Dami unavailable |
| Wi-Fi router is under Dami's personal email | Personal account dependency on High asset |
| Presentation Laptop managed only by Dami | `no_backup` + single device dependency |
| Donation Platform is Critical but only on one laptop | Critical + single device + no documentation |
| Instagram backup is unknown | Uncertainty risk — can't confirm coverage |
| Audio System: James Understands but with no backup | If James leaves, audio knowledge is lost |

### 10.8 Risk Score Calculation (Demo Verification)

| Asset | Base | Backup Penalty | Doc Penalty | Acct Penalty | Device Penalty | Total | Level |
|---|---|---|---|---|---|---|---|
| Sunday Livestream | 45 (Crit) | +15 (1× no_backup) | +15 (no) | +0 | +10 | **85** | Critical |
| Church Website | 30 (High) | +0 (has_backup) | +0 (yes) | +0 | +0 | **30** | Medium |
| Church Instagram | 18 (Med) | +7 (backup_unknown) | +15 (no) | +0 | +0 | **40** | Medium |
| Wi-Fi Network | 30 (High) | +15 (no_backup) | +15 (no) | +15 | +0 | **75** | Critical |
| Donation Platform | 45 (Crit) | +0 (has_backup) | +15 (no) | +0 | +10 | **70** | High |
| Google Drive | 30 (High) | +0 (has_backup) | +0 (yes) | +0 | +0 | **30** | Medium |
| Audio System | 18 (Med) | +15 (1× no_backup) | +7 (unknown) | +0 | +0 | **40** | Medium |
| Presentation Laptop | 18 (Med) | +15 (no_backup) | +15 (no) | +0 | +10 | **58** | High |

**Organization risk:** 2 Critical assets (Livestream 85, Wi-Fi 75) → **Organization = Critical**

### 10.9 What If Simulation (Dami Unavailable) — Demo Verification

Dami is primary on: Sunday Livestream (Manages, no_backup), Church Website (Administers, has_backup Sarah), Wi-Fi Network (Manages, no_backup), Presentation Laptop (Manages, no_backup).

| Asset | P's Responsibilities | Other People | Classification | Simulated Score |
|---|---|---|---|---|
| Sunday Livestream | Manages → no_backup → **lost** | James (Understands, still active) | **Partially affected** | 85 + 25 = 100 (Critical) |
| Church Website | Administers → has_backup Sarah → **covered** | None | **Unaffected** | 30 (unchanged) |
| Wi-Fi Network | Manages → no_backup → **lost** | None | **Orphaned** | 100 (Critical) |
| Presentation Laptop | Manages → no_backup → **lost** | None | **Orphaned** | 100 (Critical) |

Assets not involving Dami (Instagram, Donation Platform, Google Drive, Audio System) are unaffected.

**Simulated org risk:** Livestream (100 Critical), Wi-Fi (100 Critical), Presentation Laptop (100 Critical), Donation Platform (70 High), Presentation Laptop (58 High) → 3 Critical assets → **Organization = Critical** (escalated from 2 to 3 Critical)

**Demo narrative:** "If Dami becomes unavailable, the Wi-Fi network and presentation laptop are completely orphaned — nobody else can manage them. The livestream loses its management (though James still understands it). Only the website survives because Sarah is the backup. This is why backup coverage matters."

### 10.10 Seeding

`app/demo/seed.py` provides `seed_demo_data(db: Session)` that:
1. Checks if data already exists (idempotent — won't duplicate on re-run)
2. Creates the organization record
3. Creates all 4 people
4. Creates all 8 assets
5. Creates all 10 responsibilities with backup people
6. Creates documentation records for all assets
7. Creates dependency records for all assets

Called on application startup if `SEED_DEMO_DATA=true` in env (default: `true` for hackathon). Can be disabled for a clean database.

---

## 11. MVP Screens

### 11.1 Navigation

All pages extend `base.html` which includes:
- Top navigation bar: **Dashboard | Guided Discovery | People | Assets | Risk | Map | What If | Recommendations**
- Organization name in the top-left corner
- Pico CSS (or similar lightweight CSS framework) for base styling
- `static/css/style.css` for custom risk-level colors, badges, and layout
- Flash message area for save confirmations and warnings

### 11.2 Screen 1 — Welcome / Organization Setup

**Route:** `GET /` (redirects to setup if no org exists, dashboard if org exists)

**Layout:**
- Centered card on a clean page
- Title: "WithinReach Continuity"
- Subtitle: "Map your organization's technology dependencies before they become emergencies."
- Form fields:
  - Organization name (text, required)
  - Organization type (dropdown: Church, Nonprofit, Student Organization, Family Business, Other)
  - Size (text, optional, placeholder: "e.g., 200 members")
  - Description (textarea, optional)
- Button: "Get Started" → creates org, redirects to Dashboard
- Link: "Load Demo Data" (seeds Grace Community Church, redirects to Dashboard)

**Post-submit:** Redirect to Dashboard. If demo data was loaded, redirect to Dashboard with all data pre-populated.

### 11.3 Screen 2 — Dashboard

**Route:** `GET /dashboard`

**Layout:**
- Page title: Organization name + type badge
- Row of stat cards:
  - **People count** (e.g., "4 People")
  - **Assets count** (e.g., "8 Assets")
  - **Overall Risk** (large colored badge: Critical/High/Medium/Low)
- Quick action buttons:
  - "Start Guided Discovery" (primary, highlighted)
  - "Add Person"
  - "Add Asset"
- Top 3 risks panel: Three highest-risk assets with their risk level badges and one-line descriptions
- Navigation cards linking to: People, Assets, Risk View, Dependency Map, What If, Recommendations

### 11.4 Screen 3 — Guided Discovery

**Routes:**
- `GET /interview` → Intro page
- `GET /interview/{category_index}` → Category question page
- `POST /api/interview/interpret` → AI interpretation (AJAX, returns proposed records JSON)
- `POST /interview/save` → Save confirmed records (form post, redirects to Dashboard)

**Intro page layout:**
- Title: "Guided Dependency Discovery"
- Explanation: "We'll walk you through your organization's technology areas one at a time. You'll answer simple questions about each one, review the records we propose, and confirm what to save."
- Security notice: "We will never ask for passwords, keys, or tokens. Please do not enter them."
- Button: "Begin Interview" → goes to category 1

**Category page layout:**
- Progress indicator: "Category 2 of 8: Website / Domain"
- Question flow (structured form or AI-assisted free text, depending on `AI_ENABLED`)
- For each question: label, input field, and for free-text fields, a "Do not enter secrets" note
- Conditional questions appear/disappear based on previous answers (JS)
- Buttons: "Back" / "Skip" / "Next Category"
- After completing a category with AI: proposed records panel appears (AJAX), user reviews inline

**Review page layout:**
- Title: "Review Proposed Records"
- List of all proposed records grouped by category
- Each record: editable fields, accept checkbox (checked by default), reject button
- Duplicate detection: "Person 'Dami' already exists — use existing or create new?"
- Security check: any field flagged by `secret_check.py` shows a warning
- Button: "Save Confirmed Records" → POST, redirect to Dashboard
- Button: "Back to Interview" (returns to last category)

### 11.5 Screen 4 — People

**Routes:**
- `GET /people` → List
- `GET /people/{id}` → Detail
- `GET /people/new` → Add form
- `POST /people/new` → Create
- `GET /people/{id}/edit` → Edit form
- `POST /people/{id}/edit` → Update
- `POST /people/{id}/delete` → Delete (with confirmation)

**List layout:**
- Title: "People"
- Table or card grid: Name, Role, # Primary Responsibilities, # Backup Roles
- Each row/card links to person detail
- "Add Person" button

**Detail layout:**
- Person name and role title
- Contact email (if provided)
- Section: "Primary Responsibilities" — list of assets, responsibility type, backup status (and backup person names)
- Section: "Backup Roles" — list of assets where this person is a backup, primary person name, responsibility type
- Risk exposure indicator: "This person is a single point of failure for X critical assets" (if applicable)
- Buttons: Edit, Delete (with dependency warning)

### 11.6 Screen 5 — Assets

**Routes:**
- `GET /assets` → List
- `GET /assets/{id}` → Detail
- `GET /assets/new` → Add form
- `POST /assets/new` → Create
- `GET /assets/{id}/edit` → Edit form
- `POST /assets/{id}/edit` → Update
- `POST /assets/{id}/delete` → Delete (with confirmation)

**List layout:**
- Title: "Technology Assets"
- Card grid: each card shows asset name, category badge, criticality badge, risk level badge (color-coded)
- Sort/filter: by risk level (default: Critical first) or by category
- "Add Asset" button

**Detail layout:**
- Asset name, category, criticality, description
- Risk score panel: score (0–100), risk level badge, contributing factors breakdown (list with point values)
- Section: "Responsibilities" — table of primary people (name, type, backup status, backup person names)
- Section: "Documentation" — status (yes/no/unknown), location note
- Section: "Dependencies" — personal account flag + note, single device flag + note
- "Add Responsibility" button (links person to this asset)
- "Edit Documentation" / "Edit Dependencies" buttons
- Buttons: Edit Asset, Delete Asset

### 11.7 Screen 6 — Risk View

**Route:** `GET /risk`

**Layout:**
- Title: "Continuity Risk Assessment"
- Overall risk panel: large risk level badge (Critical/High/Medium/Low) + explanation text
- Score distribution bar: visual showing count of assets at each risk level
- Risks grouped by level, highest first:

**Critical section** (red heading):
- Each asset card: name, score, one-line risk description, contributing factors list
- Expandable: click to show full factor breakdown with point values

**High section** (orange heading):
- Same format

**Medium section** (yellow heading):
- Same format

**Low section** (green heading):
- Same format

- "Generate Recommendations" button → links to Recommendations page

### 11.8 Screen 7 — Dependency Map

**Route:** `GET /map`

**Layout:**
- Title: "Dependency Map"
- Legend (static HTML, see section 7.9)
- Cytoscape.js graph container (full width, ~600px height)
- Below the graph: "Single Points of Failure" summary panel listing people who are SPOFs with their critical asset count

**Behavior:**
- Graph renders on page load (fetches JSON from `/api/dependency-map`)
- Click person → navigate to `/people/{id}`
- Click asset → navigate to `/assets/{id}`
- Hover → tooltip with quick info

### 11.9 Screen 8 — What If Simulator

**Route:** `GET /simulator`

**Layout:**
- Title: "What If Simulator"
- Control panel:
  - Dropdown: "Select a person" (lists all people with their role)
  - Button: "Run Simulation"
- Results panel (initially hidden, shown after simulation):

**Results layout:**
- Comparison banner: "Current Risk: [Critical] → Simulated Risk: [Critical]" (with color badges)
- Section: "Orphaned Assets" (red) — assets with no surviving coverage
  - Each: asset name, which responsibilities lost, "No backup person recorded"
- Section: "Partially Affected Assets" (orange) — assets with some coverage lost
  - Each: asset name, responsibilities lost, responsibilities still covered, surviving backup names
- Section: "Unaffected Assets" (green) — assets where backup covers
  - Each: asset name, backup person name who covers
- Section: "Unaffected (Not Involved)" — assets where the person has no role (collapsed by default)

**Interaction:**
- User selects a person and clicks "Run Simulation"
- AJAX call to `POST /api/simulate` with `{person_id}`
- Results render in the panel below without page reload

### 11.10 Screen 9 — Recommendations

**Route:** `GET /recommendations`

**Layout:**
- Title: "Recommendations"
- Button: "Generate Recommendations" (triggers AI or fallback)
- After generation:
  - Mode indicator: "AI-assisted" or "Rule-based (AI unavailable)"
  - Recommendations list, sorted by priority (Critical first):
    - Each recommendation card:
      - Priority badge (Critical/High/Medium/Low)
      - Asset name and person name referenced
      - Risk description (what the problem is)
      - Recommendation (what to do)
      - Rationale (why it matters)
      - Link: "View risk details" → links to risk view for that asset
- If no risks exist: "No risks detected — your organization's technology dependencies are well-covered."

---

## 12. Testing Strategy

### 12.1 Approach

Tests use `pytest` with an in-memory SQLite database fixture. Each test gets a fresh database with seed data. Tests focus on the core business logic — the parts that would be most embarrassing if broken during a demo.

### 12.2 Test Files

#### test_risk_scoring.py

Tests the deterministic scoring engine in `risk_scoring.py`.

| Test | Description |
|---|---|
| `test_critical_asset_no_backup_no_docs_all_deps` | Score = 100, level = Critical |
| `test_low_asset_full_coverage` | Score = 8, level = Low |
| `test_high_asset_backup_unknown_no_docs` | Score = 52, level = High |
| `test_critical_asset_full_coverage` | Score = 45, level = Medium |
| `test_medium_asset_no_backup_single_device` | Score = 18 + 15 + 15 + 10 = 58, level = High |
| `test_backup_penalty_cap_at_30` | Asset with 3 no_backup responsibilities: penalty = 3×15 = 45, capped at 30 |
| `test_score_capped_at_100` | All penalties maxed: score = min(total, 100) |
| `test_threshold_boundaries` | 24 → Low, 25 → Medium, 49 → Medium, 50 → High, 74 → High, 75 → Critical |
| `test_org_risk_one_critical` | 1 Critical asset → org = Critical |
| `test_org_risk_three_high_no_critical` | 3 High assets, no Critical → org = Critical (accumulation rule) |
| `test_org_risk_one_high` | 1 High asset, no Critical → org = High |
| `test_org_risk_all_medium` | All Medium → org = Medium |
| `test_org_risk_all_low` | All Low → org = Low |
| `test_contributing_factors_returned` | Result includes list of ContributingFactor with labels and points |

#### test_backup_relationships.py

Tests the backup-person data model and service operations.

| Test | Description |
|---|---|
| `test_create_responsibility_with_backup` | Create responsibility with `has_backup`, add backup person, verify link |
| `test_create_responsibility_no_backup` | Create with `no_backup`, verify no backup people |
| `test_create_responsibility_backup_unknown` | Create with `backup_unknown`, verify no backup people |
| `test_change_backup_status_removes_backups` | Change from `has_backup` to `no_backup` → ResponsibilityBackup rows deleted |
| `test_multiple_backup_people` | One responsibility with 2 backup people → both linked |
| `test_person_is_primary_and_backup_on_different_responsibilities` | Person A is primary on asset 1 and backup on asset 2 |
| `test_remove_person_removes_primary_and_backup_links` | Delete person → their primary responsibilities and backup associations removed |
| `test_duplicate_backup_prevented` | Same person added as backup twice → unique constraint prevents duplicate |
| `test_unique_constraint_responsibility` | Same person + type + asset → unique constraint prevents duplicate |

#### test_simulator.py

Tests the What If simulation algorithm.

| Test | Description |
|---|---|
| `test_orphaned_asset` | P is sole primary, `no_backup`, no other people on asset → orphaned, simulated score = 100 |
| `test_unaffected_asset` | P is primary, `has_backup` with surviving backup → unaffected, score unchanged |
| `test_partially_affected_no_backup` | P has `no_backup` but other people still on asset → partially affected, score + 25 |
| `test_partially_affected_backup_unknown` | P has `backup_unknown` → partially affected, score + 25 |
| `test_backup_is_same_person` | `has_backup` but backup person = P (edge case) → treated as lost, partially affected or orphaned |
| `test_person_not_involved` | P has no responsibilities on asset → asset not in results |
| `test_simulated_org_risk` | After simulation, org risk recalculated from modified scores |
| `test_demo_data_dami_simulation` | Run simulation on demo data with Dami → verify: Wi-Fi orphaned, Website unaffected, Livestream partially affected, Presentation Laptop orphaned |
| `test_simulated_score_capped` | Partially affected: min(current + 25, 100) — if current is 85, simulated = 100 (not 110) |

#### test_secret_handling.py

Tests the security boundary — blocking behavior, pattern detection, and false-positive avoidance.

| Test | Description |
|---|---|
| `test_no_secret_fields_in_forms` | Verify no input field has name containing "password", "key", "token", "secret", "credential" |
| `test_secret_keyword_and_value_blocks` | `check_for_secrets("the Wi-Fi password is hunter2")` → blocked=True (keyword "wi-fi password" + value pattern "is hunter2") |
| `test_secret_colon_value_blocks` | `check_for_secrets("API key: sk-abc123xyz")` → blocked=True |
| `test_secret_equals_value_blocks` | `check_for_secrets("token = abc123def")` → blocked=True |
| `test_no_false_positive_on_benign_text` | `check_for_secrets("Google Drive > IT folder")` → blocked=False (no keyword match) |
| `test_no_false_positive_on_mention` | `check_for_secrets("The password reset procedure is documented in the IT binder")` → blocked=False (keyword "password" present but no value-supply pattern) |
| `test_blocks_before_db_save` | Server-side: free-text field with likely secret → field rejected, validation error returned, record NOT saved |
| `test_blocks_before_ai_transmission` | Interview answer with likely secret → `validate_answers()` returns invalid, Bedrock is NOT called, user asked to edit |
| `test_ai_proposed_records_checked_before_save` | Free-text fields in AI-proposed records pass through secret check before persistence |
| `test_no_secret_columns_in_schema` | Verify all model fields — none designed to hold secrets |

#### test_ai_fallback.py

Tests graceful degradation when AI is unavailable.

| Test | Description |
|---|---|
| `test_recommendations_fallback_when_ai_disabled` | `AI_ENABLED=false` → rule-based recommendations returned |
| `test_recommendations_fallback_on_bedrock_error` | Bedrock raises exception → rule-based recommendations returned, no error to user |
| `test_interview_structured_fallback_when_ai_disabled` | `AI_ENABLED=false` → structured form answers mapped directly to proposed records |
| `test_interview_fallback_on_bedrock_error` | Bedrock raises exception → structured fallback used |
| `test_interview_secret_blocks_before_bedrock` | Answer with likely secret → Bedrock NOT called, validation error returned, user asked to edit |
| `test_fallback_recommendations_reference_specific_assets` | Rule-based recommendation includes asset name and person name |
| `test_fallback_recommendations_prioritized` | Critical asset recommendations before High, before Medium |

### 12.3 Test Configuration

```python
# tests/conftest.py

@pytest.fixture
def db():
    """In-memory SQLite for each test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = SessionLocal(bind=engine)
    yield session
    session.close()

@pytest.fixture
def seeded_db(db):
    """Database with Grace Community Church demo data."""
    seed_demo_data(db)
    return db

@pytest.fixture
def client(db):
    """FastAPI test client with test database."""
    # Override get_db dependency to use test session
    ...
```

### 12.4 What Is NOT Tested (MVP)

- UI rendering (templates) — manual testing is sufficient for a hackathon
- Cytoscape.js client-side rendering — manual testing
- Bedrock API responses — mocked in tests; real integration tested manually
- Performance/load testing — NFR-3 is validated manually
- Authentication — not implemented for MVP

---

## Appendix A — Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./continuity.db` | SQLAlchemy database URL |
| `AI_ENABLED` | `false` | Master toggle for Bedrock AI features |
| `BEDROCK_MODEL_ID` | `anthropic.claude-3-haiku-20240307-v1:0` | Bedrock model ID — example default in `.env.example`; configurable and swappable. Application must not assume this exact model is always available. |
| `BEDROCK_REGION` | `us-east-1` | AWS region for Bedrock |
| `SEED_DEMO_DATA` | `true` | Seed Grace Community Church on startup |

## Appendix B — Requirements Traceability

| Requirement | Design Section |
|---|---|
| FR-1 Organization Profile | §3.3 Organization, §11.2 Screen 1 |
| FR-2 People & Roles | §3.3 Person, §11.5 Screen 4 |
| FR-3 Technology Assets | §3.3 Asset, §11.6 Screen 5 |
| FR-4 Responsibility Mapping | §3.3 Responsibility + ResponsibilityBackup, §4.2 Backup penalty, §5 Simulator |
| FR-5 Documentation Tracking | §3.3 AssetDocumentation, §11.6 Screen 5 |
| FR-6 Personal Account / Single Device | §3.3 AssetDependency, §4.2 Dependency penalties |
| FR-7 Service Criticality | §3.3 Asset.criticality, §4.2 Base score |
| FR-8 Continuity Risk Score | §4 Risk Scoring Design (full) |
| FR-9 Risk Display | §11.7 Screen 6 |
| FR-10 What If Simulator | §5 What If Simulator (full), §11.9 Screen 8 |
| FR-11 Recommendations | §8.3 Use Case 2, §11.10 Screen 9 |
| FR-12 Security Boundary | §9 Security Design (full) |
| FR-13 Guided Discovery | §6 Guided Dependency Discovery (full), §11.4 Screen 3 |
| FR-14 Visual Dependency Map | §7 Visual Dependency Map (full), §11.8 Screen 7 |
