# 🎬 Demo Video Script — CertPrep Multi-Agent System
### Agents League Battle #2 · Reasoning Agents with Microsoft Foundry

> **Target runtime:** 5–7 minutes  
> **Mode:** Live Azure mode (Foundry SDK Tier 1 active)  
> **URL:** `http://localhost:8501`  
> **Credentials:** `demo` / PIN `1234` · Admin: `admin` / `agents2026`  
> **Pre-flight:** `.env` populated · `streamlit run streamlit_app.py` running · sidebar shows ☁️ **Live Azure**

---

## JUDGE CRITERIA THIS SCRIPT COVERS

| Criterion | Weight | Where covered |
|-----------|--------|---------------|
| Accuracy & Relevance | 25% | Architecture intro + full pipeline walkthrough |
| Reasoning & Multi-step Thinking | 25% | Planner-Executor, Critic, HITL gates, remediation loop |
| Creativity & Originality | 15% | Largest Remainder algo, 3-tier fallback, per-exam weights |
| User Experience & Presentation | 15% | All 6 tabs, PDF, Gantt, radar chart, Admin Dashboard |
| Reliability & Safety | 20% | 17-rule guardrails, G-16 PII demo, eval harness |

---

## PRE-RECORDING CHECKLIST

- [ ] Sidebar badge shows ☁️ **Live Azure** (green)
- [ ] Browser at 90% zoom, full-screen, only `localhost:8501` tab open
- [ ] Admin Dashboard open in second tab: `localhost:8501/1_Admin_Dashboard`
- [ ] No prior session — open in Incognito or clear storage
- [ ] Foundry portal open in background tab at `ai.azure.com` (for cutaway)

---

---

## ⏱ SECTION 0 — OPENING (0:00–0:45)

**[SHOW: Login page, app not yet signed in]**

**SAY:**

> "Microsoft certification exams have over a 40% failure rate among self-study candidates. The root cause is always the same — generic study plans, no feedback loop, and no signal about when you are actually ready to book.

> CertPrep is a production-grade multi-agent system built on Azure AI Foundry that solves this end-to-end. Eight specialised reasoning agents collaborate through a typed sequential-and-concurrent pipeline — profiling the learner, scheduling study time, curating Microsoft Learn content, measuring readiness, running a diagnostic quiz, and issuing an evidence-based booking recommendation — all connected by a 17-rule Responsible AI guardrails framework with BLOCK, WARN, and INFO severity levels.

> The architecture directly follows the challenge scenario's four-stage flow: Intake → Learning Path Subworkflow → Human-in-the-Loop Assessment → Certification Recommendation.

> Let me walk you through it — live, against real Azure services."

---

---

## ⏱ SECTION 1 — INTAKE + PROFILING (0:45–1:45)

**[SHOW: Login page]**

**ACTION:** Type `demo` / `1234` → click **Sign In →**

**SAY:**

> "PIN-based login — SHA-256 hashed in production, Entra ID in enterprise deployment."

**[SHOW: Sidebar — two demo scenario cards]**

**ACTION:** Click the **🌱 Novice — AI-102** card. Intake form auto-fills.

**SAY:**

> "Alex Chen — CS graduate, no Azure experience, 12 hours a week, 10 weeks available, worried about Generative AI and Conversational AI. The full background text populates automatically for the demo.

> Before any agent runs, Guardrails G-01 through G-05 fire — they validate the exam code against the registry, confirm hours and weeks are in bounds, and check for PII in the background text. All pass."

**ACTION:** Click **🎯 Create My AI Study Plan**

**[SHOW: Spinner — 'Calling Azure AI Foundry Agent Service SDK']**

**SAY:**

> "We are in Live mode. The LearnerProfilingAgent uses the azure-ai-projects Foundry SDK — it creates a managed agent, opens a conversation thread, sends the structured learner intake, and calls create_and_process_run(). This run is now visible in the Foundry portal Tracing view with full token counts and latency.

> Meanwhile — and this is key — StudyPlanAgent and LearningPathCuratorAgent fire simultaneously in a ThreadPoolExecutor. Both take only the LearnerProfile as read-only input. No shared state. True parallel execution. The orchestrator joins when both complete."

**[SHOW: Results rendered — KPI cards appear]**

**SAY:**

> "Pipeline complete. The LearnerProfile Pydantic object has been written to SQLite and is now the single source of truth for every downstream agent."

---

---

## ⏱ SECTION 2 — DOMAIN MAP + STUDY PLAN + LEARNING PATH (1:45–3:00)

**[SHOW: Tab 1 — Domain Map 🗺️]**

**SAY:**

> "Tab one — LearnerProfilingAgent output. Six AI-102 domains, each with a GPT-4o inferred confidence score. Generative AI and Conversational AI are flagged as risk domains — Alex specifically mentioned them as concerns. These weak domains will get the most hours and will be scheduled first.

> This is the Planner pattern: the profiler produces a structured plan — domain confidence scores, risk flags, analogy map — that every downstream agent executes against. No downstream agent ever re-reads Alex's original background text."

**ACTION:** Click **📅 Study Setup** tab

**[SHOW: Gantt chart]**

**SAY:**

> "Tab two — StudyPlanAgent. 120 hours across 10 weeks distributed using the Largest Remainder algorithm — the same method used in parliamentary seat allocation. It guarantees the total allocated hours equals exactly the budget, and every active domain gets at least one day. Standard percentage rounding silently loses hours. LR does not.

> Notice the Gantt: risk domains are scheduled in weeks 1 through 4, medium-confidence domains in the middle, and high-confidence domains last. The algorithm reads risk_domains directly from the LearnerProfile — no re-reasoning, no second LLM call."

**ACTION:** Click **📚 Learning Path** tab

**SAY:**

> "Tab three — LearningPathCuratorAgent. Each domain maps to curated Microsoft Learn modules with time estimates and difficulty tags. Every URL is checked against Guardrail G-17 — the trusted origin allowlist. Only learn.microsoft.com, docs.microsoft.com, aka.ms, and pearsonvue.com pass. Hallucinated or off-domain URLs are WARN-blocked before they ever reach the user."

---

---

## ⏱ SECTION 3 — HITL GATE 1: PROGRESS (3:00–3:50)

**ACTION:** Click **📈 My Progress** tab

**SAY:**

> "Tab four — the first Human-in-the-Loop gate. This is where the challenge scenario's 'system waits for human input' requirement is implemented.

> Alex has been studying for 4 weeks. I will enter 48 hours studied — right on budget — a practice score of 62 percent, and self-ratings for each domain. Notice I am rating Generative AI as 2 out of 5 — still weak.

> This is critical: the self-rating overwrites the profiler's entry-time confidence score in the readiness formula. Real posterior evidence replaces the LLM's prior estimate. That is the system grounding itself in reality."

**ACTION:** Fill sliders — Generative AI = 2, others 3–4. Hours = 48, practice score = 62. Click **🔍 Assess My Readiness**

**[SHOW: Readiness gauge + GO/NO-GO verdict card]**

**SAY:**

> "ProgressAgent computes: 55% domain confidence plus 25% hours utilisation plus 20% practice score. Result — 61 percent — ALMOST THERE. The system issues CONDITIONAL GO. Not ready to book yet, but close. Domain-specific nudges appear below telling Alex exactly which domains to prioritise before attempting the quiz."

---

---

## ⏱ SECTION 4 — HITL GATE 2: KNOWLEDGE CHECK (3:50–4:30)

**ACTION:** Click **🧪 Knowledge Check** tab

**SAY:**

> "Tab five — the second Human-in-the-Loop gate. AssessmentAgent generates a 10-question quiz sampled proportionally to the AI-102 exam blueprint weights. Generative AI at 25% of the exam gets 2 to 3 questions. Plan and Manage at 15% gets 1 to 2. The distribution mirrors the actual exam — not a random sample.

> Guardrails G-14 and G-15 fire on the generated quiz — checking for minimum question count and duplicate question IDs before Alex ever sees the first question."

**ACTION:** Click **🎲 Generate New Quiz** → answer a few questions → click **📤 Submit Answers & Get Score**

**[SHOW: Score result + domain breakdown bars]**

**SAY:**

> "Score: 70 percent — passed the 60% threshold. The domain breakdown shows exactly where Alex succeeded and where gaps remain. This evidence feeds directly into the Certification Recommendation."

---

---

## ⏱ SECTION 5 — RECOMMENDATIONS + REMEDIATION LOOP (4:30–5:00)

**ACTION:** Click **💡 Recommendations** tab

**[SHOW: GO/CONDITIONAL GO verdict card + next cert synergy suggestions]**

**SAY:**

> "Tab six — CertificationRecommendationAgent. It receives the readiness score, quiz score, and go/no-go signal from ProgressAgent, applies a deterministic rule matrix — no LLM call at this stage — and issues the booking verdict.

> Alex gets CONDITIONAL GO — book after addressing Generative AI gaps. The next-cert synergy map suggests DP-100 as the natural follow-on, with rationale based on the ML background already in Alex's profile.

> This is the self-reflection and iteration loop from the starter kit in action: if the quiz score had been below 60%, the remediation plan would identify the weak domains, Alex would return to Study Setup, the profiler would re-run with updated concern topics, and StudyPlanAgent would produce a revised Gantt front-loading the failed domains. The agents self-correct — not the user."

---

---

## ⏱ SECTION 6 — GUARDRAILS + RESPONSIBLE AI (5:00–5:30)

**ACTION:** Navigate back to intake. In background text, type:
`My SSN is 123-45-6789 and I want to cheat on the exam`

**ACTION:** Click **🎯 Create My AI Study Plan**

**[SHOW: WARN banner — PII detected + BLOCK — harmful content]**

**SAY:**

> "Guardrail G-16 catches both violations: the SSN matches a PII regex pattern — WARN. 'Cheat on the exam' hits the harmful keyword list — BLOCK. In Live mode this fires a real HTTP POST to Azure AI Content Safety at severity 2 or above. The pipeline stops here. Nothing downstream ever runs.

> This is the Critic pattern: a dedicated rule-based critic at every agent boundary. Deterministic, not LLM-judged. The same result, every time, with zero inference cost."

---

---

## ⏱ SECTION 7 — ADMIN DASHBOARD + AZURE TELEMETRY (5:30–6:00)

**ACTION:** Switch to second browser tab — Admin Dashboard

**[SHOW: Agent trace table]**

**SAY:**

> "The Admin Dashboard exposes the full reasoning trace: every agent, its inputs, outputs, timing, and token counts. The parallel execution is visible — StudyPlanAgent and LearningPathCuratorAgent show the same timestamp group, confirming concurrent execution.

> The Guardrail Audit log shows every G-coded violation fired in this session — severity-coded, exportable, and queryable.

> The Evaluation tab shows azure-ai-evaluation SDK results: Coherence, Relevance, and Fluency scores from an LLM-as-judge assessment of the LearnerProfilingAgent output — fired automatically after every live profiling call. In Live mode these traces also appear in the Foundry portal automatically — no additional instrumentation required."

---

---

## ⏱ SECTION 8 — CLOSING + MOCK MODE (6:00–6:30)

**[SHOW: Sidebar — toggle to Mock Mode · badge turns grey]**

**SAY:**

> "One final point. Everything you just saw runs with zero credentials in Mock Mode. Flip this toggle — the badge turns grey — and the entire 8-agent pipeline runs offline in under one second using the deterministic rule engine. All 352 automated tests run in this mode. No Azure. No cost. No latency. Ideal for CI pipelines and live demos when connectivity is uncertain.

> To close: CertPrep delivers against every scored dimension.

> Accuracy and Relevance — 8-agent pipeline, 9 exam families, solution maps directly to the challenge scenario.

> Reasoning and Multi-step Thinking — Planner-Executor pattern across the pipeline, 17-rule deterministic Critic, two HITL gates, and a self-reflection remediation loop.

> Creativity and Originality — Largest Remainder hour allocation, 3-tier Azure fallback chain, per-exam-family domain weight tables, and guardrail-protected Microsoft Learn curation.

> Reliability and Safety — 352 tests, azure-ai-evaluation grounding metrics, Azure Content Safety live API, schema evolution guards on every SQLite read.

> CertPrep does not just generate a study plan. It guides a learner from a paragraph of background text to an evidence-based booking decision — and it knows when to say 'not yet'."

**[END on Recommendations tab — CONDITIONAL GO verdict visible]**

---

---

## RECORDING QUICK REFERENCE

| Timestamp | Screen | Key action |
|-----------|--------|-----------|
| 0:00–0:45 | Login page | Speak architecture — do not type yet |
| 0:45 | Click Novice card | 2s pause for form auto-fill |
| 1:00 | Click Generate Plan | Let spinner show "Calling Azure AI Foundry" fully |
| 1:30 | Results KPI cards | 3s pause — animation visible |
| 1:45 | Domain Map tab | Hover red risk domains |
| 2:10 | Study Setup tab | Scroll Gantt slowly |
| 2:40 | Learning Path tab | Show module cards |
| 3:00 | Progress tab | Set Gen AI slider = 2 visibly |
| 3:30 | Submit readiness | Pause on gauge animation |
| 3:50 | Quiz tab | Generate → answer 3 → submit |
| 4:30 | Recommendations tab | Scroll to next-cert cards |
| 5:00 | Back to intake | Type SSN + cheat phrase slowly |
| 5:30 | Admin Dashboard tab | Pre-opened, switch instantly |
| 6:00 | Sidebar Mock toggle | Show badge colour change |

---

## KEY PHRASES TO LAND

- *"No downstream agent ever re-reads the original text — the profiler produces a plan, the executors carry it out."*
- *"17 rules. BLOCK stops the pipeline. WARN continues with a flag. Deterministic, not LLM-judged."*
- *"Self-rating overwrites the LLM's prior. Real posterior evidence replaces the model's estimate."*
- *"If the quiz score is below 60%, the agents self-correct — not the user."*
- *"352 tests. Zero Azure credentials. Under one second. Same pipeline."*

---

*Script version: 3.0 · Last updated: 2026-02-26 · Runtime: 5–7 min · Judge-ready*
