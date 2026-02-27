# Agents League Battle #2 — Submission Answers

> Prepared answers for the GitHub issue submission template at
> https://github.com/microsoft/agentsleague/issues/new?template=project.yml
>
> **Submission Deadline:** March 1, 2026 (11:59 PM PT)

---

## Track

**Reasoning Agents (Azure AI Foundry)**

---

## Project Name

**CertPrep Multi-Agent System — Personalised Microsoft Exam Preparation**

---

## GitHub Username

`@athiq-ahmed`

---

## Repository URL

https://github.com/athiq-ahmed/agentsleague

---

## Project Description

*(250 words max)*

The CertPrep Multi-Agent System is a production-grade AI solution for personalised Microsoft certification exam preparation, supporting 9 exam families (AI-102, DP-100, AZ-204, AZ-305, AZ-400, SC-100, AI-900, DP-203, MS-102).

Eight specialised reasoning agents collaborate through a typed, sequential + concurrent pipeline:

1. **LearnerProfilingAgent** — converts free-text background into a structured `LearnerProfile` via Azure AI Foundry SDK (Tier 1) or direct GPT-4o JSON-mode (Tier 2), with a deterministic rule-based fallback (Tier 3).
2. **StudyPlanAgent** — generates a week-by-week Gantt study schedule using the Largest Remainder algorithm to allocate hours without exceeding the learner's budget.
3. **LearningPathCuratorAgent** — maps each exam domain to curated MS Learn modules with trusted URLs, resource types, and estimated hours.
4. **ProgressAgent** — computes an exam-weighted readiness score (`0.55 × domain ratings + 0.25 × hours utilisation + 0.20 × practice score`).
5. **AssessmentAgent** — generates a 10-question domain-proportional mock quiz and scores it against the 60% pass threshold.
6. **CertificationRecommendationAgent** — issues a GO / CONDITIONAL GO / NOT YET booking verdict with next-cert suggestions and a remediation plan.

A 17-rule GuardrailsPipeline runs at every agent boundary. Two human-in-the-loop gates ensure agents act on real learner data, not assumptions. The full pipeline runs in under 1 second in mock mode (zero Azure credentials), enabling reliable live demonstrations at any time.

---

## Demo Video or Screenshots

- **Live Demo:** https://agentsleague.streamlit.app
- **Demo Guide:** [docs/demo_guide.md](demo_guide.md) — persona scripts and walkthrough steps
- **Admin Dashboard:** shows per-agent reasoning traces, guardrail audit, timing, and token counts

---

## Primary Programming Language

**Python**

---

## Key Technologies Used

| Technology | Role |
|------------|------|
| Azure AI Foundry Agent Service SDK (`azure-ai-projects`) | Tier 1 managed agent + conversation thread for `LearnerProfilingAgent` |
| Azure OpenAI GPT-4o (JSON mode) | Tier 2 structured profiling fallback; temperature=0.2 |
| Azure Content Safety (`azure-ai-contentsafety`) | G-16 guardrail — profanity and harmful-content filter |
| Streamlit | 7-tab interactive UI + Admin Dashboard |
| Pydantic v2 `BaseModel` | Typed handoff contracts at every agent boundary |
| `concurrent.futures.ThreadPoolExecutor` | Parallel fan-out of `StudyPlanAgent` ∥ `LearningPathCuratorAgent` |
| Plotly | Gantt chart, domain radar, agent timeline |
| SQLite (`sqlite3` stdlib) | Cross-session learner profile + reasoning trace persistence |
| ReportLab | PDF generation for profile and assessment reports |
| Python `smtplib` (STARTTLS) | Optional weekly study-progress email digest |
| `hashlib` SHA-256 | PIN hashing before SQLite storage |
| Custom `GuardrailsPipeline` (17 rules) | BLOCK / WARN / INFO at every agent boundary; PII, URL trust, content safety |
| `pytest` + parametrize | 342 automated tests across 15 modules; zero credentials required |
| Streamlit Community Cloud | Auto-deploy on `git push`; secrets via environment variables |
| Visual Studio Code + GitHub Copilot | Primary IDE; AI-assisted development throughout |

---

## Submission Type

**Individual**

---

## Team Members

*(Individual submission — no team members)*

---

## Quick Setup Summary

```bash
# 1. Clone the repository
git clone https://github.com/athiq-ahmed/agentsleague.git
cd agentsleague

# 2. Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows PowerShell

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
notepad .env   # Fill in AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, and optionally
               # AZURE_AI_PROJECT_CONNECTION_STRING for Foundry SDK mode
               # Run `az login` once for local Foundry authentication

# 5. Run the application
python -m streamlit run streamlit_app.py

# 6. Run the test suite (no Azure credentials needed)
python -m pytest tests/ -v
```

> **Zero-credential demo mode:** Leave `.env` keys blank or set `FORCE_MOCK_MODE=true` — the full 8-agent pipeline runs deterministically in under 1 second using the rule-based mock engine.

---

## Technical Highlights

- **3-tier LLM fallback chain** — `LearnerProfilingAgent` attempts Azure AI Foundry SDK (Tier 1), falls back to direct Azure OpenAI JSON-mode (Tier 2), and finally to a deterministic rule-based engine (Tier 3). All three tiers share the same Pydantic output contract, so downstream agents never know which tier ran.

- **Largest Remainder day allocation** — `StudyPlanAgent` uses the parliamentary Largest Remainder Method to distribute study time at the **day level** (`total_days = weeks × 7`) across domains, then converts day blocks to week bands and hours. Guarantees: (1) total days exactly equals budget; (2) every active domain receives at least 1 day (`max(1, int(d))` floor) — no domain is silently zeroed out.

- **Concurrent agent fan-out** — `StudyPlanAgent` and `LearningPathCuratorAgent` have no data dependency on each other; they run in true parallel via `ThreadPoolExecutor`, cutting Block 1 wall-clock time by ~50%.

- **17-rule exam-agnostic guardrail pipeline** — Every agent input and output is validated by a dedicated `GuardrailsPipeline` before the next stage proceeds. BLOCK-level violations call `st.stop()` immediately; nothing downstream ever sees invalid data.

- **Exam-weighted readiness formula** — Progress scoring uses `0.55 × domain ratings + 0.25 × hours utilisation + 0.20 × practice score`, with domain weights pulled from the per-exam registry (not hardcoded for AI-102), so the formula is accurate across all 9 supported certifications.

- **Demo PDF cache** — For demo personas, PDFs are generated once and served from `demo_pdfs/` on all subsequent clicks — no pipeline re-run needed, making live demos instant and reliable.

- **Schema-evolution safe SQLite** — All `*_from_dict` deserialization helpers use a `_dc_filter()` guard that silently drops unknown keys, preventing `TypeError` crashes when the data model evolves and old rows are read back.

---

## Challenges & Learnings

| Challenge | How We Solved It | Learning |
|-----------|-----------------|----------|
| **Streamlit + asyncio conflict** — `asyncio.gather()` raises `RuntimeError: event loop already running` inside Streamlit | Replaced with `concurrent.futures.ThreadPoolExecutor` — identical I/O latency, no event-loop conflict, stdlib only | Always profile async options in the target host runtime before committing to the pattern |
| **Schema evolution crashes** — Adding new fields to agent output dataclasses caused `TypeError` when loading old SQLite rows | Added `_dc_filter()` helper to all `*_from_dict` functions; unknown keys silently dropped | Design for forward and backward compatibility from day one; use a key guard on every deserialization boundary |
| **Hardcoded AI-102 domain weights** — `ProgressAgent` used AI-102 weights for all exams, giving wrong readiness scores for DP-100 learners | Refactored to call `get_exam_domains(profile.exam_target)` dynamically | Never hardcode domain-specific constants in shared utility functions; always derive from the registry |
| **`st.checkbox` key collision** — Using `hash()[:8]` string slicing raised `TypeError` in Streamlit widget key generation | Changed to `abs(hash(item))` (integer key) which Streamlit handles natively | Read widget key type requirements; integer keys are always safe |
| **PDF generation crashes on None fields** — `AttributeError` when optional profile fields were absent | Added `getattr(obj, field, default)` guards on every field access in PDF generation | Defensive attribute access is essential for any code path that renders stored data |
| **3-tier fallback complexity** — Keeping Foundry SDK, direct OpenAI, and mock engine in sync as the output contract evolved | Defined a single `_PROFILE_JSON_SCHEMA` constant and a shared Pydantic parser used by all three tiers | A single source-of-truth schema makes multi-tier systems maintainable; contract-first design prevents drift |
| **Live demo reliability** — API latency or missing credentials causing demo failures | Mock Mode runs the full 8-agent pipeline with zero credentials in < 1 second; demo personas pre-seeded in SQLite | Always build a zero-dependency demo path; live mode is a bonus, not a requirement |

---

## Contact Information

*(Provided separately to Microsoft)*

---

## Country/Region

United Kingdom

---

---

# Reasoning Patterns — Detailed Implementation Guide

This section provides a deep-dive into how each of the four core reasoning patterns from the Agents League starter kit is implemented in this system, mapped to the four challenge requirements.

---

## Challenge Requirements

### 1. Multi-agent system aligned with the challenge scenario (student preparation for Microsoft certification exams)

The system is purpose-built around the certification prep journey:

```
Intake → Profile → Plan ∥ Curate → Progress → Assess → Recommend
```

Each stage represents a distinct cognitive task in how a human coach would actually prepare a student for a Microsoft exam:

| Stage | Agent | Real-World Equivalent |
|-------|-------|----------------------|
| Intake form | `IntakeAgent` | Coach intake questionnaire |
| Background parsing | `LearnerProfilingAgent` | Coach reads CV and identifies knowledge gaps |
| Study scheduling | `StudyPlanAgent` | Coach builds week-by-week roadmap |
| Resource curation | `LearningPathCuratorAgent` | Coach recommends specific learning materials |
| Progress check | `ProgressAgent` | Coach reviews study journal and rates readiness |
| Mock exam | `AssessmentAgent` | Coach administers practice test |
| Booking decision | `CertificationRecommendationAgent` | Coach advises whether to book the exam now |

Every agent uses a **typed Pydantic contract** — no agent receives raw text from another agent. This mirrors how a human coaching team would exchange structured reports rather than informal notes.

---

### 2. Microsoft Foundry (UI or SDK) and/or the Microsoft Agent Framework

**Live Foundry SDK integration (`azure-ai-projects`):**

```python
# b0_intake_agent.py — Tier 1 implementation
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

client = AIProjectClient.from_connection_string(
    conn_str=settings.foundry.connection_string,   # AZURE_AI_PROJECT_CONNECTION_STRING
    credential=DefaultAzureCredential(),            # az login locally
)
agent = client.agents.create_agent(
    model="gpt-4o",
    name="LearnerProfilerAgent",
    instructions=PROFILER_SYSTEM_PROMPT,
)
thread  = client.agents.create_thread()
client.agents.create_message(thread_id=thread.id, role="user", content=user_message)
run     = client.agents.create_and_process_run(thread_id=thread.id, agent_id=agent.id)
messages = client.agents.list_messages(thread_id=thread.id)
profile_json = json.loads(messages.get_last_message_by_role("assistant").content[0].text.value)
client.agents.delete_agent(agent.id)   # clean up ephemeral agent
```

Every `LearnerProfilingAgent` run when `AZURE_AI_PROJECT_CONNECTION_STRING` is set:
- Creates a **managed Foundry agent** with a system prompt
- Creates a **conversation thread** (persistent, replayable)
- Executes `create_and_process_run()` — Foundry handles model routing, retries, token counting
- **Automatically appears in Foundry portal Tracing view** with latency, token usage, and request/response payload

The remaining agents (`StudyPlanAgent`, `LearningPathCuratorAgent`, `ProgressAgent`, `AssessmentAgent`, `CertificationRecommendationAgent`) use the same typed Pydantic output contracts and run via the custom Python orchestration pipeline — ready for migration to Foundry-managed agents as a near-term extension.

---

### 3. Reasoning and multi-step decision-making across agents

The pipeline demonstrates **five distinct forms of reasoning**:

**a) Conditional routing** — The score from `AssessmentAgent` determines the next agent:
```
score ≥ 70% → CertificationRecommendationAgent (GO path)
score 50–70% → targeted domain review
score < 50%  → full remediation loop back to StudyPlanAgent
```

**b) Weighted formula reasoning** — `ProgressAgent` combines three independent evidence sources:
```python
readiness = 0.55 * domain_confidence + 0.25 * hours_utilisation + 0.20 * practice_score
```
The weights are derived from exam blueprint structure (domain confidence is most predictive of exam success).

**c) Prerequisite gap reasoning** — `StudyPlanAgent` checks whether the learner holds prerequisite certs (e.g. AI-900 before AI-102) and adjusts the plan if not, adding extra foundational blocks automatically.

**d) Domain-proportional sampling** — `AssessmentAgent` samples quiz questions proportionally to exam domain weights so the mock quiz mirrors the actual exam blueprint distribution.

**e) Next-cert path reasoning** — `CertificationRecommendationAgent` uses a synergy map to recommend the most complementary next certification based on the learner's current exam and existing cert portfolio.

---

### 4. Integration with external tools, APIs, and/or MCP servers

| Integration | Type | What it provides |
|-------------|------|-----------------|
| Azure OpenAI GPT-4o | API (live) | LLM backbone for `LearnerProfilingAgent` JSON-mode structured profiling |
| Azure AI Foundry Agent Service | SDK (live) | Managed agent lifecycle, thread persistence, Foundry portal telemetry |
| Azure Content Safety | API (live) | G-16 guardrail — content moderation at every free-text input boundary |
| MS Learn module catalogue | Static registry (live) | 9-cert × domain curated resource table; URL trust-listed via G-17 |
| MCP `/ms-learn` server | MCP protocol (wired, active) | `MCP_MSLEARN_URL` in `.env` — live module catalogue fetch replaces static lookup when running |
| SQLite | Local persistence | Cross-session learner profiles, study plans, reasoning traces |
| SMTP email | Protocol (live) | Weekly progress digest with PDF attachment; triggered post-intake |
| PDF generation (ReportLab) | Library (live) | Learner profile PDF + assessment report with all agent outputs |

---

## Reasoning Patterns — Deep Dive

### Pattern 1: Planner–Executor

**Concept:** Separate agents responsible for planning (breaking down the problem) and execution (carrying out tasks step by step).

**In this system:**

The Planner–Executor pattern appears at two levels:

**Level 1 — Macro pipeline** (across agents):
- **Planner:** `LearnerProfilingAgent` analyses the learner's background and creates an abstract `LearnerProfile` — a structured breakdown of what the learner knows (`DomainProfile`) and what they need (`risk_domains`, `recommended_approach`). This is pure planning — no study tasks are created yet.
- **Executor:** `StudyPlanAgent` takes the `LearnerProfile` plan and executes it into a concrete week-by-week `StudyPlan` with `StudyTask` objects, specific start/end weeks, hours per domain, and priority levels. It doesn't reinterpret the learner's background — it faithfully executes the plan that the profiler produced.

**Level 2 — Within `StudyPlanAgent`** (internal):
- **Planner step:** Identifies prerequisites, calculates available hours, assigns priority levels (critical → high → medium → low → skip) per domain based on the learner's `knowledge_level` and `confidence_score`.
- **Executor step:** Applies the Largest Remainder Method to convert priority-weighted fractional hours into integer week-blocks that sum to exactly the learner's `total_budget_hours`.

**Why this separation matters:**
- `LearnerProfilingAgent` can be upgraded (Foundry SDK → direct OpenAI → mock) without touching `StudyPlanAgent`
- The typed `LearnerProfile` contract enforces that the planner's output is always valid before the executor starts
- Each agent can be unit-tested independently — 24 tests for `AssessmentAgent`, 23 for `StudyPlanAgent`

---

### Pattern 2: Critic / Verifier

**Concept:** Introduce an agent that reviews outputs, checks assumptions, and validates reasoning before final responses are returned.

**In this system, the Critic pattern is implemented at two levels:**

**Level 1 — GuardrailsPipeline (structural critic)**

The `GuardrailsPipeline` is a dedicated 17-rule critic that runs *between* every agent handoff:

```
Input → [G-01..G-05 input critic] → Agent → [G-06..G-17 output critic] → Next Agent
```

Each rule has a severity level and a code:
- `BLOCK` (G-01..G-05, G-16): halts pipeline via `st.stop()` — used for PII, harmful content, negative hours, empty exam target
- `WARN` (G-06..G-15): flags concern but allows continuation — used for abnormal domain counts, low confidence, unrealistic budgets
- `INFO` (G-17): informational — URL trust guard logs untrusted links

The pipeline doesn't just validate syntax — it validates *semantic reasonableness*:
- `G-07`: Is the number of domain profiles consistent with the exam blueprint?
- `G-09`: Does the study budget match what was declared in the profile?
- `G-10`: Is every domain covered by at least one study task?
- `G-17`: Are all MS Learn URLs in the curated path on the trusted allowlist?

**Level 2 — ProgressAgent (readiness critic)**

`ProgressAgent` acts as an evidence-based critic before the learner can attempt the mock quiz:
- Computes a weighted readiness score across three independent dimensions
- Issues a structured verdict: `EXAM_READY` / `ALMOST_THERE` / `NEEDS_WORK` / `NOT_READY`
- Generates domain-specific nudges: _"You've logged 65% of your budget hours but your Computer Vision confidence is still WEAK — focus 3 more hours on this domain before attempting the quiz"_
- The `exam_go_nogo` signal (`GO` / `CONDITIONAL GO` / `NOT YET`) directly gates the assessment flow — agents cannot skip this review

**Why this is stronger than typical critic patterns:**
- Critic is rule-based (deterministic, fully unit-testable) not LLM-based (non-deterministic)
- 71 dedicated unit tests cover every critic rule with passing and failing inputs
- BLOCK-level violations are uncatchable — `st.stop()` means the pipeline physically cannot continue

---

### Pattern 3: Self-reflection & Iteration

**Concept:** Allow agents to reflect on intermediate results and refine their approach when confidence is low or errors are detected.

**In this system:**

**Remediation loop (macro self-reflection):**

When `AssessmentAgent` scores the mock quiz below the 60% pass mark:
```
Score < 60% → CertificationRecommendationAgent issues:
  - go_for_exam = False
  - remediation_plan = "Focus on: Computer Vision (33%), NLP (40%)"
  - next_cert_suggestions = [DP-100 as building block]
```
The learner is shown the remediation plan, which feeds directly back into:
1. A revised `LearnerProfile` — the profiler can be re-run with updated confidence scores reflecting the quiz weak domains
2. A new `StudyPlan` — `StudyPlanAgent.run()` re-executes with the updated profile, producing a revised schedule that front-loads the weak domains

This is a **complete agent loop** — the same agents run again on updated inputs, not a reconfiguration.

**Confidence-based adaptation within StudyPlanAgent (micro self-reflection):**

`StudyPlanAgent` internally reflects on the profile before building the plan:
1. Reads `domain_profiles[i].confidence_score` and `knowledge_level` for each domain
2. Computes a priority weight: lower confidence → higher priority → more hours in earlier weeks
3. Re-checks whether the resulting allocation is feasible given `total_budget_hours`
4. If a domain with `knowledge_level == UNKNOWN` would get zero hours after Largest Remainder (too many high-priority domains), it elevates its priority to ensure it is never skipped

**HITL gates as structured reflection checkpoints:**

Rather than agents making assumptions about learner progress:
- **Gate 1** (before `ProgressAgent`): learner manually inputs hours spent per domain + self-rating + practice exam result — forcing active self-assessment
- **Gate 2** (before `CertificationRecommendationAgent`): learner manually answers the 10-question quiz — forcing active knowledge retrieval

These gates mean the iteration loop is grounded in real learner data at every step, not just model predictions.

---

### Pattern 4: Role-based Specialisation

**Concept:** Assign clear responsibilities to each agent to reduce overlap and improve reasoning quality.

**In this system, each agent has a single, bounded responsibility:**

| Agent | Sole Responsibility | What It Does NOT Do |
|-------|--------------------|--------------------|
| `LearnerProfilingAgent` | Parse free-text background → structured `LearnerProfile` | Does not schedule, curate, assess, or recommend |
| `StudyPlanAgent` | Temporal scheduling — when to study what, for how long | Does not suggest resources, assess knowledge, or decide booking |
| `LearningPathCuratorAgent` | Content discovery — which MS Learn modules per domain | Does not schedule, assess, or care about hours or weeks |
| `ProgressAgent` | Readiness measurement — weighted formula from HITL data | Does not generate questions, curate content, or book exams |
| `AssessmentAgent` | Knowledge evaluation — generate + score a domain-proportional quiz | Does not produce study plans, resources, or booking decisions |
| `CertificationRecommendationAgent` | Booking decision + next-cert path | Does not reassess knowledge or reschedule study time |

**Why strict role-based separation improves reasoning quality:**

1. **No redundant reasoning** — `StudyPlanAgent` never "re-profiles" the learner; it trusts `LearnerProfile.risk_domains` completely. This means the planning algorithm is purely algorithmic (Largest Remainder), not subject to LLM drift.

2. **Contract enforcement** — Each role boundary is enforced by a Pydantic model. `StudyPlanAgent` receives a `LearnerProfile`; it can only produce a `StudyPlan`. It cannot request more information from the user or call back to the profiler.

3. **Independent testability** — Because roles don't overlap, each agent can be unit-tested with a minimal fixture. The 24 `AssessmentAgent` tests never need a real `StudyPlan`; the 23 `StudyPlanAgent` tests never need a real `LearningPath`.

4. **Parallel execution is possible** — `StudyPlanAgent` and `LearningPathCuratorAgent` both receive only `LearnerProfile` as input and produce independent outputs. Their lack of overlap makes concurrent execution safe — they cannot collide on shared state.

5. **Failure isolation** — If `LearningPathCuratorAgent` encounters a domain with no curated modules, it returns an empty list for that domain and logs a `WARN` — it never blocks `StudyPlanAgent` from completing, and vice versa.

**Contrast with a monolithic approach:**

A single "CertPrepAgent" that tries to do all of the above would:
- Mix temporal reasoning (scheduling) with content reasoning (curation) — two completely different problem types
- Be impossible to test without mocking the entire Azure stack
- Be unable to run any two tasks in parallel
- Produce reasoning traces that are impossible to attribute to specific decisions

The role-based design means the Admin Dashboard can show exactly which agent made each decision, with its specific inputs and outputs — providing the explainability required for responsible AI deployment.
