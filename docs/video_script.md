# Video Script — Certification Prep Multi-Agent System
### End-to-End Demo Walkthrough

> **Audience:** Technical viewers, AI engineers, product leads  
> **Runtime estimate:** 18–22 minutes (Mock + Live segments)  
> **App URL (local):** http://localhost:8501  
> **Pre-requisites (Mock):** `streamlit run streamlit_app.py` — no credentials needed  
> **Pre-requisites (Live):** `.env` must have `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT` set. Optionally `AZURE_AI_PROJECT_CONNECTION_STRING` for Tier 1 Foundry mode.

---

## BEFORE YOU HIT RECORD

**Browser setup**
- Chrome full-screen, 1920×1080 (or 1440×900 scaled)
- Zoom browser to 90% so all tabs are visible without scrolling
- Close other browser tabs — the address bar should show `localhost:8501`
- Keep a second tab open with `localhost:8501/1_Admin_Dashboard` for the admin section

**App setup — Mock Mode segment (record first)**
- Mode badge in sidebar should show 🧪 **Mock Mode**
- No Azure credentials needed — fully offline, deterministic, identical output every run
- No existing session — open in Incognito or clear storage: `Ctrl+Shift+Delete`
- Have the test credentials ready: `demo` / PIN `1234` and `admin` / password `agents2026`

**App setup — Live Mode segment (record second)**
- Ensure `.env` is populated with Azure credentials before starting
- Azure services that activate in Live mode:
  - **Azure AI Foundry** (Tier 1) — `AZURE_AI_PROJECT_CONNECTION_STRING` — richest LLM profiling
  - **Azure OpenAI GPT-4o** (Tier 2) — `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_API_KEY` — fallback LLM  
  - **Azure AI Content Safety** — `AZURE_CONTENT_SAFETY_ENDPOINT` — G-16 enhanced harm + PII check
  - SQLite stays for this demo; production swaps to **Azure Cosmos DB** (NoSQL)
- Same `demo` / `1234` credentials, same two scenario cards — only the backend tier changes

**Recording order**
1. Opening / App Introduction — architecture, Azure services, orchestration, best practices
2. **[MOCK MODE]** Scenario A — **Alex Chen** (Novice, AI-102) — full 7-tab walk
3. **[MOCK MODE]** Scenario B — **Priyanka Sharma** (Expert, DP-100) — full 7-tab walk
4. **[LIVE MODE]** Toggle demo — tier promotion + richer LLM output side-by-side
5. Guardrails demo — BLOCK / WARN (works in both modes)
6. Admin Dashboard — RunTrace, Azure Monitor integration
7. Closing — best practices recap

---

---

## PART 0 — OPENING (1 min)

### What to show on screen
> Login page. Don't type yet.

---

**SPEAK:**

> "Welcome to the Certification Prep Multi-Agent System — a production-grade AI application built on Microsoft Azure that guides learners through their Microsoft certification journey from zero to exam-ready.

> Let me start with the architecture. Eight specialised agents work in a typed sequential and concurrent pipeline.

> The orchestration pattern has four phases. First: a sequential intake phase — the LearnerProfilingAgent runs alone, profiling the learner from free-text input. It uses a three-tier fallback: Tier 1 is Azure AI Foundry Agent Service with full thread history and tool use; Tier 2 is Azure OpenAI GPT-4o called direct via the AzureOpenAI client; Tier 3 is the deterministic rule-based mock profiler for testing and CI. The app never fails due to missing credentials — it always has a tier.

> Second: a parallel fan-out — StudyPlanAgent and LearningPathCuratorAgent fire simultaneously in a ThreadPoolExecutor. No shared state, zero race conditions. We join when both complete.

> Third: two Human-in-the-Loop gates. No AI advancement without human input. These are hard gates — the pipeline literally waits.

> Fourth: a final sequential phase — ProgressAgent, AssessmentAgent, and CertRecommendationAgent run in order, each receiving a Pydantic v2 validated object from the previous step.

> The Azure services in play: Azure AI Foundry for the richest agent experience with memory and tools, Azure OpenAI GPT-4o as the direct API fallback, Azure AI Content Safety for real-time harm and PII scanning, SQLite for this demo with Azure Cosmos DB NoSQL in production, and Azure Monitor via OpenTelemetry for observability.

> A seventeen-rule Responsible AI guardrails pipeline wraps every cross-agent boundary. Three severity levels: BLOCK which hard-stops with st.stop(), WARN which lets the pipeline continue with an amber banner, and INFO for advisory notices.

> Best practices baked in: Pydantic v2 typed contracts on every handoff, zero-secret deployment pattern using Azure Key Vault and Managed Identity, URL trust guard preventing hallucinated Microsoft Learn links, exam-agnostic domain registry meaning any new cert is one dictionary entry, and 299 unit tests that run in under three seconds with zero Azure credentials.

> Today we run two complete learner journeys in Mock mode — deterministic, fully offline — then flip to Live mode and show exactly what changes when Azure steps in.

> Let's start."

---

---

## PART 1 — LOGIN (30 sec)

### What to show on screen
> Login form. Type slowly so it's legible.

---

**ACTION:** Type `demo` in the Name field. Type `1234` in the PIN field. Click **Sign In**.

**SPEAK:**

> "Any learner can register with just a name and a four-digit PIN. The PIN is stored plain-text locally — this is a demo dataset. In production you'd hash with SHA-256 or hand off to Entra ID.

> Once logged in, the sidebar shows two ready-made demo scenarios."

**PAUSE briefly** on the sidebar showing the two scenario cards:
- 🌱 **Novice** — AI-102
- 🏆 **Expert** — DP-100

> "Notice the mode badge at the bottom of the sidebar — it says Mock Mode. That means all eight agents run on deterministic rule-based logic. No Azure credentials, no API calls, identical output every time. The toggle at the top of the page switches to Live Azure mode instantly."

---

---

## PART 2 — SCENARIO A: ALEX CHEN (Novice, AI-102) (~5 min)

### 2.0 — Pick the Scenario

**ACTION:** In the sidebar, click the **🌱 Novice** card.

**SPEAK:**

> "Scenario A — Alex Chen. Recent CS graduate, no cloud experience, wants to break into AI engineering. Twelve hours a week, ten weeks available."

The intake form auto-fills. **PAUSE** to show the prefilled fields.

> "Notice all seven fields are pre-populated — background, target exam AI-102, concerns, and goal. In a real session the learner types these in themselves."

---

### 2.1 — Generate Plan (HITL intake + Block 0)

**ACTION:** Scroll down slightly to see the full form. Click **✨ Generate My Plan**.

**SPEAK:**

> "The moment that button is pressed, the Streamlit app calls the orchestrator. We are in **Mock Mode** — so let me narrate exactly what happens.

> First: pre-flight guardrails G-01 through G-05 fire in under one millisecond. They validate the raw intake struct — non-empty name, known exam code from the registry, hours between 1 and 80, weeks between 1 and 52. Any failure hard-stops the pipeline before a single agent is instantiated.

> Input passes clean. The **LearnerProfilingAgent** starts. It checks for `AZURE_AI_PROJECT_CONNECTION_STRING` — not set, Tier 1 skipped. Checks `AZURE_OPENAI_ENDPOINT` — not set, Tier 2 skipped. Falls to **Tier 3 — the deterministic rule-based profiler** in b1_mock_profiler.py. Same code used by all 299 unit tests.

> Simultaneously, the orchestrator fires **StudyPlanAgent** and **LearningPathCuratorAgent** in a ThreadPoolExecutor with max_workers=2. They are completely independent — no shared mutable state — and the executor joins when both finish. On a real machine this parallel execution saves roughly 40% wall-clock time vs sequential.

> All three complete. The orchestrator assembles the LearnerPipelineContext Pydantic object and writes it to SQLite atomically."

Wait for the results to render.

---

### 2.1b — Mock Mode explained: what differs in Live Mode

**SPEAK:**

> "In Mock Mode the domain confidence scores come from a rule table in b1_mock_profiler.py: base scores keyed by role, a plus-10% boost per held certification, and a minus-15% penalty per concern keyword matched. Fast, deterministic, great for testing and CI.

> In Live Mode with Azure OpenAI Tier 2, the same LearnerIntake struct is serialised to JSON and sent as a structured prompt to GPT-4o. The model reasons over the background text, extracts implicit skill signals, and returns a JSON object matching the DomainProfile Pydantic schema. The word 'graduate' might push Plan and Manage slightly higher; 'no cloud experience' pulls all Azure-specific domains down. These are semantic inferences the rule table cannot make.

> In Live Mode with Azure AI Foundry Tier 1, profiling runs inside a Foundry Agent thread with memory \u2014 the agent can ask clarifying questions, retrieve from a knowledge base, and produce an even richer profile. The return contract is identical \u2014 same DomainProfile model \u2014 so every downstream agent runs unchanged.

> Three tiers. One contract. That is the core design decision that makes this system both CI-safe and production-ready."

---

### 2.2 — Tab 1: Domain Map 🗺️

**ACTION:** Click the **🗺️ Domain Map** tab.

**SPEAK:**

> "Tab one — Domain Map. This is the output of the LearnerProfilingAgent.

> Six domains for AI-102: Plan and Manage, Computer Vision, NLP, Document Intelligence, Conversational AI, and Generative AI. Each bar is Alex's confidence score — zero to one.

> Alex has no Azure experience, so almost all domains start low. Generative AI and Computer Vision are flagged as risk domains — shown in red. Those will get the most study hours and will be front-loaded in the Gantt plan coming up."

**POINT OUT** (hover over the bar chart): The risk domain indicators and the 'Areas to focus' section below the chart.

> "Below the chart you can see the Insight panel — weakest domains, recommended approach, and a personalised engagement note based on Alex's goal text. All of this comes from analyzing just the free-text background the learner typed."

> "There are seven tabs in total. I'll work through them left to right — but I'll come back to Tab four, Recommendations, twice more because it gets richer after each Human-in-the-Loop gate."

---

### 2.3 — Tab 2: Study Setup 📅

**ACTION:** Click the **📅 Study Setup** tab.

**SPEAK:**

> "Tab two — the Gantt study plan from StudyPlanAgent.

> This used the Largest Remainder algorithm to distribute 120 hours — that's twelve hours times ten weeks — across six domains in proportion to exam weight. Not simple rounding — Largest Remainder guarantees the total is exactly 120 hours.

> Notice Computer Vision and NLP both carry 22.5% exam weight, so they get the most hours. Generative AI — flagged as risk — is scheduled in weeks one to four. That's the remediation-first approach: tackle what Alex fears most while energy is highest.

> At the top there's a prerequisite gap warning. Alex doesn't hold AI-900, which Microsoft strongly recommends before sitting AI-102. The pipeline flags it but doesn't block — the learner decides.

> And there are two download buttons — a PDF study plan and a welcome email summary. Both generated by ReportLab and the SMTP helper in the progress agent module."

**ACTION:** Click the **📥 Download Study Plan PDF** button to show it works.

---

### 2.4 — Tab 3: Learning Path 📚

**ACTION:** Click the **📚 Learning Path** tab.

**SPEAK:**

> "Tab three — Learning Path, from LearningPathCuratorAgent.

> Each exam domain maps to two or three Microsoft Learn modules. Alex chose hands-on labs as a preferred learning style, so lab modules are ordered first within each domain — that's the style-aware sorting logic.

> Every URL here was validated by Guardrail Rule G-17 before it was persisted — only learn.microsoft.com, docs.microsoft.com, aka.ms, and Pearson VUE domains are trusted. Any other URL would be silently removed and a warning surfaced."

**ACTION:** Expand one or two domain accordions to show the module cards.

---

### 2.4b — Tab 4: Recommendations 💡 (First Visit — Profile Insights Only)

**ACTION:** Click the **💡 Recommendations** tab (Tab 4).

**SPEAK:**

> "Tab four — Recommendations. Right now this shows the profile-level insights from the LearnerProfilingAgent: learning style, experience level, risk domains, and a prioritised action list for each domain.

> Notice the Exam Booking Guidance section at the bottom — it shows a soft 'more preparation needed' card because no quiz has been submitted yet. The pipeline uses the readiness assessment when available, and the full assessment result after the quiz. This tab gets richer at each stage."

**POINT OUT** the three columns: Learning Style card, Focus Domains card, Next-cert suggestion card.

---

### 2.5 — Tab 5: My Progress 📈 (HITL Gate 1)

**ACTION:** Click the **📈 My Progress** tab (Tab 5).

**SPEAK:**

> "Tab five — and here's the first Human-in-the-Loop gate.

> The pipeline has done everything it can from the intake data. Now it needs new information that only Alex can provide: how much has actually been studied?

> This check-in form asks for total hours spent, a one-to-five confidence rating per domain, and optionally a practice exam score. The AI cannot infer this — it must wait for the human."

**ACTION:** Fill in the form:
- Total study hours: `45`
- Set all domain sliders to around **2–3** (weak-to-moderate)
- For Computer Vision and NLP, drag sliders to **2** (Alex's weakest areas)
- Practice exam done: **Yes** — enter score `52`
- Notes: `Struggled with the Azure OpenAI and Vision APIs`

**SPEAK:**

> "Guardrails G-11 through G-13 fire before the ProgressAgent even sees this data — negative hours would block, ratings outside one to five would block, scores outside zero to one hundred would block."

**ACTION:** Click **✅ Assess My Readiness**.

**SPEAK:**

> "The ProgressAgent applies the weighted formula: 55% domain confidence, 25% hours utilisation, 20% practice score. With a practice score of 52 and moderate self-ratings, Alex is likely to come out as Nearly Ready or Needs Work."

Wait for the readiness card to appear.

> "There's the verdict. And below it, per-domain nudges — colour-coded danger, warning, and info levels — and a detailed domain status table showing which areas are on track versus behind schedule.

> If the verdict had come back Not Ready, the Knowledge Check tab would be locked and Alex would be redirected to revise the study plan."

---

### 2.5b — Tab 4: Recommendations 💡 (Second Visit — After Gate 1)

**ACTION:** Click back to the **💡 Recommendations** tab (Tab 4).

**SPEAK:**

> "Back to Recommendations. Now the Exam Booking Guidance section has updated — it's reading from the ReadinessAssessment output of the ProgressAgent, so it shows a richer verdict with the conditional booking guidance.

> The top profile section is unchanged. Only the booking section reacts to the new data. This is the incremental enrichment pattern — the tab is always visible, it just adds information as signals become available."

---

### 2.6 — Tab 6: Knowledge Check 🧪 (HITL Gate 2)

**ACTION:** Click the **🧪 Knowledge Check** tab (Tab 6).

**SPEAK:**

> "Tab six — the second and final Human-in-the-Loop gate.

> The AssessmentAgent generated thirty questions distributed by exam weight, using the same Largest Remainder algorithm as the study plan. So Computer Vision and NLP — the heaviest domains — get the most questions."

**ACTION:** Scroll through to show a few questions. Point out the domain labels on each question.

> "Each question carries the domain it tests, and the difficulty level. Notice the Submit button is greyed out — it only activates once all thirty questions have an answer selected. That's the pipeline enforcing completeness."

**ACTION:** Select answers for all questions — pick a mix of correct and incorrect to get a realistic score. Click **📝 Submit Quiz**.

**SPEAK:**

> "G-14 and G-15 fire on the assessment itself — if there were fewer than five questions, or duplicate IDs, those would block here. Then evaluation: each domain is scored independently, then weighted and combined."

Wait for the results panel to render.

> "Score card. Domain breakdown. The weak domains where Alex scored under 70% are highlighted."

---

### 2.6b — Tab 4: Recommendations 💡 (Third Visit — Full Booking Guidance)

**ACTION:** Click back to the **💡 Recommendations** tab (Tab 4).

**SPEAK:**

> "And here's the final state of the Recommendations tab. The CertRecommendationAgent has now run with the full AssessmentResult, so the Exam Booking Guidance section shows the definitive verdict.

> If Alex passed — Ready to Book the Exam — the full booking checklist appears: valid government ID, Pearson VUE account, quiet room, stable internet. Each item is an interactive checkbox.

> If not — a targeted remediation plan listing the specific domains that need more work, with a suggested re-attempt timeline.

> Either way the tab shows full exam logistics: passing score 700 on a 1000-point scale, 40 to 60 questions, 100 minutes, and the Pearson VUE scheduling link.

> And at the very bottom — next certification recommendations. For AI-102 the synergy map points to AZ-204 Azure Developer, with a rationale card explaining the progression path.

> This is the final output. Everything from this run is saved to SQLite — profile, plan, learning path, progress snapshot, assessment result, and recommendation — so Alex can come back tomorrow and pick up exactly here."

---

### 2.7 — Tab 7: Raw JSON 📄

**ACTION:** Click the **📄 Raw JSON** tab (Tab 7).

**SPEAK:**

> "Quick engineering note — Tab seven exposes the raw JSON for every pipeline artefact. Useful for debugging, for building integrations, or for importing into Cosmos DB or any downstream service. This is the actual typed Python objects serialised to JSON — no transformation."

---

---

## PART 3 — SCENARIO B: PRIYANKA SHARMA (Expert, DP-100) (~3 min)

### 3.0 — Switch Scenario

**ACTION:** In the sidebar click **↩ Reset scenario**, then click the **🏆 Expert** card.

**SPEAK:**

> "Scenario B — Priyanka Sharma. Five years in data science, holds AZ-900 and AI-900, targeting DP-100 Azure Data Scientist. Eight hours a week, six weeks. A very different starting profile."

---

### 3.1 — Generate Plan

**ACTION:** Click **✨ Generate My Plan**.

**SPEAK:**

> "Same pipeline, completely different output. Priyanka's existing certifications give domain score boosts — the mock profiler's cert-to-domain boost table maps AZ-900 and AI-900 to Machine Learning Fundamentals and Data Exploration. So those domains start with higher confidence.

> Risk domains this time are hyperparameter tuning and model deployment — which she explicitly listed as concerns. The concern-topic penalty rule applied a minus 15% confidence reduction to those domains."

---

### 3.2 — Tabs 1–4: Domain Map, Study Setup, Learning Path, Recommendations

**ACTION:** Click each tab in sequence — spend 20–30 seconds on each.

- **Tab 1 Domain Map:** Point out the higher baseline scores compared to Alex. Only 2 risk domains (vs 4 for Alex). AZ-900 and AI-900 boost is visible.
- **Tab 2 Study Setup:** Fewer total hours (48 = 8×6). Machine Learning domain gets the most hours (37.5% weight). No prerequisite gap — she already holds the recommended certs.
- **Tab 3 Learning Path:** Priyanka chose Video tutorials + Hands-on labs, so video modules come first. Learning path is shorter because STRONG domains get fewer modules.
- **Tab 4 Recommendations (first visit):** Profile insights — experience level shows Data Analyst/Scientist, no critical risk domains flagged as severe. Early booking card already shows near-ready signals.

**SPEAK:**

> "Notice how different the plans look. Same pipeline, same agents, completely personalised output driven by the learner's profile. That's the exam-agnostic registry design — adding a new certification just means adding a new entry to EXAM_DOMAIN_REGISTRY in models.py. No agent code changes."

---

### 3.3 — Progress Check-In (Gate 1)

**ACTION:** Click **📈 My Progress**. Fill in:
- Total hours: `40`
- All domain sliders set to **4** (Priyanka is experienced)
- ML Fundamentals: **5** (her strongest area)
- Practice exam: **Yes** → Score: `74`

**ACTION:** Click **✅ Assess My Readiness**.

**SPEAK:**

> "With strong self-ratings and a practice score of 74, Priyanka should land Exam Ready. The formula: 55% confidence, 25% utilisation, 20% practice."

Point to the **Exam Ready** / **GO** verdict.

**ACTION:** Click back to **💡 Recommendations** (Tab 4) briefly.

> "Tab four has updated again — Exam Booking Guidance now shows GO, based on the readiness formula output. We can already see the booking checklist appearing."

---

### 3.4 — Knowledge Check (Gate 2)

**ACTION:** Click **🧪 Knowledge Check** (Tab 6). Select answers — try to get most correct for Priyanka. Click **📝 Submit Quiz**.

**SPEAK:**

> "Priyanka passes comfortably. Now Tab four will show the full booking checklist from the AssessmentResult."

**ACTION:** Click **💡 Recommendations** (Tab 4). Show the booking checklist and next-cert progression.

**SPEAK:**

> "Ready to Book. Booking checklist, exam metrics, Pearson VUE link, and the next-cert suggestion — for DP-100 the synergy map routes to AI-102. Priyanka already holds AI-900 which gives her a head start there."

---

---

## PART 3b — LIVE MODE DEMO (~2 min)

> **Pre-requisite:** `.env` must be populated. Record this segment separately if credentials are only available in a specific environment.

**ACTION:** In the sidebar, toggle from 🧪 **Mock Mode** to 🚀 **Live Mode**.

**SPEAK:**

> "One toggle. That is all it takes to go from fully offline to full Azure."

**POINT TO** the mode badge changing in the sidebar.

> "The app re-reads the `.env` file. It finds `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY` — Tier 2 is now active. If `AZURE_AI_PROJECT_CONNECTION_STRING` were also set, the pipeline would auto-promote to Tier 1 Azure AI Foundry. No code change, no restart."

**ACTION:** Click **↩ Reset scenario**, then pick the 🌱 **Novice** card again. Click **✨ Generate My Plan**.

**SPEAK:**

> "Same intake, same form. Behind the scenes the LearnerProfilingAgent is now calling **Azure OpenAI GPT-4o** via the `openai.AzureOpenAI` client. The structured prompt includes Alex's background text, the exam domain list, and the role context. GPT-4o returns a JSON object matching the DomainProfile schema \u2014 same Pydantic model, different quality of scores."

**ACTION:** Click the **🗺️ Domain Map** tab.

> "Notice the confidence scores are subtly different from the Mock run. The LLM picked up signals the rule table cannot: 'computer science graduate' slightly raises the theoretical domains; 'no cloud or Azure experience at all' depresses every Azure service domain. Semantic inference from nine words of background text.

> The StudyPlanAgent received these new weights and re-allocated the 120 hours accordingly. Better profiling flows downstream to a better plan \u2014 automatically."

**ACTION:** Click **📅 Study Setup** briefly to show the updated Gantt.

> "Same Largest Remainder algorithm, same template \u2014 different domain weights going in, different hour distribution coming out."

**SPEAK:**

> "Two more Azure services activate in Live Mode that are invisible in the UI but critical in production.

> First: **Azure AI Content Safety**. Rule G-16 in Mock Mode uses a keyword heuristic \u2014 a curated list in guardrails.py. In Live Mode it upgrades to an API call to the Azure AI Content Safety endpoint, scoring four harm categories \u2014 Hate, Violence, Self-Harm, Sexual \u2014 each on a 0\u20137 severity scale, plus a dedicated PII detection pass. Same BLOCK/WARN outcome, much higher signal fidelity.

> Second: **Azure Monitor via OpenTelemetry**. The RunTrace AgentStep schema is aligned to the OpenTelemetry GenAI semantic conventions. In Live Mode those spans are emitted to an Azure Monitor workspace \u2014 giving you latency per agent, token consumption per LLM call, guardrail fire rates, and HITL gate durations in one Application Insights dashboard.

> In production the data layer swaps from **SQLite to Azure Cosmos DB NoSQL**. The database module uses a repository pattern \u2014 same JSON documents, same `student_id` partition key, same method signatures. One environment variable swap."

**ACTION:** Toggle back to 🧪 **Mock Mode** before continuing.

---

---

## PART 4 — GUARDRAILS DEMO (~2 min)

> **Goal:** Show the Responsible AI layer blocking bad input and warning on PII.

**ACTION:** Sign out and sign back in as `demo`. Click the 🌱 **Novice** card. On the intake form, make these deliberate bad edits before clicking Generate:

---

### 4.1 — Block on invalid hours

**ACTION:** Clear the hours/week field and type `0`.

**SPEAK:**

> "Rule G-02 — hours per week must be between one and eighty. Zero fails the boundary check."

**ACTION:** Click **Generate**. Show the red BLOCK banner: `[G-02] hours_per_week must be between 1 and 80`.

> "The pipeline hard-stops. st.stop() is called. No agent ran."

**ACTION:** Set hours back to `12`.

---

### 4.2 — Block on harmful content

**ACTION:** In the background text field, add the text: `I want to hack the exam system`.

**SPEAK:**

> "Rule G-16 — content safety. The heuristic scanner checks all free-text fields for harmful keywords."

**ACTION:** Click **Generate**. Show the red BLOCK banner for G-16.

> "BLOCK. The word 'hack' triggers the harmful content rule. In Mock Mode this uses a local keyword heuristic — a curated list maintained in guardrails.py. In Live Mode, G-16 upgrades to the **Azure AI Content Safety API**: the text is scored across four harm categories — Hate, Violence, Self-Harm, Sexual — each on a severity scale of 0–7. A score above the configured threshold triggers the same BLOCK. Same user experience, much stronger signal."

**ACTION:** Remove the harmful text. Restore to Alex's original background.

---

### 4.3 — Warn on PII

**ACTION:** Add to the background field: `My SSN is 123-45-6789`.

**SPEAK:**

> "Rule G-16 also covers PII — SSN, credit card, email in bio, phone numbers. This one is a WARN, not a BLOCK — the pipeline continues but surfaces the amber banner."

**ACTION:** Click **Generate**. Show the amber WARN for G-16 PII. Pipeline continues, profile renders.

> "The learner is informed but not stopped. In Live Mode the PII detection uses the **Azure AI Content Safety API** — matched PII spans are redacted before the text is forwarded to the Azure OpenAI prompt. Nothing containing a social security number, credit card, or phone number ever reaches the LLM call."

**ACTION:** Remove the SSN. Restore the form.

---

---

## PART 5 — ADMIN DASHBOARD (~1.5 min)

**ACTION:** Sign out. Sign back in — Name: `admin`, PIN / password field: type `agents2026`.

**SPEAK:**

> "Separate login path for admin users. The Admin Dashboard has a different layout."

**ACTION:** In the sidebar, click **🔐 Admin Dashboard** (or navigate to `localhost:8501/1_Admin_Dashboard`).

---

**SPEAK:**

> "The Admin Dashboard reads directly from SQLite and shows every student's full journey in one place."

Point out:
1. **Summary metrics** at the top — total students, exams in progress, completion rate
2. **Students table** — columns include exam target, readiness %, verdict, last updated
3. **Expand any student row** — shows profile, plan, assessment result side by side
4. **Agent Timeline tab** — the RunTrace. Per-agent execution time, status (success / repaired / skipped), and the decisions each agent made

**SPEAK:**

> "This RunTrace is built up by the orchestrator in real time — one AgentStep record per agent, with wall-clock milliseconds, status, and the key decisions made. You can see which tier ran for profiling — Tier 1 Foundry, Tier 2 OpenAI, or Tier 3 Mock — whether any guardrail fired, and the parallel execution time for StudyPlan and LearningPath side by side.

> The AgentStep schema aligns with the **OpenTelemetry GenAI semantic conventions** — span name, model, token counts, latency. In production those spans feed an **Azure Monitor** workspace via the Azure Monitor OpenTelemetry Distro, giving you the full distributed trace in Application Insights: latency per agent, LLM token consumption, guardrail fire rates, and HITL gate durations in a single dashboard.

> From here you can answer: which learner profiles take the longest to process? Which guardrail rule fires most? How does Tier 1 Foundry latency compare to Tier 2 OpenAI? Operational intelligence, not just app logs."

---

---

## PART 6 — CLOSING (30 sec)

**ACTION:** Navigate back to the main app (`localhost:8501`). Show the sidebar mode badge.

**SPEAK:**

> "Let me close with a summary of what we have seen across both modes.

> **Mock Mode** — eight agents, fully deterministic, zero Azure credentials needed. 299 unit tests pass in under three seconds. Every feature works: all seven tabs render, both HITL gates fire, guardrails block and warn, the Admin Dashboard shows full RunTrace. This is how you develop, CI, and demo offline.

> **Live Mode** — the same eight agents, the same Pydantic contracts, the same seventeen guardrail rules, the same two HITL gates. The difference: Tier 1 Azure AI Foundry gives the richest profiling — full agent thread with memory and tool use. Tier 2 Azure OpenAI GPT-4o gives strong semantic profiling via a direct API call. Azure AI Content Safety elevates G-16 from keyword matching to scored harm and PII detection. Azure Monitor and OpenTelemetry give production-grade observability.

> **Best practices demonstrated:** typed handoffs with Pydantic v2, zero-secret deployment with Azure Key Vault and Managed Identity, URL trust guard preventing hallucinated content from reaching learners, exam-agnostic registry for infinite extensibility, parallel fan-out for performance, and two HITL gates ensuring the AI never acts without human verification.

> The data layer is abstracted behind a repository interface — SQLite today, Azure Cosmos DB NoSQL in production, one configuration change.

> Source code, architecture diagrams, and full technical documentation are in the repository. Thanks for watching."

---

---

## APPENDIX — QUICK ACTION CHEAT SHEET

Use this during recording to avoid hesitation.

| Step | Where | What to click / type |
|------|-------|---------------------|
| Login (demo) | Login page | Name: `demo` · PIN: `1234` |
| Login (admin) | Login page | Name: `admin` · Password: `agents2026` |
| Pick Novice | Sidebar | Click 🌱 **Novice** card |
| Pick Expert | Sidebar | Click 🏆 **Expert** card |
| Reset scenario | Sidebar | Click **↩ Reset scenario** |
| Generate plan | Intake form | Click **✨ Generate My Plan** |
| Alex progress (Gate 1) | Tab 5: My Progress | Hours: `45` · All sliders: 2–3 · Practice: `52` |
| Priyanka progress (Gate 1) | Tab 5: My Progress | Hours: `40` · All sliders: 4–5 · Practice: `74` |
| Submit quiz (Gate 2) | Tab 6: Knowledge Check | Answer all 30 · Click **📝 Submit Quiz** |
| **Switch to Live Mode** | **Sidebar mode toggle** | **Click 🧪 Mock → 🚀 Live** |
| **Switch back to Mock** | **Sidebar mode toggle** | **Click 🚀 Live → 🧪 Mock** |
| Force G-02 BLOCK | Intake form | Set hours/week to `0` |
| Force G-16 BLOCK | Background text | Add `I want to hack the exam system` |
| Force G-16 PII WARN | Background text | Add `My SSN is 123-45-6789` |
| Admin Dashboard | Sidebar | Click **🔐 Admin Dashboard** |
| Sign out | Sidebar | Click **🚪 Sign Out** |

---

## APPENDIX — KEY TALKING POINTS (pick any for voice-over)

**Azure services used**
- **Azure AI Foundry Agent Service** (Tier 1) — `azure-ai-projects` SDK; full agent thread with memory, tool calls, knowledge retrieval; activated via `AZURE_AI_PROJECT_CONNECTION_STRING`
- **Azure OpenAI GPT-4o** (Tier 2) — `openai.AzureOpenAI` client; structured JSON prompting; activated via `AZURE_OPENAI_ENDPOINT` + `AZURE_OPENAI_API_KEY` + `AZURE_OPENAI_DEPLOYMENT`
- **Azure AI Content Safety** — `azure-ai-contentsafety` SDK; Hate / Violence / Self-Harm / Sexual categories + PII detection; upgrades G-16 from keyword heuristic to API-scored verdicts in Live Mode
- **Azure Cosmos DB NoSQL** — production data layer (SQLite in demo); same JSON document structure; `student_id` as partition key; repository pattern in `database.py` abstracts the swap
- **Azure Monitor + OpenTelemetry** — RunTrace AgentStep schema aligned to GenAI semantic conventions; feeds Application Insights via Azure Monitor OpenTelemetry Distro in production
- **Azure Key Vault + Managed Identity** — zero-secret deployment pattern; no credentials in environment variables or code in production
- **Microsoft Entra ID** — production authentication; replaces PIN login with token-based identity
- **Pearson VUE** — external exam booking; link generated by CertRecommendationAgent and validated by G-17 URL trust guard before it reaches the learner

**Agent orchestration patterns**
- **Sequential intake phase**: LearnerProfilingAgent runs alone; its DomainProfile output gates the rest of the pipeline
- **Parallel fan-out**: StudyPlanAgent ‖ LearningPathCuratorAgent via `ThreadPoolExecutor(max_workers=2)`; joined before downstream agents start; ~40% wall-clock saving vs sequential
- **Sequential evaluation phase**: ProgressAgent → AssessmentAgent → CertRecommendationAgent; each receives Pydantic-validated output from the previous agent
- **HITL gate pattern**: pipeline pauses at Gate 1 (Tab 5 My Progress) and Gate 2 (Tab 6 Knowledge Check); no agent fires past a gate until the human submits
- **Three-tier LLM fallback**: Tier 1 Foundry → Tier 2 OpenAI → Tier 3 Mock; app auto-discovers which tier to use at startup via env variable presence; entire pipeline runs on all three
- **Typed handoff contract**: every inter-agent boundary is a Pydantic v2 model; schema violations raise `ValidationError` and surface a WARN before they corrupt downstream state

**Mock Mode vs Live Mode**
- **Mock Mode**: Tier 3 rule-based profiler; deterministic scores; zero API calls; CI-safe; 299 tests run in ≤3 seconds; every feature fully functional
- **Live Mode**: Tier 1 or Tier 2 LLM profiling; semantic score inference from free text; Azure AI Content Safety active; Azure Monitor traces emitted; richer personalisation
- **What stays identical**: Pydantic models, guardrail rules, HITL gates, Gantt algorithm, quiz sampling, all seven tabs, all 299 tests
- **What changes**: domain confidence score quality, content safety fidelity, observability depth — nothing else

**Architecture highlights**
- Eight agents in a typed sequential + concurrent pipeline
- Parallel fan-out: StudyPlanAgent and LearningPathCuratorAgent run simultaneously in ThreadPoolExecutor
- Three-tier fallback: Foundry → OpenAI → Mock — app never fails due to missing credentials
- Exam-agnostic registry: add any Microsoft certification in one dict entry in `models.py`
- Streamlit app is the UI layer; all business logic lives in `src/cert_prep/`; clean separation enables non-Streamlit frontends without code changes
- Repository pattern on `database.py`: SQLite in dev/demo → Azure Cosmos DB in production, one config change

**Responsible AI / Guardrails**
- 17 rules, 3 severity levels: BLOCK (`st.stop()` — pipeline never runs), WARN (pipeline continues, amber banner), INFO (advisory only)
- G-16: Mock = keyword heuristic list; Live = Azure AI Content Safety API (4 harm categories + PII, 0–7 severity scoring)
- G-17: URL trust guard — only `learn.microsoft.com`, `docs.microsoft.com`, `aka.ms`, Pearson VUE allowed; hallucinated URLs silently removed
- Every violation logged with `student_id`, `run_id`, rule code, severity, and field name

**Human-in-the-Loop**
- Gate 1 (Tab 5 My Progress): Learner self-reports total hours + per-domain confidence (1–5 scale) + optional practice exam score
- Gate 2 (Tab 6 Knowledge Check): Learner answers 30 weighted questions — Submit button locked until all answered
- AI never advances past a gate independently — human input is structurally required by the pipeline
- Remediation loop: NOT READY verdict → CertRecommendationAgent returns domain-specific remediation plan with re-attempt timeline

**Engineering quality**
- 299 unit tests, 100% pass rate, run in ≤3 seconds, zero Azure credentials
- Pydantic v2 validates every cross-agent data handoff — no silent data corruption
- Largest Remainder algorithm guarantees exact hour totals and question counts
- SQLite WAL mode + atomic ThreadPoolExecutor design prevents concurrent write errors
- `database.py` repository pattern ready for Azure Cosmos DB swap with one env variable

---

*Script version: 2.0 · Last updated: 2026-02-26*
