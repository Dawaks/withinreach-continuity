# WithinReach Continuity — Requirements Specification

## Hackathon Context

**Theme:** Within Reach — Solve what is close to you.

**Project:** WithinReach Continuity — an AI-powered technology dependency and continuity mapper for small community organizations (churches, nonprofits, student organizations, family businesses).

**One-liner:** Help small organizations find the hidden technology dependencies held by one or two people before those dependencies become emergencies.

---

## 1. Problem Statement

Small community organizations rely on technology — livestreaming, websites, social media, Wi-Fi, shared documents, payment systems — but the knowledge of how to operate, administer, and recover that technology is usually held by one or two people. When that person becomes unavailable (illness, moving away, stepping down, conflict), the organization discovers too late that:

- Nobody else knows how to run the livestream.
- The website domain is registered under a personal account nobody else can access.
- The only person with social media admin rights has left.
- Critical files live on a single laptop with no backup.
- The Wi-Fi password and router config exist only in someone's head.

The result is operational disruption, loss of services, and in some cases permanent loss of digital assets (domains, social media accounts, donor data).

Existing enterprise IT tools (CMDBs, continuity planners, dependency mappers) are too complex, too expensive, and too generic for a small organization whose "IT department" is a volunteer who set up the projector two years ago. Small organizations need a lightweight, guided tool that surfaces these risks in plain language and tells them what to do next.

A further challenge is that most coordinators do not even know which dependencies to enter. They are not IT professionals and would not spontaneously think to create an "asset record" for the livestream laptop or categorize the domain registrar. The tool must guide discovery — asking plain-language questions and converting the answers into structured records — rather than presenting a blank form and expecting the user to know what to fill in.

---

## 2. Target Users

| Primary users | Description |
|---|---|
| **Organization coordinator** | The person who cares about continuity — a pastor, office administrator, student leader, or family business owner. Likely non-technical. Will input people, assets, and relationships, ideally through a guided interview rather than a blank form. |
| **Knowledge holders** | Volunteers or staff who manage specific technologies. May provide information about their own responsibilities and backup coverage. |
| **Reviewers / leadership** | Board members, deacons, or family stakeholders who need to understand risk without deep technical context. They benefit from a visual map that makes concentrations of knowledge obvious at a glance. |

---

## 3. Goals & Non-Goals

### Goals
1. Let a non-technical user map their organization's technology dependencies through a guided interview rather than requiring prior knowledge of what to enter.
2. Surface single-points-of-failure automatically and explain them in plain language.
3. Produce an explainable continuity risk score with clear contributing factors.
4. Make concentrations of knowledge and single points of failure visually obvious through a simple dependency map.
5. Provide a "What If?" simulator so leadership can see the blast radius of a person becoming unavailable.
6. Generate practical, prioritized recommendations to reduce each identified risk.
7. Be architected cleanly enough to extend after the hackathon.

### Non-Goals (out of scope for MVP)
- Storing or managing actual credentials, passwords, tokens, or secrets.
- Automated discovery or scanning of the organization's network, accounts, or devices.
- Real-time monitoring or alerting.
- User authentication and multi-tenant access control (single shared organization access is acceptable for the MVP).
- Mobile-native applications.
- Integration with external IT management platforms.
- Full enterprise-grade RBAC and audit logging.
- Offline-first or multi-organization dashboards.

---

## 3.5 MVP Scope & Priorities

The hackathon has a fixed timebox. To ensure a shippable demo, features are prioritized into two tiers. Tier 1 features must be complete for the MVP. Tier 2 features are stretch goals — valuable but not blocking.

### Tier 1 — Must-have for MVP
1. Organization setup (profile creation and dashboard)
2. Guided dependency discovery interview
3. People, assets, and responsibility mapping (including backup-person modeling)
4. Explainable risk scoring with risk display by level
5. Dependency visualization (simple visual map)
6. Single-person "What If?" simulation
7. AI-assisted recommendations

### Tier 2 — Stretch goals (implement if time permits)
- Multi-person "What If?" simulation
- S3 report export
- Advanced editing workflows (bulk edit, drag-and-drop reassignment)
- Extensive reporting (trend tracking, exportable summaries)
- Post-hackathon integrations (CSV/JSON import, third-party tool sync)

### Rationale
The guided discovery interview and the visual dependency map are the two features that differentiate WithinReach Continuity from a generic form-and-dashboard tool. They must be in the MVP. Multi-person simulation and S3 export are powerful but not essential to demonstrate the core value proposition.

---

## 4. Functional Requirements

### FR-1 — Organization Profile
The system must allow a user to create and edit a single organization profile capturing name, type (church, nonprofit, student organization, family business, other), size, and a short description.

### FR-2 — People & Roles
The system must allow a user to add people to the organization. Each person has a display name, role/title (e.g., "Livestream Volunteer", "Office Administrator"), and an optional contact email. A person is a lightweight record — not a login account.

### FR-3 — Technology Assets & Services
The system must allow a user to add technology assets and services. Each asset has a name, category (e.g., livestream, website, social media, network/Wi-Fi, data storage, communication, payment), a description, and an assigned criticality level.

### FR-4 — Responsibility Mapping (Revised)
The system must allow the user to record, for each asset, which people are responsible and in what capacity. Each responsibility records:
- **Primary person** — the person primarily responsible.
- **Responsibility type** — one of: Manages, Understands, Administers.
- **Backup status** — one of: `has_backup`, `no_backup`, `backup_unknown`.
- **Backup people** — when backup status is `has_backup`, one or more named people who can perform this responsibility if the primary person is unavailable. When backup status is `no_backup` or `backup_unknown`, no backup people are recorded.

This replaces the previous simple yes/no/unknown flag. The system must track the actual backup person or people so that the "What If?" simulator can determine whether an asset becomes unaffected, partially affected, or orphaned when the primary person is removed.

The data model must remain simple: a responsibility links a primary person to an asset with a type and a backup status. Backup people are a lightweight association (person references) on that responsibility. A single person may appear as primary on one responsibility and as a backup on another.

### FR-5 — Documentation Tracking
The system must allow the user to record, per asset, whether documentation exists and optionally where it is located (e.g., "Google Drive > IT folder", "binder in office"). The system must never store the documentation content itself or any secrets.

### FR-6 — Personal Account / Single Device Dependency
The system must allow the user to flag, per asset, whether it depends on a personal account (e.g., someone's personal email registered as the domain owner) or a single device (e.g., a specific laptop). This is a yes/no flag with an optional note.

### FR-7 — Service Criticality
The system must allow the user to assign a criticality level to each asset: Critical, High, Medium, or Low. Criticality is user-defined and factors into the risk score.

### FR-8 — Continuity Risk Score
The system must calculate an explainable continuity risk score for the organization. The score must be:
- **Explainable** — each contributing factor is visible and understandable, not a black box.
- **Derived** from asset criticality, backup coverage (including whether backup people are named), documentation status, and personal-account/single-device dependencies.
- **Categorized** into Critical, High, Medium, or Low overall organization risk.

### FR-9 — Risk Display
The system must display risks organized by level (Critical, High, Medium, Low). Each risk item must show the affected asset, the specific issue (e.g., "No backup for livestream — only Dami knows how to operate it"), and the contributing factors.

### FR-10 — "What If?" Simulator
The system must provide a "What If?" simulator. The user selects one person (MVP) or more (stretch) and the system shows:
- Which assets would be affected.
- For each affected asset, whether a named backup person exists and whether that backup person is also unavailable in the simulation.
- Which assets become unaffected (a surviving backup person can cover), partially affected, or orphaned (no backup or backup also unavailable).
- The resulting change in the continuity risk score.

The simulator must use actual backup-person relationships (FR-4), not just a yes/no flag, to determine impact levels.

### FR-11 — Recommendations
The system must generate practical, prioritized recommendations to reduce each continuity risk. Recommendations must be specific to the identified risk (e.g., "Identify and train a second person who can run the livestream") and prioritized by impact. The system should use AI to interpret the organization's specific context and produce human-readable, actionable advice rather than generic boilerplate.

### FR-12 — Security Boundary (Critical)
The system must NEVER ask for, accept, store, or transmit passwords, API keys, access tokens, Wi-Fi passwords, recovery codes, or any other secret. Input fields must be designed to prevent secret entry (e.g., no generic "password" or "key" fields). This requirement overrides any convenience tradeoff. This applies to all input paths including the guided discovery interview (FR-13).

### FR-13 — Guided Dependency Discovery Interview
The system must provide a guided interview that helps a non-technical coordinator discover and record their organization's technology dependencies without needing to know in advance what to enter.

The interview must:
- Walk the user through plain-language questions covering common dependency areas (livestream, website, social media, Wi-Fi/network, shared files/cloud storage, payment/donation systems).
- Ask, for each area, who handles it, whether someone else could perform the task, whether the process is documented, whether it relies on a single device, and whether it uses an organization-owned or personal account.
- Convert the user's plain-language answers into proposed People, Assets, Responsibilities (with backup status and backup people), documentation status, and dependency flags.
- Allow AI to assist in interpreting natural-language responses and proposing structured records, but the user must review and confirm every proposed record before it is saved.
- Never ask for or accept passwords, keys, tokens, recovery codes, Wi-Fi passwords, or any secret.
- Allow the user to skip any question and return to it later.
- Allow the user to run the interview multiple times or partially, adding to existing records rather than overwriting them.

This is a differentiating feature. The interview is the primary onboarding path; manual entry (Epics B–E) remains available for users who prefer to add records directly.

### FR-14 — Visual Dependency Map
The system must display a simple visual dependency map showing relationships between:
- **People** → **Technology Assets/Services** → **Organizational Functions** (derived from asset categories or user-defined labels).

The map must:
- Show which people are connected to which assets and in what capacity (Manages, Understands, Administers).
- Visually distinguish critical/high-risk dependencies (e.g., no backup, undocumented, personal-account dependency) from healthy dependencies (backup exists, documented, organization-owned).
- Make single points of failure visually obvious — a person connected to multiple critical assets with no backup should be immediately apparent.
- Be interactive or clearly structured enough that a non-technical user can understand it at a glance.
- Not require enterprise-grade graph visualization for the MVP. A simple node-and-edge layout, structured tree, or clearly organized card-based view is sufficient.

This is a differentiating feature alongside the guided discovery interview.

---

## 5. Non-Functional Requirements

### NFR-1 — Simplicity
The MVP must be usable by a non-technical coordinator within a single guided session. The data model and UI should avoid unnecessary abstraction. The guided discovery interview is the primary path; manual forms are the secondary path.

### NFR-2 — Extensibility
The backend must be cleanly layered (routes → service → data) so that new risk factors, scoring rules, asset categories, AI integrations, and discovery question sets can be added without rewriting core logic. The database schema should be versioned/migratable.

### NFR-3 — Performance
The application must remain responsive for an organization with up to ~100 people and ~100 assets. Risk score calculation, "What If?" simulation, and dependency map rendering must return within 2 seconds for typical inputs.

### NFR-4 — Security
No secrets are stored (FR-12). The application must not log sensitive input. For the MVP, single-organization access without authentication is acceptable, but the design must not preclude adding auth later.

### NFR-5 — AI Cost Control
AI features (recommendation generation and discovery interview interpretation) must be invoked explicitly or on-demand, not on every page load, to control cost and latency. The discovery interview may call AI per question batch, not per keystroke.

### NFR-6 — Portability
The system must run locally with SQLite and require no external infrastructure beyond optional AWS services and an AI model endpoint.

---

## 6. Technology Stack

| Layer | Choice | Rationale |
|---|---|---|
| Language | Python | Requested by user; strong AI ecosystem. |
| Backend framework | FastAPI | Async, typed, auto-generated docs, fast to build. |
| Database | SQLite | Zero-config, file-based, sufficient for MVP volume. |
| ORM | SQLAlchemy (or SQLModel) | Migratable schema, clean data access layer. |
| Migrations | Alembic | Versioned schema for extensibility. |
| Frontend | Server-rendered Jinja2 templates + lightweight CSS (e.g., Pico CSS or Tailwind via CDN) | Simple to ship for a hackathon; no build step. |
| Dependency map rendering | Lightweight client-side library (e.g., D3.js via CDN, Cytoscape.js, or a CSS-based card/tree layout) | No build step; sufficient for a simple interactive visualization. |
| AI | Amazon Bedrock (e.g., Claude) or OpenAI-compatible API | For discovery interview interpretation and recommendation generation. Chosen via configuration so it is swappable. |
| AWS integration | Amazon Bedrock for AI; optional S3 for export/report storage | Adds meaningful AI value; S3 export is a stretch goal (Tier 2). |

### AWS Integration Detail
- **Amazon Bedrock** — used for two AI features: (1) interpreting natural-language answers during the guided discovery interview and proposing structured records, and (2) generating continuity recommendations. The application sends a structured, secret-free prompt containing the organization's context (asset names, responsibility gaps, criticality, documentation status, dependency flags). No secrets or credentials from the organization are ever sent.
- **Optional: Amazon S3** — store generated continuity reports or risk summaries for sharing. This is a Tier 2 stretch goal, not a blocker for the MVP.

---

## 7. Data Model Overview (Conceptual)

This is a conceptual outline for scoping. Detailed schema is a design-phase concern.

- **Organization** — single record (name, type, size, description).
- **Person** — name, role/title, optional email.
- **Asset** — name, category, description, criticality (Critical/High/Medium/Low).
- **Responsibility** — links a primary Person to an Asset with a type (Manages/Understands/Administers) and a backup status (`has_backup` / `no_backup` / `backup_unknown`).
- **ResponsibilityBackup** — when backup status is `has_backup`, one or more records linking the Responsibility to a backup Person. This is a lightweight join; a single Person may be a backup on multiple responsibilities and a primary on others.
- **AssetDocumentation** — per asset: exists (yes/no/unknown), optional location note.
- **AssetDependency** — per asset: depends_on_personal_account (bool, optional note), depends_on_single_device (bool, optional note).
- **RiskScore** — computed, not stored as a fixed value (organization-level and per-asset). Stored snapshots optional.

### Backup-person modeling summary
The backup model is intentionally simple for the MVP:
- A Responsibility has exactly one primary person.
- A Responsibility has a backup status: `has_backup`, `no_backup`, or `backup_unknown`.
- When `has_backup`, the Responsibility has one or more linked backup people (ResponsibilityBackup records).
- When `no_backup` or `backup_unknown`, no backup people are linked.

This allows the "What If?" simulator to check whether removing a primary person leaves a surviving backup person who is not also unavailable.

---

## 8. User Stories

### Epic A — Organization Onboarding

**US-A1: Create organization profile**
> As an organization coordinator, I want to create a profile for my organization so that I can begin mapping its technology dependencies.

**US-A2: Edit organization profile**
> As a coordinator, I want to edit my organization profile so that I can keep its information current.

**US-A3: View organization dashboard**
> As a coordinator, I want to see a dashboard summarizing my organization's people, assets, and current continuity risk so that I have a quick overview.

---

### Epic B — People Management

**US-B1: Add a person**
> As a coordinator, I want to add a person to my organization with their name and role so that I can track who is involved with our technology.

**US-B2: Edit a person**
> As a coordinator, I want to edit a person's details so that I can correct mistakes or update their role.

**US-B3: Remove a person**
> As a coordinator, I want to remove a person so that I can reflect departures, and I want to be warned if removing them would leave assets with no responsible person or no backup.

---

### Epic C — Asset Management

**US-C1: Add a technology asset**
> As a coordinator, I want to add a technology asset or service with a name, category, and description so that I can track what our organization relies on.

**US-C2: Assign criticality to an asset**
> As a coordinator, I want to assign a criticality level (Critical/High/Medium/Low) to each asset so that the system can weigh its importance in the risk score.

**US-C3: Edit an asset**
> As a coordinator, I want to edit an asset's details so that I can keep its information current.

**US-C4: Remove an asset**
> As a coordinator, I want to remove an asset so that I can reflect decommissioned technology.

---

### Epic D — Responsibility Mapping (Revised)

**US-D1: Assign a responsibility to a person for an asset**
> As a coordinator, I want to record that a specific person Manages, Understands, or Administers a specific asset so that I can map who knows what.

**US-D2: Record backup status and backup people**
> As a coordinator, I want to record whether a responsibility has a backup, who the backup person or people are, or that the backup is unknown, so that the system can identify single points of failure and the simulator can determine real impact.

**US-D3: View all responsibilities for a person**
> As a coordinator, I want to see everything a given person is responsible for (as primary or as backup) so that I can understand their load and exposure.

**US-D4: View all responsibilities for an asset**
> As a coordinator, I want to see everyone involved with a given asset (primary and backup people) so that I can understand its coverage.

---

### Epic E — Documentation & Dependency Tracking

**US-E1: Record documentation status for an asset**
> As a coordinator, I want to record whether documentation exists for an asset and optionally where it is located so that the system can factor documentation gaps into the risk score.

**US-E2: Flag personal account dependency**
> As a coordinator, I want to flag that an asset depends on a personal account (e.g., someone's personal email is the domain registrant) so that the system can surface account-transfer risks.

**US-E3: Flag single device dependency**
> As a coordinator, I want to flag that an asset depends on a single device so that the system can surface device-loss risks.

---

### Epic F — Risk Scoring & Display

**US-F1: View overall continuity risk score**
> As a coordinator or reviewer, I want to see an overall continuity risk score for my organization so that I understand the big picture at a glance.

**US-F2: View risk breakdown by level**
> As a coordinator, I want to see risks grouped by Critical, High, Medium, and Low so that I can prioritize what to address first.

**US-F3: Understand why a risk exists**
> As a coordinator, I want to see the contributing factors behind each risk so that I understand the score instead of trusting a black box.

**US-F4: View per-asset risk**
> As a coordinator, I want to see a risk assessment for each individual asset so that I can focus on specific technologies.

---

### Epic G — "What If?" Simulator

**US-G1: Simulate a person becoming unavailable** (Tier 1 — MVP)
> As a coordinator or reviewer, I want to select a person and see what would happen if they became unavailable so that I can understand their blast radius.

**US-G2: Simulate multiple people becoming unavailable** (Tier 2 — Stretch)
> As a coordinator, I want to select more than one person so that I can model the impact of a group departing together.

**US-G3: See affected, partially affected, and orphaned assets**
> As a coordinator, I want the simulator to list which assets would be unaffected (backup person survives), partially affected, or orphaned (no backup or backup also unavailable) so that I can plan mitigation accurately.

**US-G4: See updated risk score in simulation**
> As a coordinator, I want to see how the overall risk score would change in the simulated scenario so that I can quantify the impact.

---

### Epic H — Recommendations

**US-H1: Generate continuity recommendations**
> As a coordinator, I want the system to generate practical recommendations to reduce each continuity risk so that I know what actions to take.

**US-H2: See prioritized recommendations**
> As a coordinator, I want recommendations prioritized by impact so that I can focus on the most important mitigations first.

**US-H3: Understand the reasoning behind a recommendation**
> As a coordinator, I want each recommendation to reference the specific risk it addresses so that I can trust and act on it.

---

### Epic I — Security Boundary

**US-I1: Protection against secret entry**
> As an organization coordinator, I want the application to never ask me for passwords or secrets so that I am not tempted to enter sensitive information into the system.

**US-I2: Clear security messaging**
> As a coordinator, I want visible guidance that the system does not store secrets so that I understand what not to enter.

---

### Epic J — Guided Dependency Discovery Interview (New)

**US-J1: Start a guided discovery interview**
> As a non-technical coordinator, I want to start a guided interview that asks me plain-language questions about my organization's technology so that I do not need to know in advance which dependencies to enter.

**US-J2: Answer plain-language questions about each dependency area**
> As a coordinator, I want to answer simple questions such as "Who normally handles your livestream?" and "If that person were unavailable, could someone else perform the task?" so that I can describe my organization in everyday language.

**US-J3: Review and confirm proposed records**
> As a coordinator, I want to review the proposed people, assets, responsibilities, and dependency flags that the system derives from my answers, and confirm or edit them before they are saved, so that I stay in control of what is recorded.

**US-J4: Skip and return to questions**
> As a coordinator, I want to skip a question I cannot answer yet and return to it later so that I am not blocked by uncertainty.

**US-J5: Add to existing records through a partial interview**
> As a coordinator, I want to run the interview again or partially and have it add to my existing records rather than overwriting them, so that I can build up my dependency map over time.

**US-J6: No secrets asked during the interview**
> As a coordinator, I want the interview to never ask me for passwords, keys, or tokens, and to clearly tell me not to enter them, so that I am never tempted to expose sensitive information.

---

### Epic K — Visual Dependency Map (New)

**US-K1: View the dependency map**
> As a coordinator or reviewer, I want to see a visual map showing how people, assets, and functions connect so that I can understand my organization's dependency structure at a glance.

**US-K2: Identify single points of failure visually**
> As a reviewer, I want the map to visually highlight dependencies that have no backup or are high-risk so that concentrations of knowledge are immediately obvious without reading a table.

**US-K3: Distinguish healthy from risky dependencies**
> As a coordinator, I want the map to visually distinguish healthy dependencies (backup exists, documented, organization-owned) from risky ones (no backup, undocumented, personal account) so that I can see where to focus.

**US-K4: Navigate from the map to details**
> As a coordinator, I want to click or select a person or asset on the map and see its detail view so that I can drill into specifics from the visualization.

---

## 9. Acceptance Criteria

### Epic A — Organization Onboarding

**AC-A1: Create organization profile**
- **Given** no organization profile exists
- **When** the user submits an organization name, type, size, and description
- **Then** the organization profile is created and persisted
- **And** the user is redirected to the organization dashboard or guided discovery interview

**AC-A2: Edit organization profile**
- **Given** an organization profile exists
- **When** the user edits the profile fields and saves
- **Then** the changes are persisted
- **And** the updated values are displayed on the dashboard

**AC-A3: View organization dashboard**
- **Given** an organization profile with people and assets exists
- **When** the user opens the dashboard
- **Then** the dashboard displays counts of people and assets
- **And** the current overall continuity risk level is shown
- **And** the user can navigate to the guided discovery interview, people, assets, risks, dependency map, simulator, and recommendations from the dashboard

---

### Epic B — People Management

**AC-B1: Add a person**
- **Given** an organization profile exists
- **When** the user submits a person's name and role (email optional)
- **Then** the person is created and linked to the organization
- **And** the person appears in the people list

**AC-B2: Edit a person**
- **Given** a person exists
- **When** the user edits the person's name, role, or email and saves
- **Then** the changes are persisted
- **And** the updated values are displayed

**AC-B3: Remove a person with dependencies**
- **Given** a person who is a primary or backup on one or more responsibilities exists
- **When** the user attempts to remove that person
- **Then** the system displays a warning listing the assets and responsibilities (primary and backup) that would be affected
- **And** the user can confirm or cancel the removal
- **And** if confirmed, the responsibilities or backup associations involving that person are removed and the affected assets are reflected in the next risk score

---

### Epic C — Asset Management

**AC-C1: Add a technology asset**
- **Given** an organization profile exists
- **When** the user submits an asset name, category, description, and criticality
- **Then** the asset is created and linked to the organization
- **And** the asset appears in the asset list

**AC-C2: Assign criticality**
- **Given** an asset exists
- **When** the user sets its criticality to one of Critical, High, Medium, or Low
- **Then** the criticality is persisted
- **And** the asset's risk contribution is recalculated

**AC-C3: Edit an asset**
- **Given** an asset exists
- **When** the user edits the asset fields and saves
- **Then** the changes are persisted and displayed

**AC-C4: Remove an asset**
- **Given** an asset exists
- **When** the user removes the asset
- **Then** the asset and its associated responsibilities, backup associations, documentation, and dependency records are removed
- **And** the risk score is recalculated

---

### Epic D — Responsibility Mapping (Revised)

**AC-D1: Assign a responsibility**
- **Given** at least one person and one asset exist
- **When** the user assigns a responsibility linking a primary person to the asset with a type (Manages, Understands, or Administers) and a backup status
- **Then** the responsibility is created and visible on both the person and asset views
- **And** the backup status is displayed (has backup, no backup, or backup unknown)

**AC-D2: Record backup people**
- **Given** a responsibility exists with backup status set to `has_backup`
- **When** the user selects one or more people as backup for that responsibility
- **Then** the backup people are linked to the responsibility
- **And** they are displayed on both the person and asset views
- **And** the asset's risk is recalculated (a named backup reduces risk compared to no_backup or backup_unknown)

**AC-D2b: Set backup to unknown or none**
- **Given** a responsibility exists
- **When** the user sets the backup status to `no_backup` or `backup_unknown`
- **Then** no backup people are linked
- **And** the asset's risk is recalculated (no_backup and backup_unknown both increase risk, with no_backup contributing the most)

**AC-D3: View responsibilities for a person**
- **Given** a person with one or more responsibilities exists
- **When** the user opens the person's detail view
- **Then** all assets the person is primarily responsible for are listed with the responsibility type and backup status (and backup people if any)
- **And** all assets the person is a backup for are listed separately

**AC-D4: View responsibilities for an asset**
- **Given** an asset with one or more responsibilities exists
- **When** the user opens the asset's detail view
- **Then** all primary people are listed with the responsibility type and backup status
- **And** for each responsibility with `has_backup`, the named backup people are listed

---

### Epic E — Documentation & Dependency Tracking

**AC-E1: Record documentation status**
- **Given** an asset exists
- **When** the user sets documentation status to yes, no, or unknown and optionally enters a location note
- **Then** the documentation status and note are persisted
- **And** the asset's risk is recalculated (undocumented assets contribute higher risk)

**AC-E2: Flag personal account dependency**
- **Given** an asset exists
- **When** the user enables the "depends on personal account" flag and optionally adds a note
- **Then** the flag and note are persisted
- **And** the asset's risk is recalculated (personal account dependency increases risk)

**AC-E3: Flag single device dependency**
- **Given** an asset exists
- **When** the user enables the "depends on single device" flag and optionally adds a note
- **Then** the flag and note are persisted
- **And** the asset's risk is recalculated (single device dependency increases risk)

---

### Epic F — Risk Scoring & Display

**AC-F1: View overall continuity risk score**
- **Given** an organization with assets, responsibilities, documentation, and dependency flags exists
- **When** the user opens the dashboard or risk view
- **Then** an overall continuity risk score is displayed
- **And** the score is categorized as Critical, High, Medium, or Low
- **And** the score is computed from asset criticality, backup coverage (including whether backup people are named), documentation status, and dependency flags

**AC-F2: View risk breakdown by level**
- **Given** one or more risks exist
- **When** the user opens the risk view
- **Then** risks are grouped and displayed under Critical, High, Medium, and Low headings
- **And** each risk item shows the affected asset and a plain-language description of the issue

**AC-F3: View risk contributing factors**
- **Given** a risk item exists
- **When** the user expands or opens the risk item
- **Then** the contributing factors are listed (e.g., "Critical asset", "No backup person", "Backup unknown", "No documentation", "Depends on personal account")
- **And** the user can understand why this risk was scored the way it was

**AC-F4: View per-asset risk**
- **Given** an asset with risk factors exists
- **When** the user opens the asset detail view
- **Then** a per-asset risk level is displayed along with its contributing factors

---

### Epic G — "What If?" Simulator

**AC-G1: Simulate single person unavailable** (Tier 1 — MVP)
- **Given** an organization with people and assets exists
- **When** the user selects one person in the simulator and runs the simulation
- **Then** the system displays which assets would be affected
- **And** for each affected asset, classifies it as:
  - **Unaffected** — a named backup person exists who is not the selected person, so the asset can continue operating.
  - **Partially affected** — backup status is `backup_unknown` (may or may not have coverage) or the backup person is the same as the selected person but other primary responsibilities on the asset remain covered.
  - **Orphaned** — backup status is `no_backup`, or the only backup person is also the selected person (i.e., no surviving backup).
- **And** lists the specific responsibilities lost

**AC-G2: Simulate multiple people unavailable** (Tier 2 — Stretch)
- **Given** an organization with people and assets exists
- **When** the user selects two or more people and runs the simulation
- **Then** the combined impact is displayed, classifying each affected asset as unaffected, partially affected, or orphaned based on whether any named backup person survives (i.e., is not among the selected unavailable people)

**AC-G3: Affected assets detail**
- **Given** a simulation has been run
- **When** the user views the simulation results
- **Then** each affected asset is listed with the specific responsibilities lost, the backup status, and the named backup people (if any)
- **And** orphaned assets are clearly distinguished from partially-affected and unaffected assets
- **And** for orphaned assets, the reason is shown (e.g., "No backup person recorded" or "Backup person (Sarah) is also unavailable")

**AC-G4: Updated risk score in simulation**
- **Given** a simulation has been run
- **When** the simulation results are displayed
- **Then** the recalculated overall risk level for the simulated scenario is shown alongside the current risk level for comparison

---

### Epic H — Recommendations

**AC-H1: Generate recommendations**
- **Given** one or more risks exist
- **When** the user requests recommendations
- **Then** the system generates a list of practical recommendations, each referencing a specific identified risk
- **And** recommendations use AI to incorporate the organization's specific context (asset names, people, categories) rather than generic text
- **And** no organization secrets or credentials are included in the AI prompt

**AC-H2: Prioritized recommendations**
- **Given** recommendations have been generated
- **When** they are displayed
- **Then** they are ordered by impact (highest risk reduction first)
- **And** each recommendation indicates the risk level it addresses

**AC-H3: Recommendation reasoning**
- **Given** a recommendation is displayed
- **When** the user reads it
- **Then** the recommendation references the specific asset, person, or gap it addresses
- **And** the user can navigate to or see the related risk item

---

### Epic I — Security Boundary

**AC-I1: No secret input fields**
- **Given** any form or interview question in the application (person, asset, responsibility, documentation, dependency, guided discovery interview)
- **When** the user views the form or question
- **Then** no field requests or accepts passwords, API keys, access tokens, Wi-Fi passwords, or recovery codes
- **And** free-text fields (e.g., documentation location, dependency notes, interview answers) are labeled with guidance to not enter secrets

**AC-I2: Security guidance displayed**
- **Given** the user is using the application
- **When** the user views onboarding, the guided discovery interview, or any documentation-location / dependency-note input
- **Then** visible guidance states that the system does not store secrets and the user should not enter them

---

### Epic J — Guided Dependency Discovery Interview

**AC-J1: Start a guided discovery interview**
- **Given** an organization profile exists
- **When** the user selects "Start Guided Discovery" from the dashboard
- **Then** the interview begins with an introductory screen explaining what it will ask and that no secrets are needed
- **And** the user is presented with the first question or question area

**AC-J2: Answer plain-language questions**
- **Given** the interview is in progress
- **When** the user is presented with questions such as "Who normally handles your livestream?", "If that person were unavailable tomorrow, could someone else perform the task?", "Is the process documented?", "Does the service rely on one particular device?", and "Is an organization-owned account used, or does it depend on someone's personal account?"
- **Then** the user can respond in plain language
- **And** the user is never asked for passwords, keys, tokens, or any secret

**AC-J3: Review and confirm proposed records**
- **Given** the user has answered one or more interview questions
- **When** the system derives proposed People, Assets, Responsibilities (with backup status and backup people), documentation status, and dependency flags from the answers
- **Then** the proposed records are presented to the user for review
- **And** the user can edit any proposed field (name, category, criticality, responsibility type, backup status, backup people, documentation status, dependency flags) before confirming
- **And** the user can reject any proposed record so it is not saved
- **And** no record is persisted until the user explicitly confirms it
- **And** AI may assist in interpreting the answers but the user has final say on every record

**AC-J4: Skip and return to questions**
- **Given** the interview is in progress
- **When** the user selects "Skip" on a question they cannot answer
- **Then** the question is marked as skipped and the interview continues to the next question
- **And** the user can return to skipped questions later and the dashboard shows how many questions remain unanswered

**AC-J5: Partial interview adds to existing records**
- **Given** the organization already has people, assets, or responsibilities recorded (from a previous interview or manual entry)
- **When** the user starts a new interview or resumes a partial one
- **Then** the interview adds to existing records rather than overwriting them
- **And** if the interview proposes a person or asset that already exists (matched by name), the user is offered the option to use the existing record or create a new one

**AC-J6: No secrets during interview**
- **Given** the user is answering interview questions
- **When** the user reaches any question about accounts, access, or credentials
- **Then** the question and any guidance explicitly instruct the user not to enter passwords, keys, tokens, or recovery codes
- **And** no free-text answer field is designed to accept or prompt for secrets

---

### Epic K — Visual Dependency Map

**AC-K1: View the dependency map**
- **Given** an organization with people and assets exists
- **When** the user opens the dependency map view
- **Then** a visual representation is displayed showing people connected to assets with their responsibility types (Manages, Understands, Administers)
- **And** assets are connected to organizational functions (derived from asset categories or user-defined labels)

**AC-K2: Identify single points of failure visually**
- **Given** one or more dependencies have no backup or are high-risk
- **When** the user views the dependency map
- **Then** high-risk dependencies (no backup, backup unknown, undocumented, personal-account dependency, single-device dependency) are visually distinguished from healthy dependencies
- **And** a person connected to multiple critical assets with no backup is visually prominent (e.g., color, size, or badge)

**AC-K3: Distinguish healthy from risky dependencies**
- **Given** the dependency map is displayed
- **When** the user views the connections
- **Then** healthy dependencies (backup exists, documented, organization-owned) are visually distinct from risky ones (e.g., green vs. red edges, or distinct styling)
- **And** a legend explains the visual distinction

**AC-K4: Navigate from map to details**
- **Given** the dependency map is displayed
- **When** the user clicks or selects a person or asset node
- **Then** the user is taken to (or shown) the detail view for that person or asset
- **And** the user can return to the map view

---

## 10. Risk Scoring Algorithm (Conceptual)

The risk score must be explainable. The following conceptual approach defines how factors combine. Exact weights are a design-phase decision but the structure is fixed for the MVP.

### Per-asset risk
Each asset accumulates risk points based on:

| Factor | Risk contribution |
|---|---|
| Criticality | Critical = highest weight; Low = lowest weight |
| Backup coverage | Each responsibility with backup status `no_backup` adds the most risk; `backup_unknown` adds moderate risk; `has_backup` with named backup people adds the least risk (or none). Risk is proportional to criticality. |
| Documentation | No documentation or unknown adds risk proportional to criticality |
| Personal account dependency | Adds risk if flagged |
| Single device dependency | Adds risk proportional to criticality if flagged |

An asset with Critical criticality, `no_backup`, no documentation, and a personal account dependency should score as a Critical risk. An asset with Low criticality, `has_backup` with named people, and documentation should score as Low.

### Organization risk
The overall risk level is determined by the highest concentration of risk:
- If any Critical per-asset risks exist, the organization is at least High overall.
- If multiple High risks exist, the organization is Critical overall.
- Exact thresholds are a design decision but must be documented and visible.

### Explainability
Every risk score (per-asset and organization) must be accompanied by a human-readable breakdown of contributing factors, not just a number or label.

---

## 11. AI Integration Design (Conceptual)

### Recommendation generation
- **Trigger:** User-initiated (button or action), not automatic on every page load (NFR-5).
- **Input:** A structured, secret-free representation of the organization's risk profile (asset names, categories, criticality, responsibility gaps including backup status, documentation status, dependency flags). No credentials, passwords, or personal secrets are included.
- **Output:** Natural-language recommendations, each tied to a specific risk, prioritized by impact.
- **Provider:** Amazon Bedrock (Claude or similar). Configurable via environment variables so the provider is swappable.
- **Fallback:** If the AI service is unavailable, the system must degrade gracefully to rule-based recommendations generated from the risk data, so the application remains usable during the hackathon demo even if AI is down.

### Guided discovery interview interpretation
- **Trigger:** Invoked per question batch (not per keystroke) during the interview (NFR-5).
- **Input:** The user's plain-language answers to interview questions. No secrets are accepted or sent.
- **Output:** Proposed structured records (people, assets, responsibilities, documentation status, dependency flags) for the user to review and confirm.
- **Provider:** Same as recommendation generation (Amazon Bedrock or OpenAI-compatible, configurable).
- **Fallback:** If the AI service is unavailable, the interview must still function using structured form-based questions (dropdowns, text fields) that map directly to record fields without AI interpretation. The AI is an enhancement, not a dependency.

### Security boundary for AI
No AI prompt (for recommendations or discovery) may contain passwords, API keys, tokens, recovery codes, or any secret from the organization. Free-text inputs that might contain secrets must be sanitized or the user must be warned before submission.

---

## 12. Future Extensibility (Post-Hackathon / Stretch)

These are explicitly out of scope for the MVP but the architecture should not block them:
- Multi-organization support and user authentication.
- Multi-person "What If?" simulation (Tier 2 stretch — single-person is MVP).
- Automated reminders and check-in schedules.
- S3 report export (Tier 2 stretch).
- Advanced editing workflows (bulk edit, drag-and-drop reassignment) (Tier 2 stretch).
- Extensive reporting: trend tracking, exportable summaries (Tier 2 stretch).
- Integration with existing IT tools via import/export (CSV, JSON).
- Role-based review workflows.
- Mobile-responsive progressive web app.

---

## 13. Glossary

| Term | Definition |
|---|---|
| **Asset** | A technology or service the organization depends on (e.g., livestream system, website, Wi-Fi, payment processor). |
| **Responsibility** | A person's relationship to an asset: Manages, Understands, or Administers. |
| **Primary person** | The person primarily responsible for a responsibility on an asset. |
| **Backup person** | A named person who can perform a responsibility if the primary person is unavailable. A responsibility may have zero, one, or multiple backup people depending on its backup status. |
| **Backup status** | Whether a responsibility has a backup: `has_backup` (one or more named backup people), `no_backup` (no one can cover), or `backup_unknown` (may or may not have coverage). |
| **Single point of failure** | A responsibility with `no_backup` or `backup_unknown`, or an asset with only one primary person and no backup. |
| **Personal account dependency** | An asset that relies on a personal (not organization-owned) account. |
| **Single device dependency** | An asset that relies on one specific device. |
| **Continuity risk** | The risk that an organization cannot operate a critical technology because knowledge or access is concentrated in one person or device. |
| **Blast radius** | The set of assets and responsibilities affected if a specific person becomes unavailable. |
| **Guided discovery interview** | A plain-language question flow that helps a non-technical coordinator discover and record technology dependencies without prior knowledge of what to enter. AI may assist in interpreting answers, but the user confirms all proposed records. |
| **Dependency map** | A visual representation of people, assets, and their relationships, showing concentrations of knowledge and single points of failure. |
| **Orphaned asset** | In a "What If?" simulation, an asset whose primary person is unavailable and no surviving backup person exists. |
| **Partially affected asset** | In a "What If?" simulation, an asset whose primary person is unavailable and backup status is `backup_unknown`, or where some but not all responsibilities are lost. |
| **Unaffected asset** | In a "What If?" simulation, an asset whose primary person is unavailable but a named backup person who is not also unavailable can cover the responsibility. |
