# WithinReach Continuity — Implementation Tasks

**Reference:** [requirements.md](./requirements.md) | [design.md](./design.md)
**Convention:** Each task marked **MVP REQUIRED** or **STRETCH**. All Tier 1 features are MVP REQUIRED.

---

## Phase 1 — Foundation

> **Goal:** A runnable FastAPI app with SQLite, SQLAlchemy models, base templates, and startup initialization. No business logic yet — just the skeleton.

### Task 1.1 — Create project structure [MVP REQUIRED]
**Objective:** Create the directory and file layout from design §2.
**Files created:**
- `app/__init__.py`, `app/models/__init__.py`, `app/schemas/__init__.py`
- `app/routes/__init__.py`, `app/services/__init__.py`
- `app/security/__init__.py`, `app/demo/__init__.py`
- `templates/`, `static/css/`, `static/js/`
- `tests/__init__.py`
- `requirements.txt`, `.env.example`

**Acceptance:** All directories and `__init__.py` files exist. Project imports `app` without errors.
**Dependencies:** None.

### Task 1.2 — Create requirements.txt [MVP REQUIRED]
**Objective:** Pin all Python dependencies.
**Files modified:** `requirements.txt`
**Contents:**
- `fastapi`, `uvicorn[standard]`, `sqlalchemy`, `pydantic`, `pydantic-settings`, `jinja2`, `python-multipart`, `boto3`, `pytest`, `httpx`

**Acceptance:** `pip install -r requirements.txt` succeeds.
**Dependencies:** Task 1.1.

### Task 1.3 — Create configuration module [MVP REQUIRED]
**Objective:** Pydantic Settings reading from environment variables per design §8.6 and Appendix A.
**Files created:** `app/config.py`, `.env.example`
**Settings:** `DATABASE_URL` (default `sqlite:///./continuity.db`), `AI_ENABLED` (default `false`), `BEDROCK_MODEL_ID` (example default, configurable), `BEDROCK_REGION` (default `us-east-1`), `SEED_DEMO_DATA` (default `true`).
**Acceptance:** `from app.config import settings` works. Settings read from `.env` file or environment. Model ID is explicitly documented as configurable and swappable, not hard-coded.
**Dependencies:** Task 1.1.

### Task 1.4 — Create database module [MVP REQUIRED]
**Objective:** SQLAlchemy engine, session factory, declarative base, and FastAPI `get_db` dependency per design §3.
**Files created:** `app/database.py`
**Contents:** `create_engine`, `SessionLocal` factory, `Base` (declarative base), `get_db()` generator for FastAPI dependency injection. Use SQLite with `check_same_thread=False`.
**Acceptance:** Can create an engine and get a session. `Base.metadata.create_all(engine)` runs without error (no tables yet).
**Dependencies:** Task 1.3.

### Task 1.5 — Create SQLAlchemy models [MVP REQUIRED]
**Objective:** All 7 ORM model classes matching design §3.3 schema exactly.
**Files created:**
- `app/models/organization.py` — Organization
- `app/models/person.py` — Person
- `app/models/asset.py` — Asset
- `app/models/responsibility.py` — Responsibility + ResponsibilityBackup
- `app/models/asset_documentation.py` — AssetDocumentation
- `app/models/asset_dependency.py` — AssetDependency
- `app/models/__init__.py` — Re-export all models

**Key details:** All enums as strings with CHECK constraints. FKs with cascade deletes (responsibility → asset, responsibility_backup → responsibility, documentation/dependency → asset). Unique constraints: `(asset_id, primary_person_id, responsibility_type)` on Responsibility, `(responsibility_id, backup_person_id)` on ResponsibilityBackup, `asset_id` UNIQUE on AssetDocumentation and AssetDependency. Timestamps on all models.
**Acceptance:** `Base.metadata.create_all(engine)` creates all 7 tables with correct columns, constraints, and FKs. Can query each table.
**Dependencies:** Task 1.4.

### Task 1.6 — Create base Jinja2 templates [MVP REQUIRED]
**Objective:** Base layout with navigation bar, CSS framework, and flash message area per design §11.1.
**Files created:**
- `templates/base.html` — Nav bar (Dashboard, Guided Discovery, People, Assets, Risk, Map, What If, Recommendations), org name, Pico CSS via CDN, custom `static/css/style.css`, flash messages, content block
- `static/css/style.css` — Risk-level color classes (critical=red, high=orange, medium=yellow, low=green), badge styles, card layouts
- A placeholder `templates/dashboard.html` that extends base (will be fleshed out in Phase 3)

**Acceptance:** `base.html` renders with nav bar and CSS. A child template extending it displays content in the content block.
**Dependencies:** Task 1.1.

### Task 1.7 — Create FastAPI application entrypoint [MVP REQUIRED]
**Objective:** FastAPI app with Jinja2 templates, static file mounting, and router registration per design §1.
**Files created:** `app/main.py`
**Contents:** Create FastAPI app, configure Jinja2Templates pointing to `templates/`, mount `static/` directory, include routers (initially just a placeholder page router), startup event that calls `Base.metadata.create_all()` and optionally seeds demo data.
**Acceptance:** `uvicorn app.main:app` starts. `GET /` returns a rendered page (even if placeholder). Static CSS loads.
**Dependencies:** Tasks 1.3, 1.4, 1.5, 1.6.

### Task 1.8 — Create Pydantic schemas [MVP REQUIRED]
**Objective:** Request/response schemas for all entities and risk results per design §2.
**Files created:**
- `app/schemas/organization.py` — OrganizationCreate, OrganizationUpdate, OrganizationResponse
- `app/schemas/person.py` — PersonCreate, PersonUpdate, PersonResponse
- `app/schemas/asset.py` — AssetCreate, AssetUpdate, AssetResponse
- `app/schemas/responsibility.py` — ResponsibilityCreate, ResponsibilityUpdate, ResponsibilityResponse, ResponsibilityBackupCreate
- `app/schemas/risk.py` — ContributingFactor, AssetRiskResult, OrgRiskResult
- `app/schemas/interview.py` — InterviewAnswer, ProposedRecords, ConfirmedRecord
- `app/schemas/recommendation.py` — Recommendation, RecommendationRequest

**Acceptance:** All schemas import and validate. Can create a `PersonCreate` from a dict and access fields.
**Dependencies:** Task 1.5.

---

## Phase 2 — Demo Data

> **Goal:** Grace Community Church seed data so the app has content immediately. Must be reseatable.

### Task 2.1 — Create demo data seeder [MVP REQUIRED]
**Objective:** `seed.py` that creates the full Grace Community Church dataset from design §10.
**Files created:** `app/demo/seed.py`
**Function:** `seed_demo_data(db: Session)` — idempotent (checks if org exists by name before creating). Creates: 1 organization, 4 people (Dami, James, Sarah, Pastor John), 8 assets (Sunday Livestream, Church Website, Church Instagram, Wi-Fi Network, Donation Platform, Google Drive, Audio System, Presentation Laptop), 10 responsibilities with backup people, 8 documentation records, 8 dependency records. All values match design §10.2–§10.6 exactly.
**Acceptance:** Running `seed_demo_data(db)` creates all records. Running twice does not duplicate. Counts match: 4 people, 8 assets, 10 responsibilities, 8 docs, 8 deps.
**Dependencies:** Task 1.5.

### Task 2.2 — Wire seeding into startup [MVP REQUIRED]
**Objective:** Call `seed_demo_data` on application startup when `SEED_DEMO_DATA=true`.
**Files modified:** `app/main.py`
**Acceptance:** On first startup with a fresh DB, demo data is created. On restart, data persists (no duplication).
**Dependencies:** Task 2.1, Task 1.7.

### Task 2.3 — Add demo reset capability [MVP REQUIRED]
**Objective:** A way to wipe and reseed the database for demo purposes.
**Files created:** `app/demo/reset.py` with `reset_demo_data(db: Session)` that drops all data and re-seeds.
**Acceptance:** Can call `reset_demo_data(db)` at any time. After reset, the DB has exactly the Grace Community Church data. Will be exposed as a route in Phase 11.
**Dependencies:** Task 2.1.

---

## Phase 3 — Core Dashboard

> **Goal:** The app runs in the browser with a dashboard, basic people/asset lists, and navigation. By the end of this phase, the app is demoable with seeded data (no risk scoring yet).

### Task 3.1 — Create page routes and organization setup [MVP REQUIRED]
**Objective:** Page router with the welcome/setup screen and dashboard route per design §11.2, §11.3.
**Files created:**
- `app/routes/pages.py` — `GET /` (redirect to setup if no org, dashboard if org exists), `GET /setup` (render org setup form), `POST /setup` (create org, redirect to dashboard)
- `app/routes/organization.py` — Organization CRUD API (create, read, update)
- `app/services/organization_service.py` — `get_or_create_org()`, `get_organization()`, `update_organization()`
- `templates/organization_setup.html` — Form: name, type dropdown, size, description, "Get Started" button, "Load Demo Data" link

**Acceptance:** Fresh DB → `GET /` redirects to setup. Creating an org redirects to dashboard. "Load Demo Data" seeds and redirects to dashboard.
**Dependencies:** Phase 1, Task 2.2.

### Task 3.2 — Create dashboard page [MVP REQUIRED]
**Objective:** Dashboard with people count, asset count, navigation, and quick actions per design §11.3.
**Files created:**
- `templates/dashboard.html` — Org name + type badge, stat cards (people count, asset count, overall risk placeholder), quick action buttons (Start Guided Discovery, Add Person, Add Asset), navigation cards
- `app/services/person_service.py` — `count_people(org_id)`, `get_all_people(org_id)`
- `app/services/asset_service.py` — `count_assets(org_id)`, `get_all_assets(org_id)`

**Acceptance:** Dashboard shows correct people count (4) and asset count (8) with demo data. Navigation links work (even if target pages are placeholders). Overall risk badge shows "Pending" until Phase 4.
**Dependencies:** Task 3.1, Task 2.2.

### Task 3.3 — Create basic people list page [MVP REQUIRED]
**Objective:** People list with name, role, and responsibility counts per design §11.5.
**Files created:**
- `app/routes/people.py` — `GET /people` (list), `GET /people/{id}` (detail placeholder)
- `templates/people/list.html` — Table or card grid with name, role, # primary responsibilities, # backup roles
**Acceptance:** `/people` shows 4 people from demo data with correct names and roles.
**Dependencies:** Task 3.2.

### Task 3.4 — Create basic asset list page [MVP REQUIRED]
**Objective:** Asset list with name, category, and criticality badges per design §11.6.
**Files created:**
- `app/routes/assets.py` — `GET /assets` (list), `GET /assets/{id}` (detail placeholder)
- `templates/assets/list.html` — Card grid with name, category badge, criticality badge (color-coded)
**Acceptance:** `/assets` shows 8 assets from demo data with correct names, categories, and criticality badges.
**Dependencies:** Task 3.2.

### Task 3.5 — Polish base styling and navigation [MVP REQUIRED]
**Objective:** Consistent styling across all pages using Pico CSS + custom CSS.
**Files modified:** `static/css/style.css`, `templates/base.html`
**Contents:** Risk-level color badges (critical=red, high=orange, medium=yellow, low=green), card styles, responsive nav bar, spacing and typography polish.
**Acceptance:** All pages look consistent and polished. Nav bar highlights active section. Badges are color-coded.
**Dependencies:** Task 3.4.

### Task 3.6 — Verify end-to-end browser run [MVP REQUIRED]
**Objective:** Confirm the app runs and all Phase 3 pages render correctly.
**Action:** Start `uvicorn`, navigate through setup → dashboard → people → assets → back to dashboard. Verify demo data loads correctly.
**Acceptance:** App starts without errors. All pages render. Navigation works. Demo data is visible.
**Dependencies:** Task 3.5.

---

## Phase 4 — Risk Engine

> **Goal:** Deterministic risk scoring with explainable factors, displayed on the dashboard and a dedicated risk page.

### Task 4.1 — Implement per-asset risk scoring [MVP REQUIRED]
**Objective:** Pure function `calculate_asset_risk()` per design §4.2.
**Files created:** `app/services/risk_scoring.py`
**Algorithm:** Criticality base (Critical=45, High=30, Medium=18, Low=8) + backup penalty per responsibility (no_backup=+15, backup_unknown=+7, has_backup=+0, capped at 30) + documentation penalty (no=+15, unknown=+7, yes=+0) + personal account (+15) + single device (+10). Final score capped at 100. Thresholds: 0–24 Low, 25–49 Medium, 50–74 High, 75–100 Critical.
**Returns:** `AssetRiskResult` with `score`, `risk_level`, and `contributing_factors` list (each factor has label, points, detail).
**Acceptance:** All 8 demo assets produce scores matching design §10.8 verification table exactly (Livestream=85, Website=30, Instagram=40, Wi-Fi=75, Donation=70, Google Drive=30, Audio=40, Laptop=58).
**Dependencies:** Task 1.5, Task 1.8.

### Task 4.2 — Implement organization-level risk scoring [MVP REQUIRED]
**Objective:** `calculate_org_risk()` per design §4.4.
**Files modified:** `app/services/risk_scoring.py`
**Algorithm:** Compute all per-asset scores, then apply rules: ≥1 Critical → org Critical; ≥3 High (no Critical) → org Critical; ≥1 High (no Critical) → org High; ≥1 Medium (no Critical/High) → org Medium; all Low → org Low.
**Returns:** `OrgRiskResult` with `risk_level`, `score_distribution` (count per level), `top_risks` (sorted list of asset risks), and `overall_explanation`.
**Acceptance:** Demo data produces org = Critical (2 Critical assets). Score distribution matches: 2 Critical, 2 High, 4 Medium.
**Dependencies:** Task 4.1.

### Task 4.3 — Add risk scoring unit tests [MVP REQUIRED]
**Objective:** Tests for the scoring engine per design §12.2.
**Files created:** `tests/conftest.py`, `tests/test_risk_scoring.py`
**Test cases:** Critical+no_backup+no_docs+all_deps=100; Low+full_coverage=8; High+backup_unknown+no_docs=52; Critical+full_coverage=45; backup penalty cap at 30; score cap at 100; threshold boundaries (24/25/49/50/74/75); org aggregation rules (1 Critical, 3 High no Critical, 1 High, all Medium, all Low); contributing factors returned.
**Acceptance:** `pytest tests/test_risk_scoring.py` passes. All scores match design verification table.
**Dependencies:** Task 4.2.

### Task 4.4 — Display risk on dashboard [MVP REQUIRED]
**Objective:** Replace the "Pending" risk badge with the computed org risk level and show top 3 risks.
**Files modified:** `app/routes/pages.py`, `templates/dashboard.html`
**Acceptance:** Dashboard shows "Critical" badge (red) for demo data. Top 3 risks panel shows Livestream (85), Wi-Fi (75), Donation Platform (70) with risk level badges and one-line descriptions.
**Dependencies:** Task 4.2, Task 3.2.

### Task 4.5 — Create risk overview page [MVP REQUIRED]
**Objective:** Risk page with risks grouped by level per design §11.7.
**Files created:**
- `app/routes/risk.py` — `GET /risk` renders risk overview
- `templates/risk/overview.html` — Overall risk panel, score distribution bar, risks grouped by Critical/High/Medium/Low with expandable contributing-factor breakdowns
**Acceptance:** `/risk` shows all 8 assets grouped by risk level (2 Critical, 2 High, 4 Medium). Each asset shows score and contributing factors with point values. "Generate Recommendations" button links to recommendations page (placeholder for now).
**Dependencies:** Task 4.4.

---

## Phase 5 — People, Assets, Responsibilities

> **Goal:** Full CRUD for people, assets, responsibilities, documentation, and dependencies.

### Task 5.1 — People CRUD [MVP REQUIRED]
**Objective:** Add, edit, view, and delete people per design §11.5 and requirements Epic B.
**Files created/modified:**
- `app/routes/people.py` — Add `GET /people/new`, `POST /people/new`, `GET /people/{id}`, `GET /people/{id}/edit`, `POST /people/{id}/edit`, `POST /people/{id}/delete`
- `app/services/person_service.py` — `create_person()`, `get_person()`, `update_person()`, `delete_person()` with dependency warning (lists affected responsibilities and backup roles)
- `templates/people/form.html` — Add/edit form
- `templates/people/detail.html` — Person info, primary responsibilities list, backup roles list, SPOF indicator

**Acceptance:** Can add, edit, view, and delete a person. Delete shows warning listing affected assets. Person detail shows primary and backup responsibilities. SPOF indicator shows "single point of failure for X critical assets" when applicable.
**Dependencies:** Task 3.3.

### Task 5.2 — Asset CRUD [MVP REQUIRED]
**Objective:** Add, edit, view, and delete assets per design §11.6 and requirements Epic C.
**Files created/modified:**
- `app/routes/assets.py` — Add `GET /assets/new`, `POST /assets/new`, `GET /assets/{id}`, `GET /assets/{id}/edit`, `POST /assets/{id}/edit`, `POST /assets/{id}/delete`
- `app/services/asset_service.py` — `create_asset()`, `get_asset()`, `update_asset()`, `delete_asset()` (cascade deletes responsibilities, docs, deps)
- `templates/assets/form.html` — Add/edit form with name, category, criticality, description
- `templates/assets/detail.html` — Asset info, risk score panel (score, level, factors), responsibilities table, documentation section, dependencies section, action buttons

**Acceptance:** Can add, edit, view, and delete an asset. Asset detail shows risk score with contributing factors. Delete cascades to responsibilities, docs, and deps.
**Dependencies:** Task 3.4, Task 4.1.

### Task 5.3 — Responsibility mapping [MVP REQUIRED]
**Objective:** Assign responsibilities (person → asset with type and backup status) per design §3.3 and requirements Epic D.
**Files created:**
- `app/routes/responsibilities.py` — `POST /assets/{id}/responsibilities` (create), `POST /responsibilities/{id}/edit`, `POST /responsibilities/{id}/delete`
- `app/services/responsibility_service.py` — `create_responsibility()`, `update_responsibility()`, `delete_responsibility()`, `get_responsibilities_for_asset()`, `get_responsibilities_for_person()`
**Acceptance:** Can assign a person to manage/understand/administer an asset with backup status. Responsibility appears on both person detail and asset detail. Unique constraint prevents duplicates.
**Dependencies:** Task 5.1, Task 5.2.

### Task 5.4 — Backup-person assignment [MVP REQUIRED]
**Objective:** Link named backup people when backup status is `has_backup` per design §3.3.
**Files modified:** `app/services/responsibility_service.py`
**Logic:** When backup_status=`has_backup`, allow adding one or more backup people via `ResponsibilityBackup`. When backup_status changes to `no_backup` or `backup_unknown`, delete all `ResponsibilityBackup` rows for that responsibility. Same person can be primary on one responsibility and backup on another.
**Acceptance:** Can assign backup people to a responsibility. Changing to `no_backup` removes backup associations. A person appears as both primary and backup on different responsibilities in their detail view.
**Dependencies:** Task 5.3.

### Task 5.5 — Documentation tracking [MVP REQUIRED]
**Objective:** Record documentation status and optional location per design §3.3 and requirements Epic E.
**Files created:** `app/services/asset_service.py` (add `set_documentation()`, `get_documentation()`)
**Files modified:** `app/routes/assets.py` (add documentation endpoints), `templates/assets/detail.html` (add documentation section with edit form)
**Acceptance:** Can set documentation status (yes/no/unknown) and optional location note. Status displays on asset detail. Risk score updates when documentation changes.
**Dependencies:** Task 5.2, Task 4.1.

### Task 5.6 — Personal-account dependency flag [MVP REQUIRED]
**Objective:** Flag whether an asset depends on a personal account per design §3.3 and requirements Epic E.
**Files modified:** `app/services/asset_service.py` (add `set_dependency()`), `app/routes/assets.py`, `templates/assets/detail.html`
**Acceptance:** Can set `depends_on_personal_account` flag with optional note. Flag displays on asset detail. Risk score updates when flag changes.
**Dependencies:** Task 5.2, Task 4.1.

### Task 5.7 — Single-device dependency flag [MVP REQUIRED]
**Objective:** Flag whether an asset depends on a single device per design §3.3 and requirements Epic E.
**Files modified:** `app/services/asset_service.py`, `app/routes/assets.py`, `templates/assets/detail.html`
**Acceptance:** Can set `depends_on_single_device` flag with optional note. Flag displays on asset detail. Risk score updates when flag changes.
**Dependencies:** Task 5.2, Task 4.1.

---

## Phase 6 — What If Simulator

> **Goal:** Single-person simulation showing blast radius, asset classification, and simulated risk.

### Task 6.1 — Implement simulation algorithm [MVP REQUIRED]
**Objective:** `simulate_person_unavailable()` per design §5.2.
**Files created:** `app/services/simulator.py`
**Algorithm:** For each asset where P is primary on ≥1 responsibility: classify P's responsibilities as lost (no_backup or backup=P), at_risk (backup_unknown), or covered (has_backup with surviving backup person). Classify asset: orphaned (all lost, no other people, no covered), partially_affected (some lost or at_risk), unaffected (all covered).
**Returns:** `SimulationResult` with affected assets, classifications, lost/at_risk/covered details, surviving backup names.
**Acceptance:** Demo data with Dami: Livestream=partially_affected, Website=unaffected, Wi-Fi=orphaned, Laptop=orphaned. Matches design §10.9.
**Dependencies:** Task 5.4, Task 4.1.

### Task 6.2 — Calculate simulated risk score [MVP REQUIRED]
**Objective:** Compute simulated per-asset and org risk per design §5.4.
**Files modified:** `app/services/simulator.py`
**Algorithm:** Orphaned → 100. Partially affected → min(current + 25, 100). Unaffected → unchanged. Assets not involving P → unchanged. Recalculate org risk from modified scores.
**Acceptance:** Demo data with Dami: Livestream=100, Wi-Fi=100, Laptop=100, Website=30 (unchanged). Org stays Critical (3 Critical assets now).
**Dependencies:** Task 6.1, Task 4.2.

### Task 6.3 — Build simulator UI [MVP REQUIRED]
**Objective:** Simulator page with person selection and AJAX results per design §11.9.
**Files created:**
- `app/routes/simulation.py` — `GET /simulator` (page), `POST /api/simulate` (JSON endpoint)
- `templates/simulator.html` — Person dropdown, "Run Simulation" button, results panel with comparison banner, orphaned/partially/unaffected sections

**Acceptance:** Select Dami → run simulation → results show Wi-Fi and Laptop orphaned (red), Livestream partially affected (orange), Website unaffected (green). Comparison banner shows "Current: Critical → Simulated: Critical".
**Dependencies:** Task 6.2.

### Task 6.4 — Add simulation unit tests [MVP REQUIRED]
**Objective:** Tests for the simulator per design §12.2.
**Files created:** `tests/test_simulator.py`
**Test cases:** Orphaned asset (sole primary, no_backup, no others); unaffected (has_backup with surviving backup); partially_affected_no_backup; partially_affected_backup_unknown; backup_is_same_person edge case; person_not_involved; simulated_score_capped; demo data Dami simulation (verify exact classifications and scores).
**Acceptance:** `pytest tests/test_simulator.py` passes. All classifications and scores match design.
**Dependencies:** Task 6.2.

### Task 6.5 — Add backup relationship unit tests [MVP REQUIRED]
**Objective:** Tests for the backup-person data model per design §12.2.
**Files created:** `tests/test_backup_relationships.py`
**Test cases:** Create with has_backup + backup people; create with no_backup (no backups); create with backup_unknown (no backups); change backup_status removes backups; multiple backup people; person as primary and backup on different responsibilities; remove person removes links; duplicate backup prevented; unique constraint on responsibility.
**Acceptance:** `pytest tests/test_backup_relationships.py` passes.
**Dependencies:** Task 5.4.

---

## Phase 7 — Dependency Map

> **Goal:** Interactive visual map showing people → assets → functions with risk highlighting and click-through navigation.

### Task 7.1 — Create graph-data service [MVP REQUIRED]
**Objective:** Build Cytoscape-compatible JSON (nodes + edges) per design §7.2.
**Files created:** `app/services/dependency_map_service.py`
**Function:** `build_graph_data(db, org_id) → dict` — creates person nodes (circles, with risk_load, critical_asset_count, uncovered_count), asset nodes (rectangles, with risk_level, criticality), function nodes (category labels), and edges (person→asset with responsibility type, backup_status, edge_type=primary/backup; asset→function with category link).
**Acceptance:** Returns valid JSON with nodes and edges for all 4 people, 8 assets, and 8 categories. Edge colors encode backup status. Person nodes include risk_load and uncovered counts.
**Dependencies:** Task 5.4, Task 4.1.

### Task 7.2 — Create dependency map page and API [MVP REQUIRED]
**Objective:** Map page that loads Cytoscape.js and fetches graph data per design §11.8.
**Files created:**
- `app/routes/dependency_map.py` — `GET /map` (page), `GET /api/dependency-map` (JSON)
- `templates/dependency_map.html` — Cytoscape container, legend, SPOF summary panel
- `static/js/dependency_map.js` — Fetch graph data, initialize Cytoscape, apply styling (node shapes, edge colors, risk encoding), bind click events

**Acceptance:** `/map` renders a graph showing all people, assets, and function nodes connected by edges. Dami's node is visually prominent (connected to multiple critical assets with red/no_backup edges).
**Dependencies:** Task 7.1.

### Task 7.3 — Add risk visual encoding and SPOF highlighting [MVP REQUIRED]
**Objective:** Visually distinguish risky vs. healthy dependencies and highlight SPOFs per design §7.5–7.6.
**Files modified:** `static/js/dependency_map.js`
**Visual rules:** Asset border: red=Critical, orange=High, yellow=Medium, green=Low. Edge color: red=no_backup, orange=backup_unknown, green=has_backup. Primary edges solid, backup edges dashed. Person fill: red if connected to critical assets with no_backup, orange if backup_unknown, green if healthy. Person size scales with critical_asset_count. SPOF badge shows uncovered critical responsibility count.
**Acceptance:** Dami's node is red-filled and larger. Wi-Fi and Livestream edges from Dami are red. Website edge from Dami is green (has_backup Sarah). Sarah's Google Drive edge is green.
**Dependencies:** Task 7.2.

### Task 7.4 — Add click-through navigation [MVP REQUIRED]
**Objective:** Click person/asset nodes to navigate to detail pages per design §7.7.
**Files modified:** `static/js/dependency_map.js`
**Acceptance:** Clicking Dami navigates to `/people/1`. Clicking Sunday Livestream navigates to `/assets/1`. Function nodes have no click action. Hover shows tooltip with name, role/category, risk level.
**Dependencies:** Task 7.3.

### Task 7.5 — Add legend and SPOF summary [MVP REQUIRED]
**Objective:** Static legend explaining visual encoding and SPOF summary panel per design §7.9, §11.8.
**Files modified:** `templates/dependency_map.html`
**Acceptance:** Legend explains node types, edge styles, and color meanings. SPOF summary panel lists Dami as SPOF with "3 uncovered critical responsibilities."
**Dependencies:** Task 7.4.

---

## Phase 8 — Guided Dependency Discovery

> **Goal:** Structured (non-AI) guided interview that discovers dependencies, proposes records, and saves after user review. Must work without Bedrock.

### Task 8.1 — Define interview categories and question flow [MVP REQUIRED]
**Objective:** Category definitions and question templates per design §6.2, §6.3.
**Files created:** `app/services/interview_service.py`
**Contents:** `CATEGORIES` list (8 categories with key, label, display name), question definitions for each category (11 questions mapping to model fields), `get_category(index)` function.
**Acceptance:** Can retrieve category by index. Questions map to correct model fields (asset name → Asset.name, person → Person.name, backup → Responsibility.backup_status, etc.).
**Dependencies:** Task 5.3.

### Task 8.2 — Implement structured fallback mode [MVP REQUIRED]
**Objective:** Non-AI interview that maps form fields directly to proposed records per design §6.5.
**Files modified:** `app/services/interview_service.py`
**Function:** `structured_form_fallback(category_key, answers) → ProposedRecords` — maps form fields (asset_name, person_name, role_title, responsibility_type dropdown, backup radio, backup_person_name, docs radio, doc_location, single_device radio, personal_account radio) directly to the proposed records JSON structure.
**Acceptance:** Filling in structured form fields produces valid ProposedRecords with correct field mappings. No AI call needed.
**Dependencies:** Task 8.1.

### Task 8.3 — Build interview page flow [MVP REQUIRED]
**Objective:** Interview intro page, category question pages, and review/confirm page per design §11.4.
**Files created:**
- `app/routes/interview.py` — `GET /interview` (intro), `GET /interview/{category_index}` (category questions), `GET /interview/review` (review page), `POST /interview/save` (save confirmed records)
- `templates/interview/intro.html` — Title, explanation, security notice, "Begin Interview" button
- `templates/interview/category.html` — Progress indicator, structured form questions, "Back"/"Skip"/"Next" buttons
- `templates/interview/review.html` — Proposed records list with accept/reject/edit per record, duplicate detection, "Save Confirmed Records" button

**Acceptance:** Can walk through all 8 categories with structured forms. Each category shows correct questions. Skipping works. Progress indicator shows "X of 8."
**Dependencies:** Task 8.2.

### Task 8.4 — Implement review and confirm with duplicate handling [MVP REQUIRED]
**Objective:** Review page with per-record accept/reject/edit and duplicate detection per design §6.6.
**Files modified:** `app/routes/interview.py`, `templates/interview/review.html`
**Logic:** Each proposed record has accept checkbox (default checked), editable fields, reject button. Duplicate detection: if proposed person name matches existing person, offer "Use existing" or "Create new." Same for assets. Client-side state in sessionStorage accumulates proposed records across categories.
**Acceptance:** Proposed records appear in review with editable fields. Duplicate names are detected. User can reject records. Only accepted records are included in save payload.
**Dependencies:** Task 8.3.

### Task 8.5 — Add basic secret validation before save [MVP REQUIRED]
**Objective:** Validate free-text fields before saving interview records per design §9.3–9.4.
**Files created:** `app/services/secret_check.py` (initial version)
**Functions:** `check_for_secrets(text) → SecretCheckResult` (two-layer: keyword + value-supply pattern), `validate_free_text_fields(fields) → ValidationResult` (check all fields, return errors dict).
**Logic:** Block if keyword present AND value-supply pattern matches (e.g., "password is X"). Don't block benign mentions ("password reset instructions are in the binder"). Return user-friendly message: "Please remove passwords, access codes, API keys, tokens, recovery codes, or other credentials before continuing."
**Acceptance:** `"Wi-Fi password is hunter2"` → blocked. `"password reset procedure is in the binder"` → not blocked. `"Google Drive > IT folder"` → not blocked. If blocked, field is rejected and not saved.
**Dependencies:** Task 8.4.

### Task 8.6 — Save confirmed records to database [MVP REQUIRED]
**Objective:** Persist accepted records after secret validation per design §6.6, §6.8.
**Files modified:** `app/services/interview_service.py`
**Function:** `save_confirmed_records(db, org_id, confirmed)` — validates all free-text fields through secret_check (blocking), checks for duplicates, creates new or links to existing people/assets, creates responsibilities with backup people, creates documentation and dependency records.
**Acceptance:** Saving confirmed records creates correct DB entries. Duplicate handling links to existing person/asset when selected. Secret validation blocks fields with likely credentials. After save, records appear in people/asset lists.
**Dependencies:** Task 8.5, Task 5.4.

---

## Phase 9 — Amazon Bedrock

> **Goal:** AI-assisted interview interpretation and recommendation generation via Bedrock, with fallbacks that always work.

### Task 9.1 — Add configurable Bedrock integration [MVP REQUIRED]
**Objective:** `ai_service.py` wrapper for Bedrock per design §8.1, §8.6.
**Files created:** `app/services/ai_service.py`
**Functions:** `interpret_interview_answers(category_key, answers) → ProposedRecords` and `generate_recommendations(risk_profile) → list[Recommendation]`. Uses `boto3` client with configurable `BEDROCK_MODEL_ID` and `BEDROCK_REGION`. Raises on error so callers can fall back.
**Acceptance:** When `AI_ENABLED=false`, functions raise immediately (caller uses fallback). When enabled and Bedrock is configured, functions attempt the call. Model ID is read from settings, not hard-coded.
**Dependencies:** Task 1.3, Task 8.2.

### Task 9.2 — Add AI-assisted interview interpretation [MVP REQUIRED]
**Objective:** Send validated answers to Bedrock and parse proposed records per design §6.4, §8.2.
**Files modified:** `app/services/interview_service.py`, `app/routes/interview.py`
**Flow:** User answers free-text questions → `validate_answers()` checks for secrets (blocking) → if pass and AI enabled, call `ai_service.interpret_interview_answers()` → parse JSON → return proposed records → user reviews on review page. If AI fails or disabled, use `structured_form_fallback()`.
**Bedrock prompt:** System prompt instructs model to extract structured records, never include secrets, infer responsibility_type, default criticality to medium. User message contains category + answers. Expected output: JSON matching ProposedRecords schema.
**Acceptance:** With AI enabled and Bedrock available, free-text answers produce structured proposed records. With AI disabled, structured fallback works. Secret-containing answers never reach Bedrock.
**Dependencies:** Task 9.1, Task 8.5.

### Task 9.3 — Add AI-generated recommendations [MVP REQUIRED]
**Objective:** Generate continuity recommendations via Bedrock per design §8.3.
**Files created:**
- `app/services/recommendation_service.py` — `get_recommendations(db, org_id)` → builds risk profile, calls AI if enabled, falls back to rule-based
- `app/routes/recommendations.py` — `GET /recommendations` (page), `POST /api/recommendations` (generate)
- `templates/recommendations.html` — "Generate" button, mode indicator (AI-assisted vs rule-based), recommendation cards sorted by priority

**Rule-based fallback:** Templates per design §8.4 (no_backup, backup_unknown, no docs, personal account, single device), sorted by asset risk level, each referencing specific asset and person names.
**Acceptance:** With AI: recommendations are specific, reference asset/person names, prioritized by impact. Without AI: rule-based recommendations work and reference specific assets/people. UI shows which mode was used.
**Dependencies:** Task 9.1, Task 4.2.

### Task 9.4 — Validate AI output before use [MVP REQUIRED]
**Objective:** Treat Bedrock responses as untrusted data per design §9.6.
**Files modified:** `app/services/ai_service.py`, `app/services/recommendation_service.py`
**Logic:** Parse AI JSON response against expected schema. Validate all enum values (responsibility_type, backup_status, documentation status, etc.). Reject and fall back if parsing fails or schema is invalid. Run free-text fields in AI-proposed records through `secret_check` before persistence.
**Acceptance:** Malformed AI response → graceful fallback to rule-based/structured. Valid response → proposed records used. Free-text fields from AI pass through secret_check.
**Dependencies:** Task 9.2, Task 9.3, Task 8.5.

### Task 9.5 — Ensure pre-transmission secret check for Bedrock [MVP REQUIRED]
**Objective:** Never send detected secrets to Bedrock per design §8.2, §9.6.
**Files modified:** `app/services/interview_service.py`
**Logic:** Before calling `ai_service.interpret_interview_answers()`, call `secret_check.validate_answers(answers)`. If any answer fails, do NOT call Bedrock — return validation error asking user to edit. Only validated answers are transmitted. The AI system prompt still instructs the model not to output credentials (defense in depth).
**Acceptance:** Answer containing "password is hunter2" → Bedrock NOT called, validation error returned. Answer "password reset is in the binder" → passes check, Bedrock called. No secret-containing text reaches Bedrock.
**Dependencies:** Task 9.2, Task 8.5.

### Task 9.6 — Add AI fallback tests [MVP REQUIRED]
**Objective:** Tests for graceful degradation per design §12.2.
**Files created:** `tests/test_ai_fallback.py`
**Test cases:** Recommendations fallback when AI disabled; recommendations fallback on Bedrock error; interview structured fallback when AI disabled; interview fallback on Bedrock error; secret blocks before Bedrock call; fallback recommendations reference specific assets; fallback recommendations prioritized.
**Acceptance:** `pytest tests/test_ai_fallback.py` passes.
**Dependencies:** Task 9.4, Task 9.5.

---

## Phase 10 — Security Controls

> **Goal:** Comprehensive, authoritative secret detection — client-side feedback + server-side blocking validation at all persistence and transmission boundaries.

### Task 10.1 — Implement two-layer secret detection [MVP REQUIRED]
**Objective:** Full implementation of `secret_check.py` with keyword + pattern matching per design §9.3.
**Files modified:** `app/services/secret_check.py`
**Layer 1:** Sensitive-context keywords (password, passwd, pwd, api key, apikey, api_key, access token, auth token, bearer, secret key, private key, recovery code, wi-fi password, wifi password, credential, otp, 2fa code).
**Layer 2:** Value-supply regex patterns (keyword + "is"/":"/"=" + value). Block only when BOTH layers match.
**Functions:** `check_for_secrets(text) → SecretCheckResult` (blocked, matched_keywords, matched_patterns), `validate_free_text_fields(fields) → ValidationResult`, `validate_answers(answers) → ValidationResult`.
**Acceptance:** `"password is hunter2"` → blocked. `"API key: sk-abc123"` → blocked. `"token = xyz"` → blocked. `"The password reset procedure is in the binder"` → NOT blocked. `"Google Drive > IT folder"` → NOT blocked.
**Dependencies:** Task 8.5.

### Task 10.2 — Apply server-side validation to all DB save paths [MVP REQUIRED]
**Objective:** Authoritative secret validation before any free-text field is persisted to SQLite per design §9.4.
**Files modified:** `app/services/person_service.py`, `app/services/asset_service.py`, `app/services/responsibility_service.py`, `app/services/organization_service.py`
**Logic:** Before saving any free-text field (location_note, personal_account_note, single_device_note, description, org description), run through `secret_check.validate_free_text_fields()`. If blocked, reject the field and return a validation error instead of saving.
**Acceptance:** Free-text field with likely secret → rejected, not saved, validation error returned. Clean text → saved normally.
**Dependencies:** Task 10.1, Task 5.6.

### Task 10.3 — Apply server-side validation before Bedrock transmission [MVP REQUIRED]
**Objective:** Block secret-containing answers from reaching Bedrock per design §9.4, §9.6.
**Files modified:** `app/services/interview_service.py`
**Logic:** Already partially implemented in Task 9.5 — ensure this is the authoritative check. `validate_answers()` runs before any Bedrock call. If blocked, return 400 with user-friendly message, do NOT call Bedrock.
**Acceptance:** Server-side validation is authoritative. Even if client-side JS is bypassed, server rejects secret-containing text before Bedrock.
**Dependencies:** Task 10.1, Task 9.5.

### Task 10.4 — Add client-side secret warnings [MVP REQUIRED]
**Objective:** Immediate user feedback on free-text inputs per design §9.4.
**Files modified:** `templates/interview/category.html`, `templates/interview/review.html`, `templates/assets/form.html`, `templates/assets/detail.html`, `static/js/secret_warning.js` (or inline)
**Logic:** JavaScript checks free-text fields on blur/change for the same keyword+pattern logic. Shows warning message if likely secret detected. Non-authoritative — server validation is the real enforcement.
**Acceptance:** Typing "password is hunter2" in a free-text field shows the warning message immediately. Typing "password reset is in the binder" shows no warning.
**Dependencies:** Task 10.1.

### Task 10.5 — Add secret handling tests [MVP REQUIRED]
**Objective:** Comprehensive tests for the security boundary per design §12.2.
**Files created:** `tests/test_secret_handling.py`
**Test cases:** No secret fields in forms; keyword+value blocks; colon value blocks; equals value blocks; no false positive on benign text; no false positive on mention (password reset in binder); blocks before DB save; blocks before AI transmission; AI proposed records checked before save; no secret columns in schema.
**Acceptance:** `pytest tests/test_secret_handling.py` passes. All blocking and non-blocking cases verified.
**Dependencies:** Task 10.2, Task 10.3.

---

## Phase 11 — Final Polish

> **Goal:** Polished, demo-ready application with clear messaging, empty states, and documentation.

### Task 11.1 — Improve dashboard presentation [MVP REQUIRED]
**Objective:** Make the dashboard visually compelling for a demo.
**Files modified:** `templates/dashboard.html`, `static/css/style.css`
**Contents:** Larger risk badge, clearer stat cards, better top-risks panel with risk-level colors, prominent "Start Guided Discovery" CTA.
**Acceptance:** Dashboard looks polished and professional. Risk level is immediately visible. Top risks are color-coded.
**Dependencies:** Task 4.4, Task 3.5.

### Task 11.2 — Improve empty states [MVP REQUIRED]
**Objective:** Handle cases with no data gracefully (no org, no people, no assets, no risks).
**Files modified:** `templates/dashboard.html`, `templates/people/list.html`, `templates/assets/list.html`, `templates/risk/overview.html`, `templates/recommendations.html`
**Acceptance:** Each page shows a helpful empty-state message with a clear next action when there is no data. No broken layouts or confusing blanks.
**Dependencies:** Task 11.1.

### Task 11.3 — Improve forms and navigation [MVP REQUIRED]
**Objective:** Consistent form styling, clear labels, and smooth navigation.
**Files modified:** `templates/people/form.html`, `templates/assets/form.html`, `templates/interview/category.html`, `templates/interview/review.html`, `static/css/style.css`
**Acceptance:** Forms are consistent, labels are clear, required fields are marked, submit/cancel buttons are styled. Navigation between related pages (person → asset → risk) is smooth.
**Dependencies:** Task 11.2.

### Task 11.4 — Add clear security messaging [MVP REQUIRED]
**Objective:** Visible guidance that the system does not store secrets per design §9.1, requirements Epic I.
**Files modified:** `templates/base.html`, `templates/interview/intro.html`, `templates/organization_setup.html`, all free-text input templates
**Contents:** Security notice on interview intro, security badges/notes near free-text fields, general "WithinReach does not store passwords or credentials" messaging.
**Acceptance:** A new user immediately understands the security boundary without reading documentation. Free-text fields have visible "do not enter secrets" guidance.
**Dependencies:** Task 10.4.

### Task 11.5 — Add demo-reset endpoint [MVP REQUIRED]
**Objective:** Easy reset/reseed for demo purposes per Task 2.3.
**Files created:** `app/routes/pages.py` (add `POST /demo/reset` route)
**Logic:** Calls `reset_demo_data(db)`, redirects to dashboard with flash message "Demo data reset."
**Acceptance:** Clicking "Reset Demo Data" on the dashboard wipes and reseeds the DB. Dashboard shows fresh Grace Community Church data after reset.
**Dependencies:** Task 2.3, Task 11.1.

### Task 11.6 — Create README with setup instructions [MVP REQUIRED]
**Objective:** README with install, run, and demo instructions.
**Files created:** `README.md`
**Contents:** Project overview, install steps (`pip install -r requirements.txt`), run steps (`uvicorn app.main:app --reload`), environment variables (copy `.env.example` to `.env`), demo data instructions, hackathon demo script (walkthrough: dashboard → guided discovery → risk view → dependency map → what if → recommendations).
**Acceptance:** A new developer can clone, install, and run the app by following the README. Demo script guides a presenter through the key features.
**Dependencies:** Task 11.5.

### Task 11.7 — Create .env.example [MVP REQUIRED]
**Objective:** Template environment file with documented variables.
**Files created:** `.env.example`
**Contents:** All variables from Appendix A with comments explaining each. `BEDROCK_MODEL_ID` noted as an example default, configurable.
**Acceptance:** Copying `.env.example` to `.env` and running the app works with defaults. Each variable has a clear comment.
**Dependencies:** Task 1.3.

### Task 11.8 — Final end-to-end verification [MVP REQUIRED]
**Objective:** Verify the complete app works for a demo.
**Action:** Run through the full demo script: setup → dashboard → people → assets → risk view → dependency map → what if (Dami) → recommendations → guided discovery (structured mode) → save records → verify they appear. Reset demo data. Verify all pages render and all interactions work.
**Acceptance:** Full walkthrough completes without errors. All features work. Demo data resets cleanly. App is ready to present.
**Dependencies:** All MVP REQUIRED tasks.

---

## Phase 12 — Stretch (if time permits)

> **Goal:** Tier 2 features from requirements §3.5. Only attempt after all MVP REQUIRED tasks are complete.

### Task 12.1 — Multi-person What If simulation [STRETCH]
**Objective:** Allow selecting 2+ people and computing combined impact per requirements US-G2 (Tier 2).
**Files modified:** `app/services/simulator.py`, `templates/simulator.html`, `app/routes/simulation.py`
**Acceptance:** Can select Dami + James → shows combined blast radius. Assets orphaned by combined loss are identified.
**Dependencies:** Task 6.4.

### Task 12.2 — S3 report export [STRETCH]
**Objective:** Export risk summary or continuity report to S3 per requirements §3.5 (Tier 2).
**Files created:** `app/services/export_service.py`
**Acceptance:** Can generate a report and store it in S3. Download link available on dashboard.
**Dependencies:** Task 11.8.

### Task 12.3 — Advanced editing workflows [STRETCH]
**Objective:** Bulk edit responsibilities, drag-and-drop reassignment per requirements §3.5 (Tier 2).
**Acceptance:** Can reassign multiple responsibilities in one action.
**Dependencies:** Task 5.4.

### Task 12.4 — Extensive reporting [STRETCH]
**Objective:** Trend tracking, exportable summaries per requirements §3.5 (Tier 2).
**Acceptance:** Can export a summary of risks and recommendations as a downloadable file.
**Dependencies:** Task 11.8.

---

## Task Summary

| Phase | MVP REQUIRED Tasks | STRETCH Tasks |
|---|---|---|
| 1 — Foundation | 8 | 0 |
| 2 — Demo Data | 3 | 0 |
| 3 — Core Dashboard | 6 | 0 |
| 4 — Risk Engine | 5 | 0 |
| 5 — People, Assets, Responsibilities | 7 | 0 |
| 6 — What If Simulator | 5 | 0 |
| 7 — Dependency Map | 5 | 0 |
| 8 — Guided Dependency Discovery | 6 | 0 |
| 9 — Amazon Bedrock | 6 | 0 |
| 10 — Security Controls | 5 | 0 |
| 11 — Final Polish | 8 | 0 |
| 12 — Stretch | 0 | 4 |
| **Total** | **64** | **4** |

### Critical Path (shortest path to demoable app)
1. Phase 1 (Foundation) → Phase 2 (Demo Data) → Phase 3 (Core Dashboard)
2. At this point the app runs in the browser with seeded data (Task 3.6).
3. Phase 4 (Risk Engine) adds scoring → dashboard shows risk.
4. Phase 5 (People/Assets/Responsibilities) adds full CRUD.
5. Phase 6 (What If) adds the simulator.
6. Phase 7 (Dependency Map) adds the visual.
7. Phase 8 (Guided Discovery) adds the differentiating interview (structured mode).
8. Phase 9 (Bedrock) adds AI on top of the working structured fallback.
9. Phase 10 (Security) hardens the secret checking.
10. Phase 11 (Polish) makes it demo-ready.

### Key Design Constraints Enforced Throughout
- No secrets stored or transmitted (Tasks 8.5, 9.5, 10.1–10.5)
- Risk scoring is deterministic, no AI (Task 4.1)
- Bedrock is an enhancement with fallback (Tasks 9.1, 9.4, 9.6)
- Structured interview works without AI (Task 8.2)
- Bedrock model ID is configurable, not hard-coded (Task 1.3, 9.1)
