# 📋 Judge Playbook — Agents League Battle #2

> **Project:** Certification Prep Multi-Agent System  
> **Track:** Reasoning Agents · Microsoft AI Foundry  
> **Team:** Athiq Ahmed  
> **Repo:** [athiq-ahmed/agentsleague](https://github.com/athiq-ahmed/agentsleague)

---

## Executive Summary

This project is a **multi-agent AI system** that creates personalised, adaptive study plans for any Microsoft certification exam. Eight specialised agents collaborate through a **Sequential Pipeline** orchestration pattern with **typed handoffs**, **human-in-the-loop gates**, and **17 responsible AI guardrails** — all with full reasoning trace explainability.

---

## 1. Agent Orchestration Patterns

### Why Agent Orchestration Matters

As solutions grow in complexity beyond simple single-agent setups, the coordination pattern between agents becomes the most critical architectural decision. Poor orchestration leads to:
- Unpredictable agent interactions
- Data loss between stages
- No auditability of decisions
- Inability to enforce safety at transition points

This project demonstrates that **thoughtful orchestration patterns** create systems that are reliable, explainable, and safe.

### Patterns Demonstrated

#### ✅ Sequential Pipeline (Primary Pattern)

**How it works:** Agents execute in a strict linear order. Each agent's typed output becomes the next agent's input, with guardrails validating every transition.

```
Intake → [G-01..G-05] → Profiler → [G-06..G-08] → Learning Path + Study Plan
    → [G-09..G-10, G-17] → Progress → [G-11..G-13] → Assessment
    → [G-14..G-15] → Cert Recommendation → [G-16] → Output
```

**Why it fits this project:** Certification prep is inherently sequential — you cannot assess readiness without first having a study plan, and you cannot build a study plan without knowing the learner's profile.

**Code evidence:** `streamlit_app.py` orchestrates agents in order, storing each typed result in `st.session_state` before invoking the next agent.

#### ✅ Typed Handoff Pattern

**How it works:** Rather than passing raw text between agents, each agent produces a **strongly-typed data object** (Pydantic `BaseModel` or Python `dataclass`) that the downstream agent consumes.

| Handoff | Type | Validates |
|---------|------|-----------|
| Intake → Profiler | `RawStudentInput` | G-01..G-05 |
| Profiler → Learning Path / Study Plan | `LearnerProfile` | G-06..G-08 |
| Study Plan → Progress | `StudyPlan` | G-09..G-10 |
| Progress → Cert Recommender | `ReadinessAssessment` | G-11..G-13 |
| Assessment → Cert Recommender | `AssessmentResult` | G-14..G-15 |

**Why it matters:** Typed handoffs enable compile-time-like safety, make the data contract explicit, and allow guardrails to validate between every stage.

#### ✅ Human-in-the-Loop (HITL) Gates

**How it works:** The pipeline pauses at two critical points requiring genuine human input:

1. **Progress Check-In:** Learner submits hours spent, self-ratings per domain, and practice exam scores before `ProgressAgent` runs
2. **Quiz Submission:** Learner answers exam-style questions and submits before `AssessmentAgent` evaluates

**Why it matters:** Without HITL gates, readiness scores would be meaningless — the system verifies real learner effort.

#### ✅ Conditional Routing (Readiness Gate)

**How it works:** After assessment, the pipeline branches:
- Score ≥ 70% → **GO** path → exam booking checklist + next certification suggestions
- Score < 70% → **Remediation** loop → targeted study plan revisions → back to learning

### Patterns Considered for Future Work

| Pattern | Application | Rationale |
|---------|------------|-----------|
| **Concurrent (Fan-out/Fan-in)** | `LearningPathCuratorAgent` + `StudyPlanAgent` can run in parallel since both only need `LearnerProfile` | Reduces end-to-end latency |
| **Group Chat** | Profiler + domain expert agents debating learner skill levels | Multi-perspective assessment for edge cases |
| **Magnetic** | Dynamic agent routing based on content signals from MS Learn MCP | Auto-routes content to the most relevant specialist |
| **Copilot Studio** | Visual pipeline design with built-in monitoring | Enterprise deployment with admin approval gates |

---

## 2. Responsible AI Guardrails (17 Rules)

### Guardrail Architecture

The `GuardrailsPipeline` is a **cross-cutting safety layer** that wraps every agent transition. It is not a standalone agent — it is middleware enforced at every pipeline stage.

```
 Agent A  →  🛡️ GuardrailsPipeline  →  Agent B
              ├── BLOCK → 🚫 Pipeline stops
              ├── WARN  → ⚠️ Pipeline continues with warning
              └── INFO  → ℹ️ Logged in trace
```

### Complete Guardrail Catalogue

#### Input Guards (G-01 to G-05) — Before Intake Processing

| Code | Level | Rule | Rationale |
|------|-------|------|-----------|
| G-01 | BLOCK/WARN | Non-empty required fields (name, exam target, background) | Prevents empty pipeline runs |
| G-02 | WARN | Hours per week in [1, 80] | Flags unrealistic study commitments |
| G-03 | BLOCK/WARN | Weeks available in [1, 52] | Prevents impossible timelines |
| G-04 | WARN | Exam code in recognised catalogue (30+ Microsoft exams) | Graceful fallback for unknown exams |
| G-05 | INFO | PII redaction notice | Transparency: name stored in session only |

#### Profile Guards (G-06 to G-08) — After Profiling

| Code | Level | Rule | Rationale |
|------|-------|------|-----------|
| G-06 | WARN | All 6 domain profiles present | Ensures complete skill assessment |
| G-07 | BLOCK | Confidence scores in [0.0, 1.0] | Prevents invalid scoring data |
| G-08 | WARN | Risk domain IDs are valid | Catches profiler hallucination |

#### Study Plan Guards (G-09 to G-10) — After Planning

| Code | Level | Rule | Rationale |
|------|-------|------|-----------|
| G-09 | BLOCK | No task with `start_week > end_week` | Prevents impossible schedules |
| G-10 | WARN | Total hours ≤ 110% of budget | Flags scope creep |

#### Progress Guards (G-11 to G-13) — Before Assessment

| Code | Level | Rule | Rationale |
|------|-------|------|-----------|
| G-11 | BLOCK | Hours spent ≥ 0 | Data integrity |
| G-12 | BLOCK | Self-ratings in [1, 5] | Valid Likert scale |
| G-13 | BLOCK | Practice scores in [0, 100] | Valid percentage range |

#### Assessment Guards (G-14 to G-15) — After Quiz Generation

| Code | Level | Rule | Rationale |
|------|-------|------|-----------|
| G-14 | WARN | Minimum 5 questions | Ensures statistical reliability |
| G-15 | BLOCK | No duplicate question IDs | Prevents scoring errors |

#### Content Safety Guards (G-16 to G-17) — All Outputs

| Code | Level | Rule | Rationale |
|------|-------|------|-----------|
| G-16 | BLOCK | No harmful/profane content in free-text fields | Responsible AI compliance |
| G-17 | WARN | URLs must be from trusted domains (`learn.microsoft.com`, `pearsonvue.com`, `aka.ms`) | Prevents hallucinated/malicious links |

### Trusted URL Domains

Only URLs from these prefixes pass G-17:
- `https://learn.microsoft.com`
- `https://www.pearsonvue.com`
- `https://aka.ms`
- `https://azure.microsoft.com`

---

## 3. Agent Inventory

| # | Agent | Module | Orchestration Role | Guardrails |
|---|-------|--------|--------------------|-----------|
| 1 | **Safety Guardrails** | `guardrails.py` | Cross-cutting middleware at every transition | G-01 to G-17 |
| 2 | **Learner Intake** | `b0_intake_agent.py` | Pipeline entry point — collects user input | Input: G-01..G-05 |
| 3 | **Learner Profiler** | `b1_mock_profiler.py` | Infers experience, learning style, per-domain confidence | Output: G-06..G-08 |
| 4 | **Learning Path Curator** | `b1_1_learning_path_curator.py` | Maps skills to exam domains, curates MS Learn resources | Output: G-17 |
| 5 | **Study Plan Generator** | `b1_1_study_plan_agent.py` | Week-by-week Gantt schedule, priority ordering | Output: G-09..G-10 |
| 6 | **Progress Tracker** | `b1_2_progress_agent.py` | Readiness formula (0.55×domain + 0.25×hours + 0.20×practice), GO/NO-GO | Input: G-11..G-13 |
| 7 | **Assessment Builder** | `b2_assessment_agent.py` | 30-question bank, domain-weighted, Largest Remainder sampling | Output: G-14..G-15 |
| 8 | **Cert Recommender** | `b3_cert_recommendation_agent.py` | Next-cert suggestions, remediation plans | Output: G-16 |

---

## 4. Technical Architecture

### Data Flow

```
Student (Browser)
    │
    ▼
┌──────────────────────────────────────────┐
│  Block 0 — Input Layer                   │
│  LearnerIntakeAgent → RawStudentInput    │
│  🛡️ G-01..G-05                           │
└──────────────────────────────────────────┘
    │
    ▼
┌──────────────────────────────────────────┐
│  Block 1 — Profiling                     │
│  LearnerProfilingAgent → LearnerProfile  │
│  🛡️ G-06..G-08                           │
└──────────────────────────────────────────┘
    │
    ├──► LearningPathCuratorAgent → LearningPath  🛡️ G-17
    │
    ▼
┌──────────────────────────────────────────┐
│  Block 1.1 — Study Planning              │
│  StudyPlanAgent → StudyPlan + Gantt      │
│  🛡️ G-09..G-10                           │
└──────────────────────────────────────────┘
    │
    ▼  👤 HITL Gate: Progress Check-In
┌──────────────────────────────────────────┐
│  Block 1.2 — Progress Tracking           │
│  ProgressAgent → ReadinessAssessment     │
│  🛡️ G-11..G-13                           │
└──────────────────────────────────────────┘
    │
    ▼  👤 HITL Gate: Quiz Submission
┌──────────────────────────────────────────┐
│  Block 2 — Knowledge Assessment          │
│  AssessmentAgent → AssessmentResult      │
│  🛡️ G-14..G-15                           │
└──────────────────────────────────────────┘
    │
    ▼  ◇ Readiness Gate
┌──────────────────────────────────────────┐
│  Block 3 — Certification Decision        │
│  CertRecommendationAgent                 │
│  ≥70% → GO + next certs                 │
│  <70% → Remediation → ↩ Block 1.1       │
│  🛡️ G-16                                 │
└──────────────────────────────────────────┘
```

### Tech Stack

| Component | Technology |
|-----------|-----------|
| **Frontend** | Streamlit + Plotly (gauges, Gantt, bar charts) |
| **Agent Framework** | Python (Pydantic models, dataclass pipelines) |
| **LLM Backend** | Azure OpenAI (gpt-4o) via OpenAI SDK |
| **Orchestration Pattern** | Sequential Pipeline + Typed Handoff + HITL Gates |
| **Safety Layer** | Custom GuardrailsPipeline (17 rules) + Azure AI Content Safety (planned) |
| **Persistence** | SQLite via `sqlite3` |
| **Observability** | Agent trace logging (`AgentStep` / `RunTrace`), Admin Dashboard |
| **Email** | SMTP (optional) / Azure Communication Services (planned) |

---

## 5. Demo Walkthrough

### Credentials

| Role | Credential |
|------|-----------|
| New / Returning Learner | PIN: `1234` |
| Admin | Username: `admin` · Password: `agents2026` |

### Key Demo Scenarios

1. **New Learner Flow:**
   - Enter learner details → AI profiles skills → generates personalised study plan
   - Observe guardrail violations in real-time (try empty fields for G-01 BLOCK)
   - View Gantt chart, Learning Path with MS Learn modules

2. **Assessment Flow:**
   - Generate 10-question quiz → answer questions → see scored results
   - GO/CONDITIONAL GO/NOT YET verdict with domain breakdown
   - Cert recommendation + next certification path

3. **Admin Dashboard:**
   - Full agent interaction audit trail
   - Journey funnel visualisation
   - Timing breakdown per agent
   - Guardrail violation log

4. **Guardrails Demo:**
   - Submit form with empty name → G-01 BLOCK (pipeline stops)
   - Set hours to 0 → G-02 WARN (pipeline continues with warning)
   - All violations visible in Admin Dashboard trace

---

## 6. What Sets This Apart

| Differentiator | Detail |
|---------------|--------|
| **Principled Orchestration** | Not ad-hoc agent coupling — Sequential Pipeline with typed handoffs gives predictable, debuggable behaviour |
| **17 Guardrails at Every Transition** | Safety is baked into the architecture, not bolted on. BLOCK/WARN/INFO levels with full auditability |
| **Human-in-the-Loop by Design** | Two explicit gates prevent meaningless automated assessments |
| **Exam-Agnostic** | Works for 30+ Microsoft certifications via `EXAM_DOMAIN_REGISTRY` |
| **Full Explainability** | Reasoning traces for every agent decision, viewable in Admin Dashboard |
| **Mock Mode** | Complete end-to-end experience without any Azure credentials |
| **Conditional Routing** | Readiness Gate creates a feedback loop — failure routes to remediation, not dead ends |
