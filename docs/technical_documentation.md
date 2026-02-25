# 🔧 Technical Documentation — CertPrep Multi-Agent System

> Comprehensive reference for developers and architects. Covers data models, every agent, orchestration patterns, guardrails, algorithms, persistence, Azure integration, and the UI architecture.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Technology Stack](#2-technology-stack)
3. [Data Models](#3-data-models)
4. [Guardrails Framework](#4-guardrails-framework)
5. [Input Processing — Intake Form](#5-input-processing--intake-form)
6. [Agent: Learner Profiler (B1)](#6-agent-learner-profiler-b1)
7. [Agent: Study Plan (B1.1)](#7-agent-study-plan-b11)
8. [Agent: Learning Path Curator (B1.1)](#8-agent-learning-path-curator-b11)
9. [Agent: Progress Tracker (B1.2)](#9-agent-progress-tracker-b12)
10. [Agent: Assessment (B2)](#10-agent-assessment-b2)
11. [Agent: Cert Recommendation (B3)](#11-agent-cert-recommendation-b3)
12. [Orchestration and Concurrency](#12-orchestration-and-concurrency)
13. [HITL Gates](#13-hitl-gates)
14. [SQLite Persistence Layer](#14-sqlite-persistence-layer)
15. [Session State Management](#15-session-state-management)
16. [Mock vs Live Mode](#16-mock-vs-live-mode)
17. [Admin Dashboard](#17-admin-dashboard)
18. [Multi-Cert Support](#18-multi-cert-support)
19. [UI Architecture](#19-ui-architecture)
20. [Security and Safety](#20-security-and-safety)
21. [Performance Characteristics](#21-performance-characteristics)
22. [Deployment](#22-deployment)

---

## 1. System Overview

The CertPrep Multi-Agent System is a Streamlit application that orchestrates seven specialised AI agents to produce a personalised Microsoft certification study plan. The system implements a **supervisor–worker** pattern where `streamlit_app.py` acts as the orchestrator, calling each agent in a strict ordered pipeline with HITL (Human-in-the-Loop) gates between phases.

### Pipeline Phases

```
Phase 0: Auth guard (login screen)
Phase 1: Intake (form capture + guardrails G-01..G-05)
Phase 2: Profiling (b1_mock_profiler or LearnerProfilingAgent via GPT-4o)
Phase 3: Parallel planning (StudyPlanAgent + LearningPathCuratorAgent)
Phase 4: HITL Gate 1 (progress check-in → ReadinessAssessment)
Phase 5: HITL Gate 2 (mock quiz → AssessmentResult)
Phase 6: Recommendation (CertRecommendationAgent)
```

Every phase boundary is protected by the guardrails framework. The pipeline is **non-speculative** — it only runs the next phase when the current phase has passed all guardrails.

---

## 2. Technology Stack

| Layer | Component | Choice | Reason |
|---|---|---|---|
| UI | Streamlit 1.35+ | Python-native web UI | Rapid iteration, Pythonic |
| LLM | Azure OpenAI (GPT-4o) | Structured JSON output | response_format=json_object |
| Data | SQLite | Embedded DB | Zero-infra for competition |
| Data | Pydantic v2 | Model validation | type-safe contracts |
| Visualisation | Plotly | Radar + Gantt charts | Interactive HTML |
| Concurrency | ThreadPoolExecutor | Parallel agents | I/O-bound calls |
| Guardrails | Custom framework | 17 rules | Safety + correctness |
| Auth | Custom (st.session_state) | Demo-grade | Login persona system |
| PDF reports | reportlab | Profile + Progress PDFs | Zero cloud dependency |
| Email | smtplib (MIMEMultipart) | SMTP with PDF attachment | Works with any SMTP relay |

---

## 3. Data Models

All models are defined in `src/cert_prep/models.py`.

### 3.1 RawStudentInput

Raw form data captured from the intake form. Immutable dataclass.

```python
@dataclass
class RawStudentInput:
    student_name:    str          # Display name
    exam_target:     str          # e.g. "AI-102"
    background_text: str          # 20-500 character free text
    existing_certs:  list[str]    # e.g. ["AZ-900", "AI-900"]
    hours_per_week:  float        # 1–80
    weeks_available: int          # 1–52
    concern_topics:  list[str]    # up to 8 user-selected topics
    preferred_style: str          # from STYLE_OPTIONS
    goal_text:       str          # free text motivation
    email:           str = ""     # optional contact email
```

### 3.2 LearnerProfile

Output of Phase 2 (profiling). Captures per-domain readiness.

```python
@dataclass
class LearnerProfile:
    student_name:      str
    exam_target:       str
    experience_level:  ExperienceLevel       # BEGINNER / INTERMEDIATE / ADVANCED
    domain_profiles:   list[DomainProfile]   # one per exam domain
    risk_domains:      list[str]             # domain IDs needing attention
    metadata:          dict                  # profiler version, strategy used
```

### 3.3 DomainProfile

Per-domain assessment within a LearnerProfile.

```python
@dataclass
class DomainProfile:
    domain_id:         str    # e.g. "D1"
    domain_name:       str    # e.g. "Plan and Manage Azure AI Solution"
    confidence_score:  float  # 0.0–1.0
    skill_gaps:        list[str]
    recommended_focus: str
```

### 3.4 StudyPlan

Output of StudyPlanAgent. Contains week-by-week schedule.

```python
@dataclass
class StudyPlan:
    student_name:   str
    exam_target:    str
    weekly_blocks:  list[WeekBlock]
    total_hours:    float
    prereq_gaps:    list[str]    # certs user should have first
    notes:          str
```

### 3.5 WeekBlock

One row of the Gantt chart.

```python
@dataclass
class WeekBlock:
    week_number:  int
    domain_id:    str
    domain_name:  str
    hours:        float
    activities:   list[str]    # specific tasks
```

### 3.6 LearningPath

Output of LearningPathCuratorAgent.

```python
@dataclass
class LearningPath:
    student_name:  str
    exam_target:   str
    modules:       list[LearningModule]
    total_modules: int
```

### 3.7 LearningModule

Individual MS Learn path within a LearningPath.

```python
@dataclass
class LearningModule:
    domain_id:    str
    domain_name:  str
    title:        str
    url:          str       # validated by G-17
    duration_hrs: float
    priority:     int       # 1 = highest
```

### 3.8 ProgressSnapshot

Gate 1 user input capture.

```python
@dataclass
class ProgressSnapshot:
    student_name:   str
    hours_spent:    float         # G-11: >= 0
    domain_ratings: dict[str,int] # G-12: all in [1,5]
    practice_score: int           # G-13: in [0,100]
    notes:          str
```

### 3.9 ReadinessAssessment

Output of ProgressAgent from Phase 4.

```python
@dataclass
class ReadinessAssessment:
    readiness_pct:  float          # 0–100
    verdict:        str            # "READY" | "NOT YET" | "BOARDING"
    weak_domains:   list[str]
    recommendation: str
```

### 3.10 AssessmentResult

Output of AssessmentAgent from Phase 5.

```python
@dataclass
class AssessmentResult:
    score_pct:      float
    domain_scores:  dict[str, float]   # domain_id → pct
    pass_fail:      str                # "PASS" | "FAIL"
    weak_domains:   list[str]
    question_count: int
```

### 3.11 CertRecommendation

Output of CertRecommendationAgent from Phase 6.

```python
@dataclass
class CertRecommendation:
    current_exam:       str
    ready_to_book:      bool
    next_cert:          str
    booking_checklist:  list[str]
    consolidation_plan: str
    remediation_steps:  list[str]    # non-empty when ready_to_book=False
```

---

## 4. Guardrails Framework

Defined in `src/cert_prep/guardrails.py`. Implements a two-level safety system.

### 4.1 Violation Levels

```python
class GuardrailLevel(Enum):
    BLOCK = "BLOCK"   # pipeline halts via st.stop()
    WARN  = "WARN"    # pipeline continues with st.warning()
    INFO  = "INFO"    # logged only, no user-visible effect
```

### 4.2 All 17 Rules

| Code | Trigger | Level | Check |
|------|---------|-------|-------|
| G-01 | Intake | BLOCK | student_name non-empty after strip |
| G-02 | Intake | BLOCK | exam_target in EXAM_DOMAIN_REGISTRY |
| G-03 | Intake | BLOCK | hours_per_week in [1, 80] |
| G-04 | Intake | BLOCK | weeks_available in [1, 52] |
| G-05 | Intake | BLOCK | len(background_text) > 10 |
| G-06 | Profile | BLOCK | len(domain_profiles) == expected_domains(exam) |
| G-07 | Profile | BLOCK | all confidence_score in [0.0, 1.0] |
| G-08 | Profile | BLOCK | all risk_domain IDs in registry |
| G-09 | Study Plan | WARN | total_hours <= budget * 1.1 (10% slack) |
| G-10 | Study Plan | WARN | all WeekBlock.domain_id in domain_profiles |
| G-11 | Progress | BLOCK | hours_spent >= 0 |
| G-12 | Progress | BLOCK | all domain_ratings in [1, 5] |
| G-13 | Progress | BLOCK | practice_score in [0, 100] |
| G-14 | Quiz | BLOCK | len(questions) >= 5 |
| G-15 | Quiz | BLOCK | no duplicate question IDs |
| G-16 | Content | BLOCK | background_text free of disallowed keywords |
| G-17 | URL | WARN | all module URLs from learn.microsoft.com or trusted origins |

### 4.3 Application Pattern

```python
result = run_guardrails_phase("intake", raw)
for v in result.violations:
    if v.level == GuardrailLevel.BLOCK:
        st.error(f"[{v.code}] {v.message}")
        st.stop()
    elif v.level == GuardrailLevel.WARN:
        st.warning(f"[{v.code}] {v.message}")
```

---

## 5. Input Processing — Intake Form

Implemented in `streamlit_app.py` at the intake form section.

### 5.1 Pre-fill System

Demo scenarios are defined as a Python dict `_PREFILL_SCENARIOS`. When the sidebar persona button is clicked, the dict is loaded into `st.session_state["sidebar_prefill"]`. On the next rerender, the form widgets receive `value=prefill.get(field, default)` arguments, causing them to appear pre-filled.

### 5.2 Returning-User Restore

When `is_returning=True` the same prefill mechanism loads values from the persisted `RawStudentInput` stored in SQLite. The intake form is read-only unless `st.session_state["editing_profile"]=True` is set.

### 5.3 Email Field

- Optional field (`str = ""` default)
- Stored in `RawStudentInput.email`
- Persisted to SQLite via `save_raw_input()`
- Visible in read-only profile card and admin dashboard
- Pre-filled by demo scenarios (e.g. `alex.chen@demo.com`)
- Saved to `st.session_state["user_email"]` for downstream use

---

## 6. Agent: Learner Profiler (B1)

### File

`src/cert_prep/b1_mock_profiler.py` (mock) / `src/cert_prep/b1_1_learning_path_curator.py` (live)

### Responsibility

Transform `RawStudentInput` → `LearnerProfile` with per-domain confidence scores.

### Mock Strategy (Rule Engine)

**Pass 1 — Experience Level:**
```python
keywords = {"beginner":0.1, "no cloud":0.1, "new to":0.1,
            "data scientist":0.55, "developer":0.55,
            "architect":0.8, "senior":0.8}
background_lower = background_text.lower()
score = max(v for k,v in keywords.items() if k in background_lower) or 0.3
```

**Pass 2 — Domain Base Confidence:**
- Iterates each domain in `EXAM_DOMAIN_REGISTRY[exam_target]`
- Checks if domain keywords appear in background_text or existing_certs
- Assigns base confidence in [0.05, 0.85]

**Pass 3 — Concern Topic Penalty:**
- Each concern_topic that maps to a domain lowers its confidence by 0.15 (floor 0.05)
- Adds domain to `risk_domains`

### Live Strategy (Azure OpenAI)

```python
response = client.chat.completions.create(
    model   = deployment,
    messages= [
        {"role": "system", "content": PROFILER_SYSTEM_PROMPT},
        {"role": "user",   "content": raw_input_json}
    ],
    response_format = {"type": "json_object"},
    temperature     = 0.2
)
profile = LearnerProfile(**json.loads(response.choices[0].message.content))
```

The system prompt instructs GPT-4o to produce a JSON object conforming to the LearnerProfile schema, with domain IDs matching the exam registry.

---

## 7. Agent: Study Plan (B1.1)

### File

`src/cert_prep/b1_1_study_plan_agent.py`

### Responsibility

Allocate `hours_per_week × weeks_available` study hours across domains using **Largest Remainder** allocation.

### Algorithm

```python
# Step 1: weight each domain by inverse confidence
weights = {d.domain_id: (1 - d.confidence_score) for d in domain_profiles}
total_weight = sum(weights.values())
domain_weights_normalised = {k: v/total_weight for k,v in weights.items()}

# Step 2: Largest Remainder allocation of total_hours across domains
total_hours = hours_per_week * weeks_available
raw_alloc   = {d: w * total_hours for d,w in domain_weights_normalised.items()}
floored     = {d: int(v) for d,v in raw_alloc.items()}
remainders  = sorted(raw_alloc.items(), key=lambda x: x[1]-int(x[1]), reverse=True)
deficit     = total_hours - sum(floored.values())
for i in range(int(deficit)):
    floored[remainders[i][0]] += 1
```

**Why Largest Remainder?** Ensures every hour is assigned to exactly one domain. No hours are lost to rounding. The domain with the highest fractional excess gets the next whole hour — this avoids overweighting already-weak domains due to rounding.

### Prerequisite Gap Detection

```python
PREREQ_MAP = {
    "AI-102": ["AZ-900"],
    "DP-100": ["AZ-900", "DP-900"],
    "AZ-204": ["AZ-900"],
    ...
}
prereq_gaps = [p for p in PREREQ_MAP[exam] if p not in existing_certs]
```

---

## 8. Agent: Learning Path Curator (B1.1)

### File

`src/cert_prep/b1_1_learning_path_curator.py`

### Responsibility

Map each domain to 3–5 curated Microsoft Learn modules from `MODULE_CATALOGUE`.

### Module Selection Logic

```python
for domain in profile.domain_profiles:
    if domain.skip_recommended:
        continue   # user explicitly opted out
    candidates = MODULE_CATALOGUE[exam_target][domain.domain_id]
    # Sort by: preferred_style match first, then priority ASC
    selected = sorted(candidates,
                      key=lambda m: (0 if m.tag==preferred_style else 1, m.priority))[:3]
    for m in selected:
        run_guardrail_G17(m.url)  # URL safety check
```

### G-17 URL Validation

```python
TRUSTED_ORIGINS = {
    "learn.microsoft.com",
    "docs.microsoft.com",
    "azure.microsoft.com",
}
from urllib.parse import urlparse
netloc = urlparse(url).netloc.removeprefix("www.")
if netloc not in TRUSTED_ORIGINS:
    log_violation(code="G-17", level=WARN, message=f"Unverified URL: {netloc}")
    return None   # URL excluded
```

---

## 9. Agent: Progress Tracker (B1.2)

### File

`src/cert_prep/b1_2_progress_agent.py`

### Responsibility

Compute readiness percentage and verdict from HITL Gate 1 input. Generate PDF reports. Send email notifications.

### Readiness Formula

$$\text{readiness} = 0.55 \cdot \bar{c} + 0.25 \cdot h_u + 0.20 \cdot p$$

Where:
- $\bar{c}$ = mean normalised confidence = $\frac{1}{|D|} \sum_{d \in D} \frac{rating_d - 1}{4}$
- $h_u$ = hours utilisation = $\frac{hours\_spent}{hours\_per\_week}$ (capped at 1.0)
- $p$ = practice score proportion = $\frac{practice\_score}{100}$

**Verdict thresholds:**
- READY: ≥ 0.65 (65%)
- BOARDING: 0.50–0.64
- NOT YET: < 0.50

### PDF Report Generation

Three `reportlab`-based PDF generators produce downloadable / emailable reports:

| Function | Contents | Trigger |
|---|---|---|
| `generate_profile_pdf(profile, plan, lp)` | Domain confidence scores, study plan Gantt table, learning path module list | Profile tab download / auto-email on intake |
| `generate_assessment_pdf(profile, snap, asmt)` | Progress snapshot, domain readiness bars, go/no-go verdict | Progress tab download |
| `generate_intake_summary_html(profile, plan, lp)` | HTML body for the welcome email | Auto-email on intake |

All three return `bytes` — passed directly to `st.download_button` or to `attempt_send_email(pdf_bytes=...)`.

### SMTP Email

```python
def attempt_send_email(
    to: str,
    subject: str,
    html: str,
    pdf_bytes: bytes | None = None,
    pdf_filename: str = "report.pdf",
) -> bool:
```

The function constructs a `MIMEMultipart` message with an HTML body and an optional `application/pdf` attachment. Required env vars: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASS`, `SMTP_FROM`.

---

## 10. Agent: Assessment (B2)

### File

`src/cert_prep/b2_assessment_agent.py`

### Responsibility

Build a 30-question domain-weighted mock quiz. Score answers. Identify weak domains.

### Question Sampling

Uses the same **Largest Remainder** algorithm as StudyPlanAgent, but allocates 30 questions across domains weighted by `1 - domain_scores`.

Domains where `confidence_score < 0.4` receive at minimum 3 questions regardless of weight (floor guarantee).

### Scoring

```python
weighted_score = sum(
    domain_weight[d] * domain_scores[d]
    for d in domain_scores
)
pass_fail = "PASS" if weighted_score >= 70.0 else "FAIL"
weak_domains = [d for d,s in domain_scores.items() if s < 70.0]
```

---

## 11. Agent: Cert Recommendation (B3)

### File

`src/cert_prep/b3_cert_recommendation_agent.py`

### Responsibility

Given AssessmentResult, decide next certification and action.

### Next-Cert Logic

```python
SYNERGY_MAP = {
    "AI-102": "AZ-204",
    "AZ-204": "AZ-305",
    "DP-100": "AI-102",
    "AZ-900": "AI-102",
}
next_cert = SYNERGY_MAP.get(current_exam, "AZ-305")
```

### Remediation vs Booking Branch

```python
if result.score_pct >= 70:
    return CertRecommendation(ready_to_book=True, next_cert=next_cert,
                              booking_checklist=[...])
else:
    weak = result.weak_domains
    return CertRecommendation(ready_to_book=False,
                              remediation_steps=[f"{d}: scored {s:.0f}%, need 70%"
                                                 for d,s in result.domain_scores.items()
                                                 if s < 70])
```

---

## 12. Orchestration and Concurrency

### 12.1 Orchestrator Pattern

`streamlit_app.py` is the orchestrator. It:
1. Validates phase inputs through guardrails before calling agents
2. Stores all agent outputs to `st.session_state`
3. Persists all outputs to SQLite
4. Records timing metadata per agent step
5. Drives the 6-tab UI from session state

### 12.2 Parallel Execution

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

t0 = time.perf_counter()
with ThreadPoolExecutor(max_workers=2) as pool:
    future_plan = pool.submit(StudyPlanAgent().run, profile)
    future_path = pool.submit(LearningPathCuratorAgent().run, profile)
    plan          = future_plan.result()
    learning_path = future_path.result()
parallel_ms = int((time.perf_counter() - t0) * 1000)
st.session_state["parallel_agent_ms"] = parallel_ms
```

StudyPlanAgent and LearningPathCuratorAgent are independent — neither reads the other's output. Running them in parallel reduces wall-clock latency by ~50%.

### 12.3 Agent Trace

Every agent call logs an `AgentStep`:

```python
step = AgentStep(
    run_id       = st.session_state["run_id"],
    step_index   = next_step_index(),
    agent_name   = agent.__class__.__name__,
    input_hash   = sha256(str(inputs))[:8],
    output_hash  = sha256(str(output))[:8],
    duration_ms  = elapsed_ms,
    timestamp    = datetime.utcnow().isoformat(),
)
save_agent_step(step)
```

The trace is viewable in the Admin Dashboard, and also shown in Tab 1 as a collapsible "Agent Trace" expander.

---

## 13. HITL Gates

### Gate 1 — Progress Check-In (Tab 4)

- User inputs: hours spent, per-domain self-ratings, practice score, notes
- Triggers: ProgressAgent → ReadinessAssessment
- Non-blocking: low readiness shows a warning but does not stop the user

### Gate 2 — Mock Quiz (Tab 5)

- User answers: 30 multiple-choice questions (radio buttons)
- All questions must be answered before submit button activates
- Triggers: AssessmentAgent scoring → AssessmentResult
- Feeds into: CertRecommendationAgent in Tab 6

Both gates write to SQLite and to `st.session_state`. On session restore, gates are not shown again if already submitted.

---

## 14. SQLite Persistence Layer

### File

`src/cert_prep/database.py`

### Tables

| Table | Purpose | Key Columns |
|---|---|---|
| `students` | Auth + persona data | id, name, password_hash, role |
| `raw_inputs` | Serialised RawStudentInput | student_name, json_blob, created_at |
| `learner_profiles` | Serialised LearnerProfile | student_name, exam_target, json_blob |
| `study_plans` | Serialised StudyPlan | student_name, version, json_blob |
| `learning_paths` | Serialised LearningPath | student_name, exam_target, json_blob |
| `progress_snapshots` | Serialised ProgressSnapshot | student_name, json_blob |
| `readiness_assessments` | Serialised ReadinessAssessment | student_name, readiness_pct |
| `assessment_results` | Serialised AssessmentResult | student_name, score_pct, pass_fail |
| `cert_recommendations` | Serialised CertRecommendation | student_name, next_cert |
| `agent_steps` | Observability trace | run_id, step_index, agent_name, duration_ms |
| `guardrail_violations` | Guardrail audit | code, level, message, student_name |

### Connection Management

```python
DB_PATH = Path(__file__).parent.parent.parent / "certprep.db"

def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)
```

Concurrent writes from ThreadPoolExecutor are safe because each agent write happens after thread completion (in the orchestrator), not inside the parallel threads.

---

## 15. Session State Management

Streamlit rerenders on every user interaction. Session state is the only persistent store within a browser session. Keys are namespaced by feature to avoid collision.

### Lifecycle

1. **Login:** `logged_in`, `login_name`, `user_email` set
2. **Intake submit:** `raw`, `guardrail_result` set
3. **Profiling:** `profile` set
4. **Parallel planning:** `plan`, `learning_path`, `parallel_agent_ms` set
5. **Gate 1 submit:** `progress_submitted=True`, `progress_snapshot`, `readiness` set
6. **Gate 2 submit:** `quiz_submitted=True`, `assessment_result` set
7. **Recommendation:** `cert_recommendation` set
8. **Edit profile:** `editing_profile=True` set → form shown → `editing_profile` popped on re-submit

---

## 16. Mock vs Live Mode

| Aspect | Mock | Live (Azure OpenAI) |
|---|---|---|
| Profiling | Rule-based keyword scoring | GPT-4o JSON-structured response |
| Study plan | Deterministic algorithm | Same deterministic algorithm |
| Learning path | MODULE_CATALOGUE lookup | Same catalogue lookup |
| Quiz | Static question bank | Same question bank |
| Cost | Zero | Azure OpenAI credits |
| Latency | < 50ms | 2–15 seconds |
| Reproducibility | 100% deterministic | Stochastic (temp=0.2) |
| Competition demo | Default visible path | Available via sidebar toggle |

The mock/live switch is per session, set via the sidebar "Azure OpenAI Config" expander.

---

## 17. Admin Dashboard

### File

`pages/1_Admin_Dashboard.py`

### Access

URL: `/pages/1_Admin_Dashboard` after login. Admin credentials: `admin` / `agents2026`.

### Data Sources

All data comes from SQLite queries — no in-memory session state is used. This ensures the dashboard reflects all students, not just the currently logged-in session.

### Agent Trace HTML Rendering

```python
level_colour = {"INFO": "#3b82f6", "WARN": "#f59e0b", "BLOCK": "#ef4444"}
html = f"""
<div style="border-left:3px solid {level_colour['INFO']};
            padding:8px; margin-bottom:6px; background:#1e293b">
  <strong>{step.agent_name}</strong>
  <span style="color:#94a3b8;font-size:11px">{step.timestamp} · {step.duration_ms}ms</span>
  <div>{step.input_summary}</div>
</div>
"""
st.markdown(html, unsafe_allow_html=True)
```

---

## 18. Multi-Cert Support

The system fully supports **5 Microsoft certification exams** via `EXAM_DOMAIN_REGISTRY` in `src/cert_prep/models.py`. The Learning Path Catalogue in `b1_1_learning_path_curator.py` covers all 5 exams with 81 curated Microsoft Learn modules.

| Exam | Full Name | Domains | Modules |
|------|-----------|---------|---------|
| AI-102 | Azure AI Engineer Associate | 6 | 24 |
| AI-900 | Azure AI Fundamentals | 5 | 15 |
| AZ-204 | Azure Developer Associate | 5 | 18 |
| AZ-305 | Azure Solutions Architect Expert | 4 | 16 |
| DP-100 | Azure Data Scientist Associate | 4 | 16 |

```python
# models.py
EXAM_DOMAIN_REGISTRY: dict[str, list[dict]] = {
    "AI-102": EXAM_DOMAINS,     # 6 domains
    "AI-900": AI900_DOMAINS,    # 5 domains
    "AZ-204": AZ204_DOMAINS,    # 5 domains
    "DP-100": DP100_DOMAINS,    # 4 domains
    "AZ-305": AZ305_DOMAINS,    # 4 domains
}
```

Adding a new cert requires:
1. Adding domain definitions to `models.py` → `EXAM_DOMAIN_REGISTRY`
2. Adding module catalogue entries to `_LEARN_CATALOGUE` in `b1_1_learning_path_curator.py`
3. Adding prereq mapping in `StudyPlanAgent._PREREQ_MAP`
4. Adding synergy mapping in `CertRecommendationAgent.SYNERGY_MAP`

No code changes to agents or orchestrator are needed.

---

## 19. UI Architecture

### Layout

```
streamlit_app.py
├── Sidebar (persona buttons, Azure config expander, nav)
├── Login screen (3 demo cards + custom login)
└── Main area
    ├── Phase 0-2: Intake form → profile spinner
    └── Phase 3-6: 6-tab navigator
        ├── Tab 1: Domain Radar + Agent Trace
        ├── Tab 2: Study Plan Gantt (Plotly)
        ├── Tab 3: Learning Path module cards
        ├── Tab 4: [HITL Gate 1 form | Readiness result]
        ├── Tab 5: [HITL Gate 2 quiz | Score result]
        └── Tab 6: Cert Recommendation + next cert
```

### Theme

The app uses custom CSS injected via `st.markdown(css, unsafe_allow_html=True)` to implement a dark theme with `#0f172a` background, `#1e293b` card backgrounds, and `#3b82f6` accent.

---

## 20. Security and Safety

### Content Safety (G-16)

Background text is checked for a keyword list before being used in any prompt or displayed to other users.

### URL Safety (G-17)

All module URLs are validated before display. Only `learn.microsoft.com`, `docs.microsoft.com`, and `azure.microsoft.com` are whitelisted. Unverified URLs are excluded and logged.

### Auth

Demo-grade auth: passwords are compared as plain strings. Production would use PBKDF2 or bcrypt.

### Secrets Management

Azure OpenAI credentials are entered in the sidebar and stored in `st.session_state` (not written to disk). They are passed to `os.environ` only during the LLM call.

---

## 21. Performance Characteristics

| Metric | Mock Mode | Live Mode |
|---|---|---|
| Intake → first tab rendered | < 200ms | 3–15s (LLM call) |
| Parallel planning (both agents) | < 50ms | < 50ms (no LLM) |
| Gate 1 → readiness result | < 20ms | < 20ms |
| Gate 2 quiz scoring (30q) | < 20ms | < 20ms |
| SQLite read (restore session) | < 50ms | < 50ms |
| Admin Dashboard load (10 students) | < 100ms | < 100ms |

ThreadPoolExecutor reduces parallel agent wall-clock time by ~50% vs sequential. Measured timing is recorded in `parallel_agent_ms` and displayed in the Admin Dashboard.

---

## 22. Deployment

### Local

```powershell
cd "d:\OneDrive\Athiq\MSFT\Agents League"
.venv\Scripts\python -m streamlit run streamlit_app.py
```

### Streamlit Community Cloud

```
Repository: https://github.com/athiq-ahmed/agentsleague
Branch:     master
Main file:  streamlit_app.py
Python:     3.11
```

### Requirements

```
streamlit>=1.35
openai>=1.30
pydantic>=2.0
plotly>=5.0
```

All dependencies in `requirements.txt`. No Docker required for demo deployment — Streamlit Community Cloud provisions automatically.
