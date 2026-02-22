# 🏆 Agents League — Battle #2: Certification Prep Multi-Agent System

> **Track:** Reasoning Agents · Microsoft AI Foundry  
> **Team:** Athiq Ahmed  
> **Repo:** [athiq-ahmed/agentsleague](https://github.com/athiq-ahmed/agentsleague)

A multi-agent AI system that creates **personalised, adaptive study plans** for any Microsoft certification exam. Six specialised agents collaborate to profile each learner, map existing skills to exam domains, generate week-by-week study schedules, run practice assessments, and track readiness — all orchestrated with reasoning traces for full explainability.

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
| **Safety** | Azure AI Content Safety + custom guardrails |
| **Observability** | Agent trace logging, Gantt timeline, admin audit |

---

## 📄 License

This project was created for the **Microsoft Agents League** hackathon.  
For educational and demonstration purposes.
