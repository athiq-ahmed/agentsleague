# 🏆 Agents League — Battle #2: Multi-Cert Preparation System

> **Track:** Reasoning Agents · Microsoft AI Foundry · Battle #2
> **Team:** Athiq Ahmed
> **Repo:** [athiq-ahmed/agentsleague](https://github.com/athiq-ahmed/agentsleague) *(private)*
> **Live Demo:** [agentsleague.streamlit.app](https://agentsleague.streamlit.app)

A **production-grade multi-agent AI system** for personalised Microsoft certification preparation — supporting **9 exam families** (AI-102, DP-100, AZ-204, AZ-305, AZ-400, SC-100, AI-900, DP-203, MS-102). Eight specialised reasoning agents collaborate through a typed sequential + concurrent pipeline with human-in-the-loop gates, 17 responsible AI guardrails, and full reasoning trace explainability — runnable without Azure credentials via mock mode.

---

## 🏅 Competition Alignment

| Judging Criterion | Weight | Evidence |
|---|---|---|
| **Accuracy & Relevance** | 25% | ✅ 9-cert registry; exam-weighted domain sampling; prereq gap detection per cert; MS Learn URLs validated by guardrail G-17 |
| **Reasoning & Multi-step Thinking** | 25% | ✅ 8-agent pipeline with typed handoffs; conditional routing (score ≥ 70% → GO, < 70% → remediation loop); Planner–Executor + Critic patterns |
| **Creativity & Originality** | 15% | ✅ Exam-agnostic domain registry; Largest Remainder allocation algorithm; configurable readiness formula; concurrent agent fan-out via ThreadPoolExecutor |
| **User Experience & Presentation** | 15% | ✅ 7-tab Streamlit UI; Admin Dashboard with per-agent reasoning trace; Gantt / radar / bar charts; mock mode for zero-credential demo; optional email for weekly digest |
| **Reliability & Safety** | 20% | ✅ 17-rule GuardrailsPipeline (BLOCK/WARN/INFO); BLOCK halts pipeline via st.stop(); URL trust guard; content heuristic filter; SQLite persistence |

---

## 🛠️ Development Approach

**Chosen approach: Local code-first development in Visual Studio Code with Azure OpenAI integration**

Per the [Agents League Starter Kit](https://github.com/microsoft/agentsleague/tree/main/starter-kits/2-reasoning-agents), participants can use one of:

| Approach | Description | Status in This Project |
|----------|-------------|----------------------|
| **Local development (code-first)** | Build and test custom agentic solution locally with the [OSS Microsoft Agent Framework](https://github.com/microsoft/agent-framework) in Visual Studio Code | ✅ **Chosen** — custom Python pipeline built and tested locally in VS Code with GitHub Copilot |
| **Cloud-based (low-code/no-code)** | Use [Foundry UI](https://ai.azure.com/) to configure agents and workflows visually | ❌ Not chosen — code-first preferred for typed handoffs, deterministic algorithms, and unit-testable guardrails |
| **Cloud-based (code-first Foundry SDK)** | Use the [Foundry Agent Service SDK](https://learn.microsoft.com/azure/ai-foundry/how-to/develop/sdk-overview) to build programmatically in the cloud | ✅ **Implemented** — `azure-ai-projects` SDK active for `LearnerProfilingAgent` when `AZURE_AI_PROJECT_CONNECTION_STRING` is set |

### What We Actually Use

| Component | Technology | Notes |
|-----------|-----------|-------|
| **IDE** | Visual Studio Code | Primary development environment throughout |
| **AI-assisted development** | **GitHub Copilot** | Used extensively to accelerate code generation, refactoring, and test scaffolding |
| **Agent framework — Tier 1** | **`azure-ai-projects` SDK** (Azure AI Foundry Agent Service) | `LearnerProfilingAgent` uses `AIProjectClient.from_connection_string()` to create a managed Foundry agent + conversation thread; activated when `AZURE_AI_PROJECT_CONNECTION_STRING` is set |
| **Agent framework — Tier 2** | `openai.AzureOpenAI` direct call | Fallback when only `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_API_KEY` are set; identical output contract |
| **Agent framework — Tier 3** | Rule-based Python mock engine | Zero credentials needed; used for demo, testing, and offline development |
| **Custom orchestration** | Python pipeline (`ThreadPoolExecutor` fan-out) | Sequential typed stages between Foundry/OpenAI calls; Pydantic contracts at every boundary |
| **Data models / contracts** | Pydantic v2 `BaseModel` + `@dataclass` | Validated typed handoffs at every agent boundary |
| **Persistence** | SQLite (Python stdlib `sqlite3`) | Zero-dependency local store; schema portable to Azure Cosmos DB |
| **Hosting** | Streamlit Community Cloud | Auto-deploys from `git push`; secrets via environment variables |
| **Microsoft Agent Framework (OSS)** | Not used in current implementation | Architecture is compatible; migration path documented |

### Why Code-First Over Foundry UI?

The solution requires capabilities that are best expressed in code, not UI configuration:

- **Typed handoff contracts** — Pydantic `BaseModel` between every agent; no raw strings cross boundaries
- **Deterministic algorithms** — Largest Remainder allocation, weighted readiness formula (`0.55×confidence + 0.25×hours_utilisation + 0.20×practice_score`)
- **17-rule guardrail pipeline** — fully enumerable, unit-tested with 25 pytest tests, reproducible across runs
- **Conditional state machine** — `score ≥ 70%` → CertRecommendation; else → remediation loop back to StudyPlanAgent

### Azure AI Foundry Agent Service Integration

When `AZURE_AI_PROJECT_CONNECTION_STRING` is set, `LearnerProfilingAgent` uses the **`azure-ai-projects` SDK** to run as a proper Foundry-managed agent:

```python
# src/cert_prep/b0_intake_agent.py — Tier 1 (Foundry SDK)
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

client = AIProjectClient.from_connection_string(
    conn_str=settings.foundry.connection_string,   # AZURE_AI_PROJECT_CONNECTION_STRING
    credential=DefaultAzureCredential(),            # az login locally / SP vars in cloud
)
# Create a managed Foundry agent
agent = client.agents.create_agent(
    model=settings.openai.deployment,              # e.g. gpt-4o
    name="LearnerProfilerAgent",
    instructions=PROFILER_SYSTEM_PROMPT,
)
# Create conversation thread and run
thread = client.agents.create_thread()
client.agents.create_message(thread_id=thread.id, role="user", content=user_message)
run = client.agents.create_and_process_run(thread_id=thread.id, agent_id=agent.id)
# Extract structured JSON response
messages = client.agents.list_messages(thread_id=thread.id)
last_msg = messages.get_last_message_by_role("assistant")
profile_json = json.loads(last_msg.content[0].text.value)
# Cleanup — avoid accumulating ephemeral agents in Foundry project
client.agents.delete_agent(agent.id)
```

The agent automatically falls back to direct `AzureOpenAI` if Foundry credentials are absent, and to the rule-based mock if neither is configured — **all three tiers share the same Pydantic output contract**.

### Setting Up Foundry Credentials

```bash
# 1. Create an Azure AI Foundry project (if you don't have one)
az ml workspace create --kind hub -g <rg> -n <hub-name>
az ml workspace create --kind project -g <rg> -n <project-name> --hub-name <hub-name>

# 2. Get your connection string
# Azure portal → your Foundry project → gear icon → Project properties → copy

# 3. Authenticate locally
az login

# Or create a service principal for Streamlit Cloud:
az ad sp create-for-rbac --name certprep-sp --role Contributor --scopes /subscriptions/<sub-id>
# Set AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID from the output
```

### Models Used

| Mode | LLM | Backend |
|------|-----|---------|
| **Foundry SDK** | `gpt-4o` (or any deployment) | Azure AI Foundry Agent Service — managed agent + thread |
| **Direct OpenAI** | `gpt-4o` (configurable via `AZURE_OPENAI_DEPLOYMENT`) | Azure OpenAI API directly |
| **Mock** | Rule-based engine | Locally hosted — zero cost, zero credentials |

---

## ☁️ Azure Services Used

| Azure Service | Role in This System | Why We Use It | Key Benefit |
|---|---|---|---|
| **Azure OpenAI Service** (GPT-4o) | Powers `LearnerProfilingAgent` in live mode — converts free-text background into a structured `LearnerProfile` JSON via JSON-mode completion | Best-in-class reasoning for nuanced, multi-field extraction from unstructured learner text | JSON-mode guarantees valid structured output; enterprise SLA; no hallucinated schema |
| **Azure AI Foundry Agent Service** *(Tier 1 — active)* | `LearnerProfilingAgent` runs as a managed Foundry agent via `azure-ai-projects` SDK — `AIProjectClient` creates a persistent agent + thread, calls `create_and_process_run()`, extracts the response, then deletes the ephemeral agent | `AZURE_AI_PROJECT_CONNECTION_STRING` + Azure identity (DefaultAzureCredential / service principal) | Managed agent lifecycle, built-in conversation threads, Foundry portal telemetry |
| **Azure App Service / Streamlit Cloud** | Hosts the Streamlit web application publicly at `agentsleague.streamlit.app` | Zero-config container deployment; auto-scales; secrets management via environment variables | Deploy in minutes; built-in HTTPS; direct GitHub CI/CD integration |
| **Azure OpenAI Embeddings** *(roadmap)* | Semantic matching between learner background text and module catalogue entries | Vector search returns the most relevant MS Learn module for each weak domain | More accurate than keyword matching; enables personalised learning path beyond static lookup tables |
| **Azure AI Search** *(roadmap)* | Index the full MS Learn module catalogue (~4 000 modules) and search by exam domain, skill level, content type | Replaces static dictionary in `LearningPathCuratorAgent` with live, up-to-date catalogue | Real-time catalogue; faceted filtering by certification, locale, duration |
| **Azure Monitor / App Insights** *(roadmap)* | Telemetry for production agent runs — latency per agent, guardrail fire rate, parallel speedup ratio | Observability at scale; alerts when P95 latency exceeds threshold | Dashboards for each judging criterion (accuracy, reasoning depth, reliability) |
| **Azure Cosmos DB** *(roadmap)* | Replace SQLite with globally distributed multi-region learner data store | Required for production multi-tenant deployments; TTL policies for data retention compliance | 99.999% SLA; NoSQL schema flexibility matches our evolving agent output structs |
| **SMTP Email** *(current — any provider)* | Weekly study-progress digest sent to the learner's optional email address (collected at intake); uses Python `smtplib`, works with Gmail, Outlook, or any SMTP relay | Zero Azure dependency; plug in any SMTP provider (Gmail app-password, Outlook, SendGrid, etc.); degrades silently when `SMTP_USER`/`SMTP_PASS` are absent | Self-contained; no SDK required; email field collected but sending is opt-in | 
| **Azure Communication Services — Email** *(roadmap)* | Production-grade replacement for raw SMTP — use the [azure-communication-email](https://pypi.org/project/azure-communication-email/) SDK with a Foundry-provisioned sender domain (`DoNotReply@<guid>.azurecomm.net`) | First-party Azure managed service; no SMTP relay; built-in delivery telemetry and bounce handling | To set up: create **Communication Services** resource in Azure portal → add **Email Communication Service** sub-resource → verify a domain or use the free Azure-managed domain (`azurecomm.net`) → copy connection string to `AZURE_COMM_CONNECTION_STRING` |

---

## 🔮 Azure AI Foundry — Conceptual Mapping & Migration Target

> **Note:** The code in this section reflects the **actual running implementation** of `LearnerProfilingAgent` when `AZURE_AI_PROJECT_CONNECTION_STRING` is set. The rest of the pipeline (StudyPlanAgent, LearningPathCuratorAgent, ProgressAgent, AssessmentAgent, CertRecommendationAgent) uses the same typed output contract and is not yet Foundry-managed — this is the **near-term roadmap item** described below.

Here is how every Foundry concept maps to our current and planned architecture:

### 1 — Agent Definitions
Each of the 8 agents is defined as an **AI Foundry Agent** with a system prompt, tool list, and output schema. The Foundry runtime manages the conversation thread and ensures agents receive only the data they are entitled to:

```python
# Example: LearnerProfilingAgent using Foundry runtime
agent = project.agents.create_agent(
    model="gpt-4o",
    name="LearnerProfiler",
    instructions=PROFILER_SYSTEM_PROMPT,
    tools=[EXAM_DOMAIN_LOOKUP_TOOL, BACKGROUND_PARSER_TOOL],
)
thread = project.agents.create_thread()
run = project.agents.create_and_process_run(
    thread_id=thread.id, agent_id=agent.id,
    additional_instructions=f"Input: {raw_input_json}"
)
profile = parse_output(run.result)
```

### 2 — Tool Calling
The `LearningPathCuratorAgent` uses **Foundry tool calling** to invoke the MS Learn catalogue lookup as a structured function — not a free-text prompt:

```python
tools = [
    {
      "type": "function",
      "function": {
        "name": "lookup_ms_learn_modules",
        "description": "Return MS Learn modules for a given exam domain and skill level",
        "parameters": {"exam_code": "string", "domain_id": "string", "skill_level": "string"}
      }
    }
]
```

### 3 — Message Threading & Memory
Foundry's **thread-per-learner** model maps directly to our `RunTrace` in SQLite — each thread preserves the full conversation between agents, enabling:
- Resume from any checkpoint (learner closes browser, returns next day)
- Complete audit trail for the Admin Dashboard
- Reproducible replays for debugging guardrail decisions

### 4 — Connected Agent Pattern (Multi-Agent)
The fan-out between `StudyPlanAgent` ∥ `LearningPathCuratorAgent` maps to Foundry's **Connected Agent** pattern where a parent (orchestrator) agent dispatches sub-agents in parallel runs on the same thread:

```python
# Foundry connected-agent dispatch (conceptual)
orchestrator.dispatch_parallel([
    SubAgentRun(agent_id=study_plan_agent_id,   input=profile),
    SubAgentRun(agent_id=learning_path_agent_id, input=profile),
])
results = orchestrator.await_all()
```

In the current implementation this is realised via `concurrent.futures.ThreadPoolExecutor` — the Foundry-native version is on the roadmap.

### 5 — Guardrails as Foundry Middleware
Foundry's **content filters** and our custom `GuardrailsPipeline` are layered: Foundry handles toxicity/CSAM at the model level, while our pipeline handles domain-specific checks (G-01..G-17) at the application level. This two-layer approach means no harmful content ever reaches the exam preparation output regardless of adversarial input.

---

## 🗺️ User Journey

```mermaid
flowchart TD
    A([Open App]) --> B{Returning user?}
    B -- No --> C[Pick Persona or Sign In]
    B -- Yes --> D[Session restored from SQLite]
    C --> E[Intake Form\nExam · Background · Hours · Email optional]
    E --> F{Input Guardrails\nG-01 to G-05}
    F -- BLOCK --> G[Error shown, pipeline stops]
    F -- PASS --> H[Parallel Agents\nStudyPlan AND LearningPath concurrently]
    D --> I
    H --> I[Tab 1 Learner Profile\nDomain radar · Experience level]
    I --> J[Tab 2 Study Plan\nGantt · Prereq gap]
    I --> K[Tab 3 Learning Path\nMS Learn modules]
    J --> L[Tab 4 Progress Check-In\nHITL Gate 1]
    L --> M{Progress Guardrails\nG-11 to G-13}
    M -- PASS --> O[Readiness Assessment\nWeighted formula]
    O --> P[Tab 5 Mock Quiz\nHITL Gate 2]
    P --> R{Score >= 70%?}
    R -- YES --> S[Tab 6 Cert Recommendation]
    R -- NO --> T[Remediation Plan loop back]
    S --> U[Admin Dashboard\nAgent traces · Guardrail audit]
    T --> H
```

---

## ⚙️ Technical Architecture

```mermaid
flowchart TD
    UI[Streamlit UI] --> RAW[RawStudentInput + email]
    RAW --> GI[Guardrails G-01..G-05]
    GI -- BLOCK --> STOP1[st.stop]
    GI -- PASS --> B0A[LearnerProfilingAgent\nmock or Azure OpenAI JSON-mode]
    B0A --> LP[LearnerProfile Pydantic]
    LP --> GPR[Guardrails G-06..G-08]
    GPR -- BLOCK --> STOP2[st.stop]
    GPR -- PASS --> FANOUT

    subgraph FANOUT[ThreadPoolExecutor max_workers=2]
        SP[StudyPlanAgent\nLargest Remainder alloc]
        LPC[LearningPathCuratorAgent\nMS Learn module map]
    end

    SP --> PLAN[StudyPlan]
    LPC --> PATH[LearningPath]
    PLAN --> GPL[Guardrails G-09..G-10]
    PATH --> GPH[Guardrail G-17 URL trust]
    GPL --> PROG[ProgressAgent\nreadiness formula]
    GPH --> PROG
    PROG --> RA[ReadinessAssessment]
    RA --> GPG[Guardrails G-11..G-13]
    GPG -- PASS --> B2[AssessmentAgent\n30-Q bank domain-weighted]
    B2 --> AR[AssessmentResult]
    AR --> GAS[Guardrails G-14..G-16]
    GAS -- PASS --> ROUTE{Score >= 70?}
    ROUTE -- YES --> B3[CertRecommendationAgent]
    ROUTE -- NO --> REM[Remediation loop]
    B3 --> CREC[CertRecommendation]
    CREC --> DB[(SQLite)]
    CREC --> TRACE[RunTrace AgentStep]
    TRACE --> ADMIN[Admin Dashboard]

    style FANOUT fill:#FFF3CD,stroke:#FFC107
```

---

## 🤖 Agent Inventory — 8 Agents

| # | Agent | Module | Input → Output | Reasoning Pattern |
|---|-------|--------|----------------|-------------------|
| 1 | **Safety Guardrails** | `guardrails.py` | Any → `GuardrailResult` | **Critic/Verifier** — 17-rule exam-agnostic middleware; BLOCK halts via st.stop() |
| 2 | **Learner Intake** | `b0_intake_agent.py` | UI form → `RawStudentInput` | **Planner** — collects background, any exam target, constraints, optional email |
| 3 | **Learner Profiler** | `b1_mock_profiler.py` | `RawStudentInput` → `LearnerProfile` | **Executor** — 40+ regex patterns; exam domain boost matrices; LLM JSON-mode in live |
| 4 | **Learning Path Curator** | `b1_1_learning_path_curator.py` | `LearnerProfile` → `LearningPath` | **Specialist** — maps weak/risk domains to MS Learn modules; skips strong domains; runs in parallel |
| 5 | **Study Plan Generator** | `b1_1_study_plan_agent.py` | `LearnerProfile` → `StudyPlan` | **Planner** — Largest Remainder week allocation; prereq gap detection; runs in parallel |
| 6 | **Progress Tracker** | `b1_2_progress_agent.py` | `ProgressSnapshot` → `ReadinessAssessment` | **Critic** — weighted readiness formula; GO/CONDITIONAL GO/NOT YET verdict |
| 7 | **Assessment Builder** | `b2_assessment_agent.py` | `LearnerProfile` → `AssessmentResult` | **Evaluator** — 30-Q bank per exam; domain-weighted sampling; per-domain score breakdown |
| 8 | **Cert Recommender** | `b3_cert_recommendation_agent.py` | `AssessmentResult` → `CertRecommendation` | **Planner** — next-cert path selection; booking checklist; remediation plan |

---

## ⚡ Concurrent Agent Execution — asyncio.gather() Pattern

Both Block 1.1 agents depend only on `LearnerProfile` — no data dependency between them — enabling true parallel fan-out.

```python
import concurrent.futures

def _run_study_plan():
    return StudyPlanAgent().run_with_raw(profile, existing_certs=_existing_certs_list)

def _run_learning_path():
    return LearningPathCuratorAgent().curate(profile)

with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
    plan_future   = executor.submit(_run_study_plan)
    path_future   = executor.submit(_run_learning_path)
    plan          = plan_future.result()
    learning_path = path_future.result()
```

**Why ThreadPoolExecutor over raw asyncio.gather():** Azure OpenAI calls are I/O-bound; threads release the GIL during HTTP wait, providing genuine parallelism. Raw `asyncio.run()` inside Streamlit triggers `RuntimeError: event loop already running` without `nest_asyncio`. `ThreadPoolExecutor` is stdlib-only and has identical network I/O latency.

---

## 🛡️ Guardrails — 17 Rules, Exam-Agnostic

| Rule(s) | Category | Level | What It Checks |
|---------|----------|-------|----------------|
| G-01..G-05 | **Input Validation** | BLOCK/WARN/INFO | Required fields; hours ∈ [1,80]; weeks ∈ [1,52]; exam code in dynamic registry; PII notice |
| G-06..G-08 | **Profile Integrity** | BLOCK/WARN | N domain profiles present; confidence ∈ [0,1]; risk IDs valid against registry |
| G-09..G-10 | **Study Plan Bounds** | BLOCK/WARN | No start_week > end_week; total hours ≤ 110% budget |
| G-11..G-13 | **Progress Validity** | BLOCK | hours_spent ≥ 0; self-ratings ∈ [1,5]; practice score ∈ [0,100] |
| G-14..G-15 | **Quiz Integrity** | WARN/BLOCK | Min 5 questions; no duplicate question IDs |
| G-16 | **Content Safety** | BLOCK | Heuristic harmful keyword filter on all free-text outputs |
| G-17 | **URL Trust / Anti-Hallucination** | BLOCK/WARN | Generated URLs must originate from learn.microsoft.com, pearsonvue.com, or aka.ms |

---

## 🤝 Responsible AI Considerations

This system is built with Microsoft's Responsible AI principles embedded in every agent transition:

| Principle | Requirement | Implementation Status | Evidence |
|-----------|-------------|----------------------|----------|
| **Guardrails** | Validate inputs and outputs to prevent harmful content | ✅ **Implemented** | 17-rule `GuardrailsPipeline` (BLOCK/WARN/INFO); G-01..G-05 validate all user inputs; G-06..G-17 validate all agent outputs before the next stage proceeds |
| **Content Filters** | Use Azure Content Safety to detect inappropriate content | ✅ **Heuristic active** / 🗺️ API roadmap | G-16: 14 harmful-keyword heuristic blocks profanity and harmful content on all free-text fields; `check_content_safety()` stub in `guardrails.py` ready for `azure-ai-contentsafety` SDK upgrade (see TODO.md §C) |
| **Bias Evaluation** | Evaluate agent responses for fairness across scenarios | ✅ **Structural fairness** / 🗺️ Formal eval roadmap | All 9 exam families use the same domain registry and scoring logic; assessment questions are drawn from exam blueprints (factual/technical, not demographic-sensitive); formal LLM bias evaluation via Foundry Evaluation is a near-term roadmap item |
| **Transparency** | Clearly indicate to users when interacting with AI | ✅ **Implemented** | Sidebar mode badge (☁️ Azure AI Foundry SDK / 🔌 Mock Mode); spinner messages name the exact tier called; `🤖 AI-generated` badges on study plans and recommendations; mock mode banner when no Azure creds; judge playbook documents all AI boundaries |
| **Human Oversight** | Include human-in-the-loop patterns for critical decisions | ✅ **Implemented** | HITL Gate 1: learner manually submits study hours + self-ratings (agents cannot auto-advance); HITL Gate 2: learner manually answers the 30-question quiz; readiness gate blocks assessment until progress threshold met |
| **Fallback & Graceful Degradation** | Prevent silent AI failures | ✅ **Implemented** | 3-tier execution strategy: Foundry SDK → Direct OpenAI → Mock; guardrail BLOCK calls `st.stop()` (never silently skipped); all agent errors surface in UI and agent trace |
| **Privacy / PII** | Protect personally identifiable information | ✅ **Implemented** | G-05 PII notice: names stored locally only, never transmitted to external APIs; G-16 PII regex (7 patterns: SSN, credit card, passport, UK NI, email, phone, IP) BLOCKS submission if detected; demo data is synthetic only; `.env` is gitignored |

### What Is NOT Yet Implemented (Honest Gaps)

| Gap | Plan |
|-----|------|
| Azure Content Safety API (live call) | Upgrade G-16 from heuristic to `azure-ai-contentsafety` SDK when `AZURE_CONTENT_SAFETY_ENDPOINT/KEY` are set; stub + env vars already in place |
| Formal LLM bias evaluation dataset | Create eval harness in Foundry Evaluation SDK with demographic parity + counterfactual tests |
| Differential privacy metrics | Track token-level PII exposure rate across sessions via Azure Monitor |

---

## 🔮 Futuristic Vision

### Near Term (3–6 months)
- **Extend Azure AI Foundry SDK to remaining agents** — `LearnerProfilingAgent` now uses `AIProjectClient` (Tier 1); next step is wrapping `StudyPlanAgent`, `LearningPathCuratorAgent`, `AssessmentAgent`, and `CertRecommendationAgent` with Foundry-managed agents for full platform observability and built-in thread memory
- **Azure AI Search integration** — replace static MS Learn lookup table with live vector search across the full ~4 000 module catalogue; semantic matching between learner profile and module descriptions
- **Email digest — upgrade from SMTP to Azure Communication Services** — the current implementation uses Python `smtplib` (works with Gmail/Outlook); the roadmap upgrade swaps this for the `azure-communication-email` SDK using a managed Azure sender domain (`DoNotReply@<guid>.azurecomm.net`); to set up today: create a **Communication Services** resource in the Azure portal, add an **Email Communication Service** sub-resource, then copy the connection string to `AZURE_COMM_CONNECTION_STRING`
- **Adaptive quiz engine** — use GPT-4o to generate novel domain-specific questions dynamically rather than sampling from a static bank; item-response theory (IRT) for adaptive difficulty

### Medium Term (6–12 months)
- **Multi-language support** — Azure OpenAI Whisper for voice-based intake; multilingual exam content via Azure AI Translator
- **Study group / cohort mode** — shared study plans for enterprise teams preparing for the same certification batch
- **Real-time practice labs** — integrate Azure sandbox environments so learners can attempt actual Azure tasks inline (e.g. deploy an Azure OpenAI endpoint as a graded exercise)
- **Exam booking assistant** — connect to Pearson VUE API to show seat availability and book directly from the recommendation tab

### Long Term (12+ months)
- **Autonomous learning loop** — agent self-improves question bank by monitoring which questions correlate most with real exam pass/fail outcomes (A/B testing with learner consent)
- **Cert path graph** — multi-hop reasoning across all 9 cert prerequisites to recommend the optimal 12-month cert roadmap given the learner's starting point
- **Enterprise LMS integration** — export study plans to LMS platforms (Cornerstone, SAP SuccessFactors) via LTI/xAPI so organisations can track team certification progress
- **Multimodal input** — accept PDF uploads (e.g. existing CV/résumé) as background context; parse with Azure Document Intelligence and pass to profiler

---

## 📦 Multi-Cert Domain Registry

```python
EXAM_DOMAIN_REGISTRY = {
    "AI-102": [...],   # Azure AI Engineer Associate
    "AI-900": [...],   # Azure AI Fundamentals
    "AZ-204": [...],   # Azure Developer Associate
    "AZ-305": [...],   # Azure Solutions Architect Expert
    "AZ-400": [...],   # DevOps Engineer Expert
    "DP-100": [...],   # Azure Data Scientist Associate
    "DP-203": [...],   # Azure Data Engineer Associate
    "SC-100": [...],   # Cybersecurity Architect Expert
    "MS-102": [...],   # Microsoft 365 Administrator Expert
}

# All agents use dynamic lookup — zero code change to support a new cert:
domains = get_exam_domains("DP-100")
```

---

## 🧠 Reasoning Patterns & Best Practices

As recommended in the [Agents League starter kit](https://github.com/microsoft/agentsleague/tree/main/starter-kits/2-reasoning-agents#-reasoning-patterns--best-practices), this project implements all four core reasoning patterns:

| Pattern | Starter Kit Requirement | Where in This System |
|---------|------------------------|---------------------|
| **Planner–Executor** | Separate agents for planning and execution | `IntakeAgent` plans (collects goals) → `LearnerProfilingAgent` executes (extracts typed `LearnerProfile`) → `StudyPlanAgent` plans the schedule |
| **Critic / Verifier** | Agent that reviews outputs and validates reasoning | `GuardrailsPipeline` (17 rules) validates every agent output before the next stage proceeds; `ProgressAgent` critiques learner readiness before unlocking assessment |
| **Self-reflection & Iteration** | Agents reflect on intermediate results and refine | Score < 70% → remediation loop: `StudyPlanAgent` re-runs with updated weak-domain profile; HITL gate captures real learner data before each iteration |
| **Role-based specialisation** | Clear, bounded responsibilities per agent | `StudyPlanAgent` (temporal scheduling only) ≠ `LearningPathCuratorAgent` (content discovery only) ≠ `AssessmentAgent` (evaluation only) ≠ `CertRecommendationAgent` (booking + next-cert path only) |

### Additional Patterns

| Pattern | Where |
|---------|-------|
| **Human-in-the-Loop (HITL)** | Gate 1: learner submits study hours + self-ratings; Gate 2: learner answers 30-question quiz — agents produce inputs and interpret outputs, human provides the data |
| **Conditional Routing** | `score ≥ 70%` → `CertRecommendationAgent`; `50–70%` → targeted review; `< 50%` → full remediation loop |
| **Typed Handoff Contracts** | All agents exchange Pydantic `BaseModel` or `@dataclass` — never raw strings; validated at every boundary by `GuardrailsPipeline` |
| **Concurrent Fan-out** | `StudyPlanAgent` ∥ `LearningPathCuratorAgent` via `ThreadPoolExecutor` — independent agents with same `LearnerProfile` input, different outputs |

### Best Practices Applied

| Starter Kit Best Practice | How This System Addresses It |
|--------------------------|-----------------------------|
| Use telemetry, logs, and visual workflows | `AgentStep`/`RunTrace` observability structs capture per-agent latency, token count, and I/O summary; Admin Dashboard surfaces guardrail violations, agent traces, and student roster |
| Foundry built-in monitoring (roadmap) | `agent_trace.py` data model is directly portable to Azure AI Foundry telemetry schema when migrating to Foundry SDK |
| Apply evaluation strategies | 25 pytest tests (`test_guardrails.py`, `test_config.py`, `test_agents.py`); mock mode enables reproducible, deterministic testing without API calls |
| Build with Responsible AI principles | `GuardrailsPipeline` G-16 (content safety), G-17 (URL trust / anti-hallucination), G-01..G-05 (input validation and PII notice); `.env` never committed; demo data only in public repo |
| Leverage AI-assisted development | GitHub Copilot used throughout for code generation, refactoring, and test scaffolding |

---

## � Microsoft Foundry Best Practices — Implementation Status

Explicit mapping of each [Foundry best practice from the starter kit](https://github.com/microsoft/agentsleague/tree/main/starter-kits/2-reasoning-agents#-best-practices-for-building-with-microsoft-foundry) to concrete implementation evidence in this codebase.

| # | Foundry Best Practice | Status | Implementation Evidence |
|---|----------------------|--------|------------------------|
| 1 | **Use telemetry, logs, and visual workflows in Foundry** to understand how agents reason and collaborate | ✅ **Implemented** | `agent_trace.py` — `AgentStep` struct captures: `agent_id`, `agent_name`, `start_ms`, `duration_ms`, `status`, `input_summary`, `output_summary`, `decisions[]`, `warnings[]`; `RunTrace` aggregates all steps per session with `run_id`, `student_name`, `exam_target`, `mode`, `total_ms`; Admin Dashboard renders the full per-agent reasoning trace (expandable cards); Azure AI Foundry portal **automatically** logs all Tier 1 `create_and_process_run()` calls with latency + token counts |
| 2 | **Foundry Control Plane** — built-in monitoring tools to track agent interactions and performance | ✅ **Partially active** | When `AZURE_AI_PROJECT_CONNECTION_STRING` is set, every `LearnerProfilingAgent` run appears in the Foundry portal **Tracing** view (request/response, latency, token usage) — recorded automatically by `AIProjectClient`; remaining agents are traced locally via `RunTrace` / Admin Dashboard; full Control Plane coverage for all agents is sprint task T-06 |
| 3 | **Apply evaluation strategies** — test cases, scoring rubrics, or HITL reviews to continuously improve agent behaviour | ✅ **Implemented** | 25 pytest tests (`test_guardrails.py`, `test_config.py`, `test_agents.py`); `GuardrailsPipeline` is a 17-rule scoring rubric (BLOCK/WARN/INFO with per-rule codes G-01..G-17); HITL Gate 1 (study hours + self-ratings) and Gate 2 (30-question quiz) are structured human reviews embedded in the pipeline; remediation loop re-runs planning agents on low-score outcomes |
| 4 | **Evaluate generative AI models and applications** using Microsoft Foundry built-in features | ✅ **Active (portal)** / 🗺️ SDK roadmap | Foundry portal evaluation is available today for all Tier 1 `LearnerProfilingAgent` runs; `azure-ai-evaluation` SDK integration (programmatic metrics: coherence, groundedness, relevance) is sprint task T-09 — `AgentStep`/`RunTrace` data model is already schema-compatible |
| 5 | **Evaluate your AI agents with the Microsoft Foundry SDK** (`azure-ai-evaluation`) | 🗺️ **Roadmap — T-09** | `azure-ai-evaluation` package not yet wired; `AgentStep`/`RunTrace` structs are schema-compatible with Foundry Evaluation input format; see `docs/TODO.md` sprint task T-09 |
| 6 | **Build with Responsible AI principles** — at both application and data layers | ✅ **Comprehensively implemented** | **Application layer:** 17-rule `GuardrailsPipeline` (input G-01..G-05, profile G-06..G-08, study plan G-09..G-10, progress G-11..G-13, quiz G-14..G-15, content G-16, URL-trust G-17); **Foundry model layer:** Foundry's content filters applied automatically to all Tier 1 managed runs at the model endpoint; **Data layer:** `.env` gitignored, synthetic demo personas only, no PII in repo — see `## 🤝 Responsible AI Considerations` for the full 7-principle breakdown |
| 7 | **Responsible AI in Microsoft Foundry** — transparency, guardrails, human oversight | ✅ **Implemented** | Sidebar mode badge clearly labels the active AI tier (☁️ Azure AI Foundry SDK / ☁️ Live Azure OpenAI / 🔌 Mock Mode); spinner messages name the exact API called; `🤖 AI-generated` disclaimers on study plans and recommendations; 3-tier graceful degradation (Foundry → OpenAI → Mock) ensures no silent failures; `GuardrailsPipeline` BLOCK halts via `st.stop()` with a user-visible error message |

### Honest Gaps

| Gap | Sprint Task | Notes |
|-----|-------------|-------|
| `azure-ai-evaluation` SDK not yet wired | T-09 | Schema-compatible `AgentStep` data ready; needs `pip install azure-ai-evaluation` + eval harness scripting |
| Foundry SDK limited to `LearnerProfilingAgent` only | T-06 | Remaining 4 agents still use Tier 2 (direct OpenAI) or Tier 3 (mock) |
| Azure Content Safety API not called (heuristic only for G-16) | T-07 | `check_content_safety()` stub in `guardrails.py`; env vars present in `.env.example` |
| Foundry Evaluation dataset for bias testing | B-01 | Requires labelled test set across all 9 cert exam families |

---

## �🚀 Quick Start

```bash
git clone https://github.com/athiq-ahmed/agentsleague.git
cd agentsleague
python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate      # macOS/Linux
pip install -r requirements.txt
streamlit run streamlit_app.py  # opens http://localhost:8501
```

### Demo Credentials

| Role | Name | Credential | Journey |
|------|------|-----------|---------|
| New Learner | Alex Chen | PIN: `1234` | AI-102 from scratch |
| Returning Learner | Priyanka Sharma | PIN: `1234` | DP-100 with profile loaded |
| Admin | `admin` | Password: `agents2026` | Full trace + guardrail audit |

### Azure OpenAI (optional — enables live mode)
```ini
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com
AZURE_OPENAI_API_KEY=<key>
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-12-01-preview
```

### Email digest (optional — standard SMTP, any provider)
The progress agent sends a study-digest email via Python's built-in `smtplib`. Works with Gmail, Outlook, or any SMTP relay:
```ini
SMTP_HOST=smtp.gmail.com       # or smtp.office365.com, smtp.sendgrid.net, etc.
SMTP_PORT=587
SMTP_USER=your.account@gmail.com
SMTP_PASS=<app-password>       # Gmail: Settings → Security → App Passwords
SMTP_FROM=CertPrep <your.account@gmail.com>
```
> **Note:** No Azure subscription needed for email. If these variables are absent the progress agent silently skips sending — the rest of the app is unaffected.
> 
> **Azure Communication Services (roadmap):** production upgrade to managed sender domain (`DoNotReply@<guid>.azurecomm.net`). Set up: Azure portal → **Communication Services** → add **Email Communication Service** sub-resource → verify/use the free Azure-managed domain → copy connection string to `AZURE_COMM_CONNECTION_STRING`.

---

## 📁 Project Structure

```
agentsleague/
├── streamlit_app.py                      # Orchestrator + full 8-tab UI (main entry point)
├── .env                                  # ⚠️ NOT committed — real secrets here (gitignored)
├── .env.example                          # ✅ Committed template — copy to .env, fill in values
├── requirements.txt                      # pip dependencies
│
├── pages/
│   └── 1_Admin_Dashboard.py             # Agent audit dashboard + per-agent guardrail log
│
├── src/
│   └── cert_prep/
│       ├── __init__.py
│       ├── models.py                     # Data contracts + EXAM_DOMAIN_REGISTRY (9 certs)
│       ├── config.py                     # Settings dataclass: OpenAI, Foundry, ContentSafety,
│       │                                 #   CommServices, MCP, App — auto live-mode detection
│       ├── guardrails.py                 # GuardrailsPipeline — 17 rules with real PII patterns
│       ├── agent_trace.py                # AgentStep / RunTrace observability structs
│       ├── database.py                   # SQLite persistence (learner profiles + traces)
│       ├── b0_intake_agent.py            # Intake + LearnerProfilingAgent (live Azure OpenAI)
│       ├── b1_mock_profiler.py           # Rule-based profiler (zero-credential mock mode)
│       ├── b1_1_study_plan_agent.py      # Gantt study plan generator (parallel fan-out)
│       ├── b1_1_learning_path_curator.py # MS Learn module curator (parallel fan-out)
│       ├── b1_2_progress_agent.py        # Readiness tracker + email digest
│       ├── b2_assessment_agent.py        # Quiz builder + scorer
│       └── b3_cert_recommendation_agent.py  # Next-cert path recommender
│
├── tests/                                # Smoke test suite (pytest)
│   ├── __init__.py
│   ├── test_guardrails.py               # 14 tests — G-16 PII patterns + harmful blocker
│   ├── test_config.py                   # 7 tests — settings loading, placeholder detection
│   └── test_agents.py                   # 4 tests — mock profiler outputs
│
├── docs/
│   ├── architecture.md                  # System design + agent pipeline diagrams
│   ├── user_flow.md                     # All 8 user journey scenarios (S1–S8 incl. PII)
│   ├── judge_playbook.md               # Hackathon judging Q&A
│   ├── TODO.md                          # Task tracker (completed + pending items)
│   └── CertPrep_MultiAgent_Architecture.drawio  # Architecture diagram source
│
└── archive/                             # Old planning files (not in production path)
```

### Why two `.env` files?

| File | Committed? | Purpose |
|------|-----------|---------|
| `.env` | ❌ Never (gitignored) | Your real secrets — Azure keys, endpoints, passwords |
| `.env.example` | ✅ Yes | Safe template listing every required variable with placeholders — copy to `.env` and fill in |

**To go Live:** copy `.env.example` → `.env`, fill real Azure values, restart app. The toggle switches automatically.

---

## 🏆 Submission Requirements Checklist

Complete alignment with the [Battle #2 Submission Requirements](https://github.com/microsoft/agentsleague/tree/main/starter-kits/2-reasoning-agents#-submission-requirements). Every mandatory criterion is met; all optional/highly-valued criteria are also addressed.

### Mandatory Requirements

| # | Requirement | Status | Evidence |
|---|-------------|--------|----------|
| 1 | **Multi-agent system** aligned with the challenge scenario (student preparation for Microsoft certification exams) | ✅ **Met** | 8 specialised reasoning agents: `IntakeAgent` → `LearnerProfilingAgent` → `StudyPlanAgent` ∥ `LearningPathCuratorAgent` → `ProgressAgent` → `AssessmentAgent` → `CertRecommendationAgent`; supports 9 exam families (AI-102, DP-100, AZ-204, AZ-305, AZ-400, SC-100, AI-900, DP-203, MS-102) |
| 2 | **Use Microsoft Foundry (UI or SDK)** and/or the Microsoft Agent Framework for agent development and orchestration | ✅ **Met** | `azure-ai-projects` SDK (`AIProjectClient.from_connection_string()`) is live for `LearnerProfilingAgent` — creates managed agent + thread, calls `create_and_process_run()`, deletes ephemeral agent after response; Tier 2 fallback to direct Azure OpenAI; remaining agents use Foundry-compatible typed contracts |
| 3 | **Demonstrate reasoning and multi-step decision-making** across agents | ✅ **Met** | 8-agent sequential + parallel pipeline; Planner–Executor pattern (Intake → Profiler → Planner); Critic/Verifier pattern (GuardrailsPipeline at every agent boundary); conditional routing (`score ≥ 70%` → CertRecommender, `50–70%` → targeted review, `< 50%` → remediation loop); self-reflection iteration (re-plan on score drop); HITL gates |
| 4 | **Integrate with external tools, APIs, and/or MCP servers** to meaningfully extend agent capabilities | ✅ **Met** | Azure OpenAI GPT-4o (LLM backbone); Azure AI Foundry Agent Service SDK (managed agent execution); SQLite persistence (cross-session learner profiles); SMTP email digest (progress notifications); MS Learn module catalogue (9-cert static registry; live MCP `/ms-learn` server integration via `MCP_MSLEARN_URL` is active roadmap — placeholder wired) |
| 5 | **Be demoable** (live or recorded) and clearly explain the agent interactions | ✅ **Met** | Live at [agentsleague.streamlit.app](https://agentsleague.streamlit.app) (Streamlit Cloud); Admin Dashboard shows per-agent reasoning trace, input/output, guardrail violations, latency; mock mode runs zero-credential locally; `docs/judge_playbook.md` guides live demo walkthrough |
| 6 | **Clear documentation** describing: agent roles and responsibilities, reasoning flow and orchestration logic, tools/API/MCP integrations | ✅ **Met** | `README.md` (this file — full architecture, agent table, reasoning patterns, tool integrations, Foundry SDK integration); `docs/architecture.md` (sequence diagrams, agent contracts, compliance map); `docs/judge_playbook.md` (demo script, scenario walkthroughs, guardrail evidence); `docs/user_flow.md` (full user journey with PII edge cases) |

### Optional But Highly Valued

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 7 | **Use of evaluations, telemetry, or monitoring** | ✅ **Implemented** | `AgentStep` / `RunTrace` structs capture per-agent latency, token count, I/O snapshot, and guardrail violations; Admin Dashboard surfaces full trace per student session; 25 pytest tests in `tests/`; Azure AI Foundry portal telemetry active for Tier 1 Foundry-managed runs |
| 8 | **Advanced reasoning patterns** (planner–executor, critics, reflection loops) | ✅ **All 4 implemented** | Planner–Executor (Intake→Profiler→StudyPlan); Critic/Verifier (GuardrailsPipeline 17 rules); Self-reflection + Iteration (remediation loop on low score); Role-based specialisation (bounded single-responsibility agents); + HITL gates, conditional routing, typed handoff contracts, concurrent fan-out |
| 9 | **Responsible AI considerations** (guardrails, validation, fallbacks) | ✅ **Comprehensively implemented** | 17-rule `GuardrailsPipeline` (BLOCK/WARN/INFO); G-16 content safety heuristic (14 harmful keywords + PII regex); G-17 URL trust/anti-hallucination; G-05 PII notice; 3-tier graceful degradation (Foundry → OpenAI → Mock); HITL human oversight gates; transparency badges (mode badge, spinner labels, AI disclaimers); `.env` gitignored; synthetic demo data only — see `## 🤝 Responsible AI Considerations` section above for full breakdown |

### Self-Improvement & Workflow Governance

This project enforces a **plan-first, verify-before-done** development discipline:

| Workflow Principle | Implementation |
|-------------------|----------------|
| **Plan Node Default** | Any task with > 3 implementation steps must be written to `docs/TODO.md` before coding starts |
| **Self-Improvement Loop** | After every correction or AI-assisted change, lessons are recorded in `docs/lessons.md` — compounding the mistake rate drop over time |
| **Verification Before Done** | No task is marked `✅` without: syntax check (`py_compile`), behaviour diff (manual or `pytest`), and git diff review |
| **Autonomous Bug Fixing** | CI test failures / error logs are addressed root-cause-first — no patch-over-patch workarounds |
| **Strict Task Management** | `docs/TODO.md` uses checkable items; in-progress items are limited to one at a time; completed items immediately ticked |

See [`docs/TODO.md`](docs/TODO.md) for current sprint tasks and [`docs/lessons.md`](docs/lessons.md) for the cumulative lessons log.

---

## ✅ Starter Kit Compliance Checklist

Alignment with the [Starter Kit README](https://github.com/microsoft/agentsleague/tree/main/starter-kits/2-reasoning-agents):

| Starter Kit Item | Status | Notes |
|-----------------|--------|-------|
| Multi-agent reasoning system | ✅ | 8 agents, 4 reasoning patterns |
| `azure-ai-projects` SDK (`AIProjectClient`) active | ✅ | `LearnerProfilingAgent` Tier 1 — Foundry managed agent + thread |
| Foundry-compatible typed agent contracts | ✅ | All agents exchange Pydantic `BaseModel` / `@dataclass` |
| Human-in-the-Loop gates | ✅ | 2 explicit HITL gates in pipeline |
| Content safety + input validation | ✅ | G-01..G-17 guardrails pipeline |
| Evaluation / telemetry | ✅ | `AgentStep`/`RunTrace` + 25 pytest tests |
| `.gitignore` per starter kit guidelines | ✅ | `.env`, `.azure/`, `.secrets/` excluded |
| GitHub repository with full documentation | ✅ | [athiq-ahmed/agentsleague](https://github.com/athiq-ahmed/agentsleague) |

---

## 🔒 Security & Disclaimer

> ⚠️ **This is a public repository accessible worldwide.** Before contributing or forking, please read the [Agents League Disclaimer](https://github.com/microsoft/agentsleague/blob/DISCLAIMER.md).

### What This Repository Does NOT Contain

| Prohibited Content | Status |
|-------------------|--------|
| ❌ Azure API keys, connection strings, or credentials | `.env` is gitignored; `.env.example` contains only placeholders |
| ❌ Customer data or personally identifiable information (PII) | All demo personas (Alex Chen, Priyanka Sharma) use synthetic data only |
| ❌ Confidential or proprietary company information | None |
| ❌ Internal engineering projects not approved for open source | None |
| ❌ Pre-release product information under NDA | None |
| ❌ Trade secrets or proprietary algorithms | Largest Remainder allocation is a published parliamentary apportionment method |

### Azure Security Best Practices Applied

```ini
# ✅ .gitignore includes:
.env
.env.*
.azure/
**/.secrets/
*.pem
*.key
```

- ✅ **Credentials in environment variables only** — never in committed code
- ✅ **`.env.example` committed** — safe template with placeholder values only
- ✅ **Demo data only** — no real customer data or production datasets in the repository
- ✅ **PIN hashed (SHA-256)** — demo PINs are hashed before SQLite storage
- ✅ **Production path** uses Azure Key Vault + Managed Identity (documented in `docs/architecture.md`)

### Responsible AI in This System

| Principle | Implementation |
|-----------|---------------|
| **Validate inputs and outputs** | 17-rule `GuardrailsPipeline` — BLOCK halts pipeline; WARN is logged and surfaced in Admin Dashboard |
| **Content filters** | G-16 heuristic harmful-keyword filter on all free-text fields; G-17 URL trust allowlist prevents hallucinated links |
| **Transparency** | Every response includes agent source label and mock/live mode indicator |
| **Human oversight** | Two HITL gates interrupt the pipeline — humans provide real progress data before agents advance |
| **Fairness** | Exam domains drawn from official Microsoft weighting tables — not model-generated |

Learn more: [Responsible AI in Microsoft Foundry](https://learn.microsoft.com/azure/ai-foundry/responsible-use-of-ai-overview)

### Legal & Licensing

- All content is original work created for this competition
- Submitted under the repository's [MIT License](https://github.com/microsoft/agentsleague/blob/LICENSE)
- Complies with the [Code of Conduct](https://github.com/microsoft/agentsleague/blob/CODE_OF_CONDUCT.md)
- Demo personas use entirely synthetic / fictional data

---

## 📄 License

Created for **Microsoft Agents League** — Battle #2: Reasoning Agents. Educational and demonstration purposes.
