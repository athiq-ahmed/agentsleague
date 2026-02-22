# 🏆 Agents League — Battle #2: Certification Prep Multi-Agent System

> **Track:** Reasoning Agents · Microsoft AI Foundry  
> **Team:** Athiq Ahmed  
> **Repo:** [athiq-ahmed/agentsleague](https://github.com/athiq-ahmed/agentsleague)

A multi-agent AI system that creates **personalised, adaptive study plans** for any Microsoft certification exam. Six specialised agents collaborate to profile each learner, map existing skills to exam domains, generate week-by-week study schedules, run practice assessments, and track readiness — all orchestrated with reasoning traces for full explainability.

---

## 🔀 Agent Orchestration Patterns

As multi-agent solutions grow in complexity, choosing the right orchestration pattern is critical. This project demonstrates several production-ready patterns:

### Patterns Implemented

| Pattern | Status | Where in Code |
|---------|--------|---------------|
| **Sequential Pipeline** | ✅ Primary | `streamlit_app.py` — Intake → Profiling → Learning Path → Study Plan → Assessment → Cert Recommendation |
| **Handoff** | ✅ Implemented | Each agent produces a typed output (`LearnerProfile`, `StudyPlan`, etc.) that is explicitly handed off to the next agent via `st.session_state` |
| **Human-in-the-Loop (HITL)** | ✅ Implemented | Two explicit gates: Progress Check-In form and Quiz submission before `ProgressAgent` / `AssessmentAgent` run |
| **Conditional Routing** | ✅ Implemented | Readiness Gate — score ≥ 70% → GO path; < 70% → Remediation loop back to Study Plan |
| **Concurrent (Fan-out)** | 🟡 Architecturally ready | `LearningPathCuratorAgent` and `StudyPlanAgent` both consume `LearnerProfile` independently — can run in parallel |

### How Sequential Coordination Works

The agents execute in a strict linear pipeline where each agent's **typed output becomes the next agent's input**:

```
📥 Intake → 🛡️ Guardrails → 🧠 Profiler → 🗺️ Learning Path → 📅 Study Plan
                                                                      ↓
                                              📊 Cert Recommender ← 🧪 Assessment ← 📈 Progress
```

Every transition is wrapped by the **Guardrails Pipeline** (17 rules, G-01 to G-17) that validates inputs/outputs and can BLOCK, WARN, or INFO at each step.

### How Handoff Works

Agents hand off work through **shared typed dataclass/Pydantic models** — not raw text or unstructured messages:

| From Agent | Handoff Object | To Agent |
|------------|---------------|----------|
| LearnerIntakeAgent | `RawStudentInput` | GuardrailsPipeline → LearnerProfilingAgent |
| LearnerProfilingAgent | `LearnerProfile` | LearningPathCuratorAgent + StudyPlanAgent |
| ProgressAgent | `ReadinessAssessment` | CertificationRecommendationAgent |
| AssessmentAgent | `AssessmentResult` | CertificationRecommendationAgent |

### Patterns Considered for Future Work

| Pattern | Use Case | Status |
|---------|----------|--------|
| **Group Chat** | Multi-agent deliberation (e.g., profiler + domain expert agents debating a learner's skill level) | 🔮 Planned |
| **Magnetic** | Dynamic agent attraction/routing based on content type | 🔮 Planned |
| **Copilot Studio Orchestration** | Visual agent pipeline design with built-in monitoring | 🔮 Planned |

---

## 🛡️ Responsible AI & Guardrails

Safety is not an afterthought — the **GuardrailsPipeline** wraps every agent transition with 17 validation rules across 6 categories:

| Rules | Category | Level | Description |
|-------|----------|-------|-------------|
| G-01 to G-05 | **Input Validation** | BLOCK / WARN / INFO | Non-empty fields, sensible hours/weeks, recognised exam codes, PII notice |
| G-06 to G-08 | **Profile Integrity** | BLOCK / WARN | Domain completeness, confidence bounds [0.0–1.0], valid risk domain IDs |
| G-09 to G-10 | **Study Plan Bounds** | BLOCK / WARN | No start > end week, total hours within ±10% of budget |
| G-11 to G-13 | **Progress Data Validity** | BLOCK | Non-negative hours, self-ratings [1–5], practice scores [0–100] |
| G-14 to G-15 | **Quiz Integrity** | WARN / BLOCK | Minimum 5 questions, no duplicate question IDs |
| G-16 to G-17 | **Content Safety & URL Trust** | BLOCK / WARN | Harmful content detection, URLs must be from `learn.microsoft.com` or `pearsonvue.com` |

**Guardrail Levels:**
- **🚫 BLOCK** — Hard-stop: pipeline does not proceed
- **⚠️ WARN** — Soft-stop: pipeline proceeds with visible warning
- **ℹ️ INFO** — Advisory: logged in agent trace

All guardrail violations are surfaced in the **Admin Dashboard** for complete auditability.

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| **6 AI Agents** | Intake, Profiling, Learning Path Curator, Study Plan Generator, Assessment Builder, Progress Tracker |
| **Any Microsoft Cert** | Exam-agnostic design — AI-102, DP-100, AZ-204, AZ-305, and more via `EXAM_DOMAIN_REGISTRY` |
| **Adaptive Study Plans** | Week-by-week Gantt schedules weighted by domain risk and exam blueprint |
| **Practice Quizzes** | Domain-weighted exam-style questions with tiered verification |
| **Readiness Assessment** | GO / CONDITIONAL GO / NOT YET verdict with nudges and email summaries |
| **Responsible AI** | PII filtering, anti-cheating checks, content safety guardrails |
| **Admin Dashboard** | Full agent interaction audit trail, journey funnel, timing breakdown |
| **Mock Mode** | Works end-to-end without any Azure credentials (rule-based agents) |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    🛡️ Safety & Guardrails                       │
│              PII filter · anti-cheat · content safety           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📥 Student    →  🧠 Intake &   →  🗺️ Learning Path  →  📅 Study │
│     Input          Profiling        Curator             Plan    │
│                                                                 │
│                    ┌──────────────────┐                          │
│                    │ Domain Confidence│                          │
│                    │    Scorer        │                          │
│                    └────────┬─────────┘                          │
│                             ▼                                   │
│                    ◇ Readiness Gate ◇                            │
│                    │ Yes          │ No                           │
│                    ▼              ▼                              │
│            ✅ Assessment    🔄 Remediate                         │
│               Builder       & Replan                            │
│                    │                                            │
│                    ▼                                            │
│            📊 Progress &                                        │
│               Readiness                                         │
│               Assessment                                        │
├─────────────────────────────────────────────────────────────────┤
│            📋 Reasoning Trace Log (explainability)              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🤖 Agent Roles

| # | Agent | Module | Responsibility |
|---|-------|--------|---------------|
| 1 | **Safety Guardrails** | `guardrails.py` | PII redaction, anti-cheating, content policy enforcement |
| 2 | **Learner Intake** | `intake_agent.py` | Collect background, goals, constraints via conversational form |
| 3 | **Learner Profiler** | `mock_profiler.py` | Infer experience level, learning style, per-domain confidence |
| 4 | **Learning Path Curator** | `learning_path_curator.py` | Map skills to exam domains, curate MS Learn resources |
| 5 | **Study Plan Generator** | `study_plan_agent.py` | Week-by-week schedule, prerequisite gap analysis, priority ordering |
| 6 | **Assessment Builder** | `assessment_agent.py` | Exam-style quiz generation, tiered verification, scoring |
| 7 | **Progress Tracker** | `progress_agent.py` | Readiness assessment, nudges, GO/NO-GO verdict, email summaries |
| 8 | **Cert Recommender** | `cert_recommendation_agent.py` | Suggest next certifications based on profile and goals |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- (Optional) Azure OpenAI resource for live LLM agents
- (Optional) Node.js 18+ for MS Learn MCP server

### Install & Run

```bash
# Clone
git clone https://github.com/athiq-ahmed/agentsleague.git
cd agentsleague

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run the app (mock mode — no Azure needed)
streamlit run streamlit_app.py
```

### Configure Azure OpenAI (optional)

```bash
# Edit .env with your credentials:
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com
AZURE_OPENAI_API_KEY=<your-key>
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-12-01-preview
```

---

## 📁 Project Structure

```
agentsleague/
├── streamlit_app.py              # Main Streamlit app (login, 7-tab UI)
├── pages/
│   └── 1_Admin_Dashboard.py      # Admin-only agent audit dashboard
├── src/
│   ├── cert_prep/
│   │   ├── models.py             # Data models, EXAM_DOMAINS registry
│   │   ├── config.py             # Azure OpenAI config loader
│   │   ├── intake_agent.py       # Learner intake (LLM or CLI)
│   │   ├── mock_profiler.py      # Rule-based profiler (no LLM needed)
│   │   ├── learning_path_curator.py  # MS Learn resource curator
│   │   ├── study_plan_agent.py   # Study plan generator
│   │   ├── assessment_agent.py   # Quiz builder + verifier + scorer
│   │   ├── progress_agent.py     # Readiness tracker + email summaries
│   │   ├── cert_recommendation_agent.py  # Next-cert suggestions
│   │   ├── guardrails.py         # Safety pipeline
│   │   └── agent_trace.py        # Run trace logging for admin dashboard
│   └── demo_intake.py            # CLI demo script
├── docs/
│   ├── TODO.md                   # Azure setup guide & task tracker
│   └── architecture.md           # Detailed architecture documentation
├── .env                          # Azure credentials (gitignored)
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

---

## 🔐 Access Credentials (Demo)

| Role | Credential |
|------|-----------|
| **New / Returning Learner** | PIN: `1234` |
| **Admin** | Username: `admin` · Password: `agents2026` |

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| **Frontend** | Streamlit + Plotly |
| **Agent Framework** | Python (Pydantic models, dataclass pipelines) |
| **LLM Backend** | Azure OpenAI (gpt-4o) via OpenAI SDK |
| **Orchestration** | Azure AI Foundry (planned) |
| **Tool Use** | MS Learn MCP Server (planned) |
| **Safety** | Azure AI Content Safety + custom GuardrailsPipeline (17 rules, G-01 to G-17) |
| **Orchestration Patterns** | Sequential Pipeline, Typed Handoff, Human-in-the-Loop, Conditional Routing |
| **Observability** | Agent trace logging, Gantt timeline, admin audit |

---

## 📄 License

This project was created for the **Microsoft Agents League** hackathon.  
For educational and demonstration purposes.
