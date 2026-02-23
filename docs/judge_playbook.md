# Judge Playbook — CertPrep Multi-Agent System

> This document is designed for competition judges evaluating the CertPrep entry for Agents League 2026. It explains the multi-agent architecture, key design decisions, scoring dimensions, and answers to likely technical questions.

---

## Table of Contents

1. [Elevator Pitch](#1-elevator-pitch)
2. [Why Multi-Agent](#2-why-multi-agent)
3. [Agent Inventory](#3-agent-inventory)
4. [Guardrails Deep Dive](#4-guardrails-deep-dive)
5. [Study Plan Algorithm](#5-study-plan-algorithm)
6. [Readiness Formula](#6-readiness-formula)
7. [End-to-End Data Flow](#7-end-to-end-data-flow)
8. [Concurrent Execution Argument](#8-concurrent-execution-argument)
9. [Azure AI Services Mapping](#9-azure-ai-services-mapping)
10. [Production Deployment Path](#10-production-deployment-path)
11. [Competition Scoring Self-Assessment](#11-competition-scoring-self-assessment)

---

## 1. Elevator Pitch

> Most learners buy a course, then stall. CertPrep uses a pipeline of specialised AI agents — one to understand you, one to plan, one to curate, one to measure progress, one to test, one to recommend — each with guardrails preventing hallucinations at every boundary. The result is a personalised, verifiable, agentic study companion that knows when you are ready to book, and which cert to pursue next.

**Three differentiators:**

| Differentiator | Description |
|---|---|
| Agent specialisation | Each agent has a single, bounded responsibility. No monolithic prompt doing everything. |
| Guardrail enforcement | 17 rules, BLOCK and WARN levels, applied between every phase. All violations auditable in Admin Dashboard. |
| HITL loops | Two human-in-the-loop gates. The system checks real learner progress before advancing. |

---

## 2. Why Multi-Agent

### Bounded Complexity

A single GPT-4 prompt doing all 6 phases would require ~4000 tokens of instruction and degrades on edge cases. Each agent has one task:

- **LearnerProfiler:** background text → domain confidence scores
- **StudyPlanAgent:** domain scores → weekly schedule
- **LearningPathCurator:** domain scores → MS Learn module list
- **ProgressAgent:** self-ratings + practice score → readiness percentage
- **AssessmentAgent:** domain weaknesses → 30 weighted questions
- **CertRecommender:** quiz score → booking decision + next cert

### Parallelism

StudyPlanAgent and LearningPathCuratorAgent are independent. Both take LearnerProfile as input and produce different outputs. Running them in parallel (ThreadPoolExecutor) halves wall-clock time.

```python
with ThreadPoolExecutor(max_workers=2) as pool:
    f_plan = pool.submit(StudyPlanAgent().run, profile)
    f_path = pool.submit(LearningPathCuratorAgent().run, profile)
    plan   = f_plan.result()
    path   = f_path.result()
```

The Admin Dashboard shows measured parallel execution time. Typical: 12–35ms in mock mode.

### Independent Testability

Each agent has a clean interface: `run(input) -> output`. They can be unit-tested, swapped, and mocked independently. The orchestrator does not know how profiling works — it only cares about the LearnerProfile contract.

### Graduated Safety

Different agents have different failure modes. A hallucinated module URL is a different problem from a hallucinated study plan duration. Each phase has its own guardrail set applied at the right boundary.

### Human Checkpoints

Two HITL gates interrupt the pipeline:
- **Gate 1:** How much have you studied? How confident do you feel?
- **Gate 2:** Answer these 30 questions.

The agents produce the inputs for these gates and interpret the outputs — humans provide the data.

---

## 3. Agent Inventory

| # | Agent | Module | Input | Output |
|---|---|---|---|---|
| 0 | Intake Guard | guardrails.py (G-01..G-05) | RawStudentInput | GuardrailResult |
| 1 | Learner Profiler | b1_mock_profiler.py | RawStudentInput | LearnerProfile |
| 2 | Study Planner | b1_1_study_plan_agent.py | LearnerProfile | StudyPlan |
| 3 | Path Curator | b1_1_learning_path_curator.py | LearnerProfile | LearningPath |
| 4 | Progress Tracker | b1_2_progress_agent.py | ProgressSnapshot | ReadinessAssessment |
| 5 | Assessment | b2_assessment_agent.py | LearnerProfile | AssessmentResult |
| 6 | Cert Recommender | b3_cert_recommendation_agent.py | AssessmentResult | CertRecommendation |

---

## 4. Guardrails Deep Dive

### G-02 — Exam Registry Validation

The exam code must exist in `EXAM_DOMAIN_REGISTRY`. This prevents any downstream agent from running against an unknown exam with no domain definitions.

```python
if raw.exam_target not in EXAM_DOMAIN_REGISTRY:
    return GuardrailViolation(
        code    = 'G-02',
        level   = GuardrailLevel.BLOCK,
        message = f"Exam code '{raw.exam_target}' is not in the supported registry."
    )
```

Without this guardrail: StudyPlanAgent receives a LearnerProfile with 0 domains → Largest Remainder divides by zero.

### G-17 — URL Origin Allowlist

Every URL returned by LearningPathCuratorAgent is checked against a trusted origin set.

```python
TRUSTED_ORIGINS = {
    'learn.microsoft.com',
    'docs.microsoft.com',
    'azure.microsoft.com',
}

def check_G17(url):
    netloc = urlparse(url).netloc.removeprefix('www.')
    if netloc not in TRUSTED_ORIGINS:
        return GuardrailViolation(code='G-17', level=GuardrailLevel.WARN,
                                  message=f'Unverified URL excluded: {netloc}')
    return None
```

WARN not BLOCK: a single bad URL should not halt the entire learning path.

### All 17 Rules

| Code | Phase | Level | Check |
|------|-------|-------|-------|
| G-01 | Intake | BLOCK | student_name non-empty |
| G-02 | Intake | BLOCK | exam_target in EXAM_DOMAIN_REGISTRY |
| G-03 | Intake | BLOCK | hours_per_week in [1, 80] |
| G-04 | Intake | BLOCK | weeks_available in [1, 52] |
| G-05 | Intake | BLOCK | len(background_text) > 10 |
| G-06 | Profile | BLOCK | len(domain_profiles) == expected_domains(exam) |
| G-07 | Profile | BLOCK | all confidence_score in [0.0, 1.0] |
| G-08 | Profile | BLOCK | all risk_domain IDs in registry |
| G-09 | Study Plan | WARN | total_hours <= budget * 1.1 |
| G-10 | Study Plan | WARN | all WeekBlock.domain_id in domain_profiles |
| G-11 | Progress | BLOCK | hours_spent >= 0 |
| G-12 | Progress | BLOCK | all domain_ratings in [1, 5] |
| G-13 | Progress | BLOCK | practice_score in [0, 100] |
| G-14 | Quiz | BLOCK | len(questions) >= 5 |
| G-15 | Quiz | BLOCK | no duplicate question IDs |
| G-16 | Content | BLOCK | background_text free of disallowed keywords |
| G-17 | URL | WARN | all module URLs from trusted origins |

### Audit Trail

Every violation is persisted to the `guardrail_violations` SQLite table. Admin Dashboard shows colour-coded violations. Judges can verify guardrails are actually firing — not just present in code.

---

## 5. Study Plan Algorithm

### Largest Remainder Allocation

Allocates `total_hours = hours_per_week × weeks_available` across domains weighted by inverse confidence (weaker domains get more time).

**Worked example: Alex Chen, AI-102, 12hr/wk × 10 weeks = 120 hours**

| Domain | Confidence | Inv. Weight | Normalised | Raw Alloc | Floored | Final |
|--------|-----------|-------------|------------|-----------|---------|-------|
| D1 | 0.20 | 0.80 | 0.165 | 19.8 | 19 | 19 |
| D2 | 0.15 | 0.85 | 0.175 | 21.0 | 21 | 21 |
| D3 | 0.10 | 0.90 | 0.186 | 22.3 | 22 | 23 |
| D4 | 0.25 | 0.75 | 0.155 | 18.6 | 18 | 18 |
| D5 | 0.15 | 0.85 | 0.175 | 21.0 | 21 | 21 |
| D6 | 0.30 | 0.70 | 0.144 | 17.3 | 17 | 18 |
| **Total** | | | 1.000 | 120.0 | 118 | **120** |

Sum of floored = 118. Deficit = 2. Top 2 remainders: D3 (0.3), D6 (0.3) → each gets +1.

**Key property:** Sum is always exactly `total_hours`. No hours lost to rounding.

---

## 6. Readiness Formula

```
readiness = 0.55 × c_bar + 0.25 × h_u + 0.20 × p
```

Where:
- `c_bar` = mean normalised confidence = (1/|D|) × Σ (r_d − 1) / 4  (rating 1–5 → 0–1)
- `h_u` = hours utilisation = min(hours_spent / hours_budget, 1.0)
- `p` = practice score proportion = practice_score / 100

**Worked example:**

Ratings: [3, 2, 2, 3, 2, 4] → c_bar = (0.50+0.25+0.25+0.50+0.25+0.75)/6 = 0.417  
Hours spent=8, budget=12 → h_u = 0.667  
Practice score=45 → p = 0.45  

readiness = 0.55×0.417 + 0.25×0.667 + 0.20×0.45 = 0.229 + 0.167 + 0.090 = **0.486 → 48.6%**

Verdict: **NOT YET** (below 50%)

**Weight rationale:** Confidence (0.55) is highest because it directly measures domain knowledge. Hours (0.25) rewards effort. Practice score (0.20) is a proxy for exam readiness.

---

## 7. End-to-End Data Flow

```
Browser
  |
  v
streamlit_app.py (orchestrator)
  |
  +-- [G-01..G-05] BLOCK -> user corrects form
  |
  +-- Profiler Agent
  |    Mock: b1_mock_profiler.py (rule engine)
  |    Live: LearnerProfilingAgent -> Azure OpenAI GPT-4o
  |    Output: LearnerProfile -> SQLite
  |
  +-- [G-06..G-08] BLOCK -> bug in profiler
  |
  +-- ThreadPoolExecutor
  |    +-- StudyPlanAgent -> StudyPlan -> SQLite
  |    +-- LearningPathCuratorAgent -[G-17]-> LearningPath -> SQLite
  |
  +-- [G-09..G-10] WARN, [G-17] WARN
  |
  +-- HITL Gate 1 (Tab 4) -> user fills form
  |    +-- ProgressAgent -> ReadinessAssessment
  |
  +-- HITL Gate 2 (Tab 5) -> user answers quiz
  |    +-- AssessmentAgent -> AssessmentResult -> SQLite
  |
  +-- CertRecommendationAgent -> CertRecommendation -> SQLite
       |
       v
     Tab 6: booking decision + next cert + remediation plan
```

---

## 8. Concurrent Execution Argument

**Claim:** StudyPlanAgent and LearningPathCuratorAgent run in parallel.

**Evidence visible to judges:**
1. Admin Dashboard shows `Parallel agents completed in Xms` with measured timing
2. Timing recorded in `st.session_state['parallel_agent_ms']` and shown in Tab 1 Agent Trace
3. Both agent outputs appear atomically in the trace

**Why safe to parallelise:** Both agents take LearnerProfile as read-only input. Neither writes to shared mutable state. SQLite writes happen in the orchestrator after thread completion.

**GIL note:** For pure Python, the GIL limits CPU parallelism. However, both agents in mock mode are I/O-bound (SQLite reads). In live mode they make HTTP calls that release the GIL. ThreadPoolExecutor correctly overlaps both cases.

---

## 9. Azure AI Services Mapping

| Azure Service | Role in CertPrep | Benefit |
|---|---|---|
| Azure OpenAI (GPT-4o) | LearnerProfilingAgent in live mode | Structured JSON output, low temperature |
| Azure AI Foundry | Agent orchestration (production roadmap) | Native multi-agent patterns, Connected Agent support |
| Azure AI Search | Knowledge retrieval for module catalogue | Semantic search over MS Learn content |
| Azure Cosmos DB | Production learner data store | Global distribution, sub-10ms reads, session TTL |
| Azure Monitor | Telemetry, guardrail violation alerts | Built-in dashboard, alert rules for BLOCK events |
| Azure Key Vault | Secrets management in production | API key rotation without code deployment |
| Azure Container Apps | Streamlit hosting in production | Auto-scale, managed TLS, GitHub Actions CD |
| Azure Content Safety | G-16 content filtering in production | Managed harmful-content detection API |

### AI Foundry Production Migration

Current build: `streamlit_app.py` is the orchestrator, calling agents as Python functions.

Production target:

```
AI Foundry Project
+-- Agent: LearnerProfilerAgent     (Azure OpenAI tool)
+-- Agent: StudyPlanAgent           (Python function tool)
+-- Agent: LearningPathCuratorAgent (Azure AI Search tool)
+-- Agent: ProgressTrackerAgent     (Python function tool)
+-- Agent: AssessmentAgent          (Python function tool)
+-- Agent: CertRecommenderAgent     (Python function tool)

Orchestrator: AI Foundry Thread + Assistant API
  -> Supervisor routes tasks to specialist agents
  -> Thread memory maintains context across HITL gates
  -> Azure AI Evaluation SDK for agent quality metrics
```

---

## 10. Production Deployment Path

### Phase 1 — Current (Competition)
- SQLite (local file)
- Mock profiler (rule engine) + Azure OpenAI optional via sidebar toggle
- Streamlit Community Cloud

### Phase 2 — Production MVP
- Azure Cosmos DB replaces SQLite
- Azure OpenAI always-on (GPT-4o)
- Azure Container Apps for hosting
- Azure Key Vault + Azure Monitor

### Phase 3 — Full AI Foundry Migration
- AI Foundry multi-agent threads
- Connected Agents (LearnerProfiler sub-calls LearningPathCurator)
- Azure AI Search integration for live MS Learn catalogue
- Azure Content Safety for G-16

### Phase 4 — Futuristic Vision (12+ months)

| Feature | Technology |
|---|---|
| Voice intake | Azure Speech + GPT-4o |
| Real-time MS Learn progress sync | Microsoft Graph API |
| Cohort analysis | Azure ML + Cosmos DB analytics |
| Dynamic question bank | Azure AI Search semantic ranker |
| Exam score correlation | Pearson VUE API |

---

## 11. Competition Scoring Self-Assessment

| Dimension | Max | Our Score | Justification |
|---|---|---|---|
| Technical Innovation | 25 | 22 | 7-agent pipeline, LR allocation algorithm, guardrail framework, HITL gates |
| Azure Services Usage | 20 | 18 | GPT-4o live mode, AI Foundry roadmap, 8 services documented |
| Problem Impact | 20 | 19 | Real problem (cert failure rate), personalised plans, booking readiness gate |
| Demo Quality | 20 | 17 | 3 instant demo scenarios, Gantt + radar charts, Admin audit dashboard |
| Code Quality | 15 | 13 | Typed models (Pydantic), guardrail separation, parallel execution evidence |
| **Total** | **100** | **89** | |

### Expected Judge Questions

**Q: Is this really multi-agent or just one big prompt?**  
A: Each agent is a separate Python class with its own typed input-output contract. They are independently callable and testable. Admin Dashboard shows each agent step with individual timing.

**Q: How do you prevent hallucinations?**  
A: Three mechanisms: (1) 17 guardrail rules with BLOCK/WARN levels between every phase, (2) `response_format=json_object` for all GPT-4o calls with Pydantic validation, (3) URL allowlisting (G-17) prevents hallucinated links from reaching users.

**Q: What is the HITL value-add?**  
A: The ProgressAgent cannot know how the learner actually felt studying. Gate 1 captures self-ratings and hours spent. Gate 2 provides a 30-question diagnostic identifying weak domains for remediation. Without these gates, the system only recommends based on background text — no feedback loop.

**Q: Why Largest Remainder for study plan?**  
A: It guarantees every available study hour is allocated to exactly one domain with no rounding loss. Standard round-to-nearest loses hours when total_hours is not divisible by domain count. LR is O(n log n) and produces provably optimal allocations.

**Q: Can this scale beyond one learner?**  
A: SQLite scales to thousands of learners (read-heavy workload). The orchestrator is stateless (all state in SQLite + session_state). Replacing SQLite with Cosmos DB requires changing only the `database.py` connection string.

**Q: What is novel versus a RAG chatbot?**  
A: Five differences: (1) Structured per-domain confidence scores, not free-text answers; (2) Deterministic study plan via LR algorithm; (3) Readiness gating that tells users when NOT to book; (4) Next-cert recommendation with synergy map; (5) Multi-student admin view with full audit trail.
