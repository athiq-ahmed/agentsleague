# 🏆 Agents League — Battle #2: Certification Prep Multi-Agent System

> **Track:** Reasoning Agents · Microsoft AI Foundry
> **Team:** Athiq Ahmed
> **Repo:** [athiq-ahmed/agentsleague](https://github.com/athiq-ahmed/agentsleague)
> **Live Demo:** [agentsleague.streamlit.app](https://agentsleague.streamlit.app)

A **production-grade multi-agent AI system** that creates personalised, adaptive study plans for any Microsoft certification exam. Eight specialised agents collaborate through a typed sequential pipeline with human-in-the-loop gates, 17 responsible AI guardrails, and full reasoning trace explainability — all runnable without any Azure credentials via mock mode.

---

## 🔀 Agent Orchestration Patterns

### Patterns Implemented

| Pattern | Status | Where |
|---------|--------|-------|
| **Sequential Pipeline** | ✅ Primary | `streamlit_app.py` → Intake → Profiling → LearningPath → StudyPlan → Assessment → CertRec |
| **Typed Handoff** | ✅ Every stage | `RawStudentInput` → `LearnerProfile` → `StudyPlan`/`LearningPath` → `ReadinessAssessment` → `CertRecommendation` |
| **Human-in-the-Loop (HITL)** | ✅ Two gates | Progress Check-In form + Quiz submission before downstream agents run |
| **Conditional Routing** | ✅ Readiness Gate | Score ≥ 70% → GO path; < 70% → Remediation loop back to Study Plan |
| **Guardrail Middleware** | ✅ Every transition | 17 rules across 6 categories, BLOCK/WARN/INFO at every agent boundary |
| **Concurrent (Fan-out)** | 🟡 Architecturally ready | `StudyPlanAgent` + `LearningPathCuratorAgent` both consume only `LearnerProfile` — parallelisable via `asyncio.gather()` in production |

### Sequential → Parallel Latency Design

Current execution (mock: ~0.5s, live Azure OpenAI: ~10–14s):

```
Intake → Guardrails → Profiler ──► StudyPlan      (~3–5s)
                                └──► LearningPath  (~3s)   ← SEQUENTIAL NOW
                                  total: ~14s
```

Production-optimised with `asyncio.gather()`:

```
Intake → Guardrails → Profiler ──► StudyPlan   ─┐
                              └──► LearningPath ─┘► merge  (~5s parallel)
                                  total: ~8s
```

> **Why not Magentic-One today?**
> Magentic-One's dynamic orchestrator helps when agents have non-deterministic routing (an orchestrator deciding at runtime which specialist to invoke). Our pipeline has a hard data dependency: `StudyPlanAgent` requires the fully-structured `LearnerProfile` Pydantic object — not raw text. B0 (Profiler) must always complete first regardless of orchestrator. Magentic-One would add per-token overhead without routing benefit here. The right next step is `asyncio` parallelism for B1.1 agents. Magentic-One fits a future "multi-expert deliberation" pattern where Profiler + domain expert agents debate a learner's skill level.

---

## 🛡️ Responsible AI Guardrails — 17 Rules

The `GuardrailsPipeline` is **cross-cutting middleware**, not a standalone agent. It wraps every transition point.

```
Agent A  →  GuardrailsPipeline  →  Agent B
            ├── BLOCK  →  pipeline stops, error shown to user
            ├── WARN   →  pipeline continues with visible warning
            └── INFO   →  advisory, logged in trace only
```

| Rules | Category | Level | What It Checks |
|-------|----------|-------|----------------|
| G-01..G-05 | **Input Validation** | BLOCK/WARN/INFO | Non-empty fields, hours ∈ [1–80], weeks ∈ [1–52], recognised exam codes, PII notice |
| G-06..G-08 | **Profile Integrity** | BLOCK/WARN | 6 domain profiles present, confidence ∈ [0.0, 1.0], risk domain IDs valid |
| G-09..G-10 | **Study Plan Bounds** | BLOCK/WARN | No `start_week > end_week`, total hours ≤ 110% budget |
| G-11..G-13 | **Progress Validity** | BLOCK | Hours ≥ 0, self-ratings ∈ [1–5], practice scores ∈ [0–100] |
| G-14..G-15 | **Quiz Integrity** | WARN/BLOCK | Minimum 5 questions, no duplicate question IDs |
| G-16..G-17 | **Content Safety & URL Trust** | BLOCK/WARN | Heuristic harmful content; URLs must be `learn.microsoft.com`, `pearsonvue.com`, or `aka.ms` |

All violations surface in the **Admin Dashboard** with code, level, message, and field for full auditability.

---

## ✨ Production Best Practices Applied

### 1. Typed Data Contracts — No Raw Text Passing

Every agent hands off a **strongly-typed Pydantic `BaseModel` or Python `dataclass`**, never a raw string. This enables compile-time-like safety and deterministic guardrail validation.

```python
# What we do — typed handoff
profile: LearnerProfile = LearnerProfilingAgent().run(raw)     # Pydantic model, validated
plan:    StudyPlan      = StudyPlanAgent().run_with_raw(profile, existing_certs=[...])

# What we avoid — raw text passing
result = agent_b.run(str(agent_a.run(raw_text)))   # no type safety, no contract
```

### 2. Safety-First Architecture (Not Bolted On)

Guardrails are architectural first-class citizens defined in `guardrails.py` before any agent code was written. A BLOCK-level violation halts the pipeline with a clear `st.error()` banner and `st.stop()` — no partial state is saved.

```python
_input_result = GuardrailsPipeline().check_input(raw)
if _input_result.blocked:
    for v in _input_result.violations:
        if v.level == GuardrailLevel.BLOCK:
            st.error(f"Guardrail [{v.code}]: {v.message}")
    st.stop()   # pipeline does NOT proceed
```

### 3. Human-in-the-Loop by Design

Two explicit HITL gates prevent meaningless automated assessments:

- **Progress Gate**: Learner submits real study hours, domain self-ratings, and practice exam score first. `ProgressAgent` uses this data — without it, readiness is undefined.
- **Quiz Gate**: Learner clicks "Generate Quiz", reads and answers questions, then submits. Only then does `AssessmentAgent` score the answers and produce `AssessmentResult`.

Without these gates, the system would output fictional readiness numbers from no real input.

### 4. Exam-Agnostic via Domain Registry

The system is not hardcoded to AI-102. `EXAM_DOMAIN_REGISTRY` in `models.py` supports 6+ exam families. Adding a new certification requires only a registry entry — zero agent code changes.

```python
# Swap exam by changing one key
domains = get_exam_domains("AZ-305")   # returns AZ-305 domain weights
domains = get_exam_domains("DP-100")   # returns DP-100 domain weights
```

Current registry: AI-102, AI-900, AZ-204, AZ-305, AZ-400, DP-100, DP-203, SC-100, MS-102.

### 5. Mock Mode = Full Parity, No Credentials Needed

`b1_mock_profiler.py` is a **rule-based profiler** that exactly mirrors LLM profiler output. It uses:
- 40+ keyword-to-domain regex patterns for concern topic mapping
- 6-exam × 6-cert domain boost matrices (existing cert → domain confidence boost)
- Background keyword sets for `ExperienceLevel` inference (`_BG_ML_KEYWORDS`, `_BG_AZURE_INFRA`, `_BG_DEV_KEYWORDS`)
- Learning style regex patterns (hands-on → `LAB_FIRST`, reference → `REFERENCE`, etc.)

### 6. Transparent Readiness Formula

`ProgressAgent` uses a **documented, explainable formula** — not a black-box model:

```
readiness_pct = (0.55 × domain_confidence) + (0.25 × hours_ratio) + (0.20 × practice_score)
```

- `domain_confidence` = mean self-rated domain score (1–5 scale, normalised)
- `hours_ratio` = hours_spent / total_budget_hours (capped at 1.0)
- `practice_score` = practice exam score / 100

Weights are configurable and the formula is visible to users in the UI.

### 7. Study Plan Algorithm — Largest Remainder Method

`StudyPlanAgent` allocates study weeks using a proportional algorithm:
1. Compute each domain's raw week allocation = `domain_weight × total_study_weeks`
2. Take floor of each allocation, keep remainders
3. Use **Largest Remainder Method** to distribute any leftover weeks — highest-remainder domains get +1 week
4. Front-load risk domains (critical → high → medium → low)
5. Schedule skip-recommended domains minimally at the end

This ensures total weeks always equals the budget exactly with fair distribution.

### 8. Quiz Question Distribution — Largest Remainder Sampling

`AssessmentAgent` distributes quiz questions across domains proportionally to exam weights, using the same Largest Remainder Method. For a 10-question quiz on AI-102:

```
computer_vision (22.5%) →  2 questions (floor 2, remainder 0.25)
nlp             (22.5%) →  2 questions
plan_manage     (17.5%) →  2 questions (gets +1 from remainder)
document_int.   (17.5%) →  2 questions (gets +1 from remainder)
generative_ai   (10.0%) →  1 question
conversational  (10.0%) →  1 question
                         = 10 total ✓
```

### 9. SQLite Persistence for Session Recovery

All profile, plan, trace, and progress data is persisted to `cert_prep_data.db`. Returning users recover their session by entering name + PIN — no re-profiling needed. Schema: `students`, `profiles`, `plans`, `learning_paths`, `traces`, `progress` tables.

### 10. Separation of Concerns

```
models.py      ← Pure data definitions (no logic, no I/O, no imports from agents)
config.py      ← Environment config only (Azure creds, defaults)
guardrails.py  ← Safety layer only (no business logic)
b0_*           ← Intake + Profiling agents
b1_*           ← Planning agents (study plan, learning path, progress)
b2_*           ← Assessment agents
b3_*           ← Recommendation agents
streamlit_app.py ← Orchestrator + UI (calls agents, manages st.session_state, renders)
```

No circular imports. Each layer only imports from layers below it.

---

## 🤖 Agent Inventory

| # | Agent | Module | Input → Output | Role |
|---|-------|--------|----------------|------|
| 1 | **Safety Guardrails** | `guardrails.py` | Any → `GuardrailResult` | 17-rule cross-cutting middleware at every transition |
| 2 | **Learner Intake** | `b0_intake_agent.py` | UI form → `RawStudentInput` | Collect background, goals, constraints |
| 3 | **Learner Profiler** | `b1_mock_profiler.py` | `RawStudentInput` → `LearnerProfile` | Infer experience level, learning style, per-domain confidence |
| 4 | **Learning Path Curator** | `b1_1_learning_path_curator.py` | `LearnerProfile` → `LearningPath` | Map domains to curated MS Learn modules, skip strong domains |
| 5 | **Study Plan Generator** | `b1_1_study_plan_agent.py` | `LearnerProfile` → `StudyPlan` | Week-by-week Gantt, Largest Remainder allocation, prereq gap |
| 6 | **Progress Tracker** | `b1_2_progress_agent.py` | `ProgressSnapshot` → `ReadinessAssessment` | Weighted readiness formula, GO/NO-GO verdict, nudges |
| 7 | **Assessment Builder** | `b2_assessment_agent.py` | `LearnerProfile` → `Assessment`+`AssessmentResult` | 30-Q bank per exam, domain-weighted sampling, scoring |
| 8 | **Cert Recommender** | `b3_cert_recommendation_agent.py` | `AssessmentResult` → `CertRecommendation` | Next-cert path, booking checklist, remediation plan |

---

## 🏗️ Architecture Overview

```
 ┌──────────── Guardrails Middleware (G-01..G-17, all transitions) ──────────┐
 │                                                                           │
 │  Student Input (UI form)                                                  │
 │        │ [G-01..G-05]                                                     │
 │        ▼                                                                  │
 │  LearnerProfilingAgent → LearnerProfile                                   │
 │        │                                                                  │
 │        ├─[G-06..G-08]──► StudyPlanAgent        → StudyPlan + Gantt       │
 │        └─[G-17]       ──► LearningPathCurator  → LearningPath            │
 │                                  │                                        │
 │                       HITL: Progress Check-In (form submit)               │
 │                                  │ [G-11..G-13]                           │
 │                                  ▼                                        │
 │                        ProgressAgent → ReadinessAssessment                │
 │                                  │                                        │
 │                       HITL: Quiz Submission (40 questions)                │
 │                                  │ [G-14..G-15]                           │
 │                                  ▼                                        │
 │                        AssessmentAgent → AssessmentResult                 │
 │                                  │                                        │
 │                         ◇ Score >= 70%?                                   │
 │                       YES │          NO → Remediation → StudyPlan        │
 │                           ▼                                               │
 │                  CertRecommendationAgent → CertRecommendation             │
 │                                                                           │
 └──────────────────────────────────────────────────────────────────────────┘
                                 │
                    Streamlit UI (7 tabs) + Admin Dashboard
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- (Optional) Azure OpenAI resource for live LLM mode

### Install & Run

```bash
git clone https://github.com/athiq-ahmed/agentsleague.git
cd agentsleague

python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
streamlit run streamlit_app.py  # opens http://localhost:8501
```

No Azure credentials needed — mock mode works fully out of the box.

### Configure Azure OpenAI (optional)

Create a `.env` file:

```
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com
AZURE_OPENAI_API_KEY=<your-key>
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-12-01-preview
```

Then in the app, expand "Azure OpenAI Settings", check "Use Live Azure OpenAI", enter credentials.

### Demo Credentials

| Role | Login |
|------|-------|
| New Learner | Name: anything · PIN: `1234` |
| Admin | Username: `admin` · Password: `agents2026` |

---

## 📁 Project Structure

```
agentsleague/
├── streamlit_app.py                      # Orchestrator + 7-tab UI (~3300 lines)
├── pages/
│   └── 1_Admin_Dashboard.py              # Agent audit dashboard
├── src/cert_prep/
│   ├── models.py                         # Data models + EXAM_DOMAIN_REGISTRY
│   ├── config.py                         # Azure OpenAI config loader
│   ├── guardrails.py                     # 17-rule safety pipeline (GuardrailsPipeline)
│   ├── agent_trace.py                    # AgentStep / RunTrace observability
│   ├── b0_intake_agent.py                # Learner intake (LLM or mock)
│   ├── b1_mock_profiler.py               # Rule-based profiler (no LLM)
│   ├── b1_1_learning_path_curator.py     # MS Learn module curator
│   ├── b1_1_study_plan_agent.py          # Gantt study plan generator
│   ├── b1_2_progress_agent.py            # Readiness tracker
│   ├── b2_assessment_agent.py            # Quiz builder + scorer
│   ├── b3_cert_recommendation_agent.py   # Next-cert recommender
│   └── database.py                       # SQLite persistence
├── docs/
│   ├── architecture.md                   # Technical architecture deep-dive
│   ├── judge_playbook.md                 # Hackathon judge reference
│   └── user_guide.md                     # End-user walkthrough
├── .streamlit/config.toml                # Theme + server config
├── requirements.txt
└── README.md
```

---

## 🔑 Key Data Models

```python
# Input dataclass (collected from UI form)
@dataclass
class RawStudentInput:
    student_name: str
    exam_target: str           # e.g. "AI-102"
    background_text: str       # free-text background description
    existing_certs: list[str]  # e.g. ["AZ-104", "AI-900"]
    hours_per_week: float
    weeks_available: int
    concern_topics: list[str]  # free-text topics the student is unsure about
    preferred_style: str       # free-text learning style preference

# Core learner profile (Pydantic — validated on creation)
class LearnerProfile(BaseModel):
    exam_target: str
    experience_level: ExperienceLevel   # BEGINNER / INTERMEDIATE / ADVANCED_AZURE / EXPERT_ML
    learning_style: LearningStyle       # LINEAR / LAB_FIRST / REFERENCE / ADAPTIVE
    domain_profiles: list[DomainProfile]
    risk_domains: list[str]             # domain IDs with confidence below threshold
    modules_to_skip: list[str]          # domain IDs with strong prior knowledge
    hours_per_week: float
    total_budget_hours: float

# Study plan (dataclass — domain schedule)
@dataclass
class StudyPlan:
    tasks: list[StudyTask]    # one task per active domain
    total_weeks: int
    review_start_week: int
    prerequisites: list[Prerequisite]
    prereq_gap: bool
    prereq_message: str

# Readiness verdict
@dataclass
class ReadinessAssessment:
    readiness_pct: float   # 0–100, from weighted formula
    verdict_label: str     # "Ready" / "Almost Ready" / "Needs More Prep"
    exam_go_nogo: str      # "GO" / "CONDITIONAL GO" / "NOT YET"
    hours_remaining: float
    weeks_remaining: int
    verdict_colour: str    # hex colour for UI rendering
```

---

## 📦 Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `streamlit` | >=1.35.0 | UI framework — tabs, forms, charts |
| `plotly` | >=5.0.0 | Gantt, bar charts, radar/spider plots |
| `openai` | >=1.30.0 | Azure OpenAI SDK (live LLM mode) |
| `pydantic` | >=2.0.0 | Typed data models with validation |
| `python-dotenv` | >=1.0.0 | `.env` file loading |
| `rich` | >=13.7.0 | Debug / CLI terminal output |
| `reportlab` | >=4.0.0 | PDF report generation (optional) |

---

## 🔮 Roadmap

| Feature | Priority | Description |
|---------|----------|-------------|
| `asyncio` parallel agents | High | Run `StudyPlanAgent` + `LearningPathCuratorAgent` concurrently — saves ~3s |
| Azure AI Content Safety | High | Replace heuristic G-16 with Azure AI Content Safety API |
| Magentic-One deliberation | Medium | Multi-expert profiler debate for uncertain learner skill levels |
| MCP MS Learn server | Medium | Live MS Learn search via Model Context Protocol |
| Copilot Studio integration | Medium | Visual pipeline designer + built-in monitoring |
| Streaming responses | Low | Stream LLM tokens to UI instead of waiting for full response |
| Azure Communication Services | Low | Replace SMTP with ACS for production email delivery |

---

## 📄 License

Created for the **Microsoft Agents League** hackathon — educational and demonstration purposes.
