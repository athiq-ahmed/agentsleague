# 📋 User Flow Scenarios — Microsoft Cert Prep Multi-Agent System

> This document describes every user journey the system supports, including the exact sequence of technical events behind each user action. Intended audience: developers, QA engineers, and technical judges.

---

## Navigation Map

| Scenario | User Type | Mode | Entry Point |
|---|---|---|---|
| [S1 — New Learner, AI-102](#s1--new-learner-ai-102-from-scratch) | First-time user | Mock | Login → Intake Form → Full pipeline |
| [S2 — Returning Learner, DP-100](#s2--returning-learner-dp-100-profile-on-file) | Returning user | Mock | Login → Restore → Progress → Quiz |
| [S3 — Live Azure OpenAI Mode](#s3--live-azure-openai-mode) | New user with Azure credentials | Live GPT-4o | Login → Intake → Azure profiling |
| [S4 — Admin Dashboard](#s4--admin-user-audit-dashboard) | Admin | N/A | /pages/1_Admin_Dashboard |
| [S5 — Remediation Loop](#s5--remediation-loop-score--70) | Any learner | Mock/Live | After quiz — score < 70% |
| [S6 — Edit Profile](#s6--returning-user-edits-profile) | Returning user | Mock/Live | Profile card → Edit |
| [S7 — Guardrail BLOCK](#s7--guardrail-block-scenarios) | Any user | Any | Various — invalid inputs |

---

## S1 — New Learner, AI-102 from Scratch

**Persona:** Alex Chen — CS graduate, no Azure experience, targeting AI-102.  
**Mode:** Mock (no Azure credentials needed)  
**Time to complete:** ~5 minutes (mock) / ~12 minutes (live Azure OpenAI)

### User Actions and Technical Events

```
Browser → https://agentsleague.streamlit.app

    [LOGIN SCREEN]
    Three demo cards shown.
    User clicks "Alex Chen — New Learner" card.

    TECHNICAL:
      st.session_state["logged_in"]  = True
      st.session_state["login_name"] = "Alex Chen"
      upsert_student("Alex Chen","1234","learner") → SQLite write

    [INTAKE FORM — pre-filled via sidebar_prefill="alex"]

    TECHNICAL — Pre-fill mechanism:
      st.session_state["sidebar_prefill"] = "alex"
      → prefill.update(_PREFILL_SCENARIOS["Alex Chen — complete beginner, AI-102"])
      → Every widget seeded via value=prefill.get(...)
      → email_input pre-filled with "alex.chen@demo.com"
```

### Form Fields Pre-filled

| Field | Pre-filled Value |
|-------|-----------------|
| Exam | AI-102 – Azure AI Engineer Associate |
| Email | alex.chen@demo.com |
| Hours/week | 12 |
| Weeks | 10 |
| Background | "Recent CS graduate, basic Python skills, no cloud experience" |
| Learning style | Hands-on labs, Practice tests |
| Motivation | Career growth |
| Concerns | Azure Cognitive Services, Azure OpenAI, Bot Service |

### After Submit — Pipeline Events

```
[GUARDRAILS G-01..G-05]
  G-01: student_name = "Alex Chen" — present ✓
  G-02: exam_target = "AI-102" — in EXAM_DOMAIN_REGISTRY ✓
  G-03: hours_per_week = 12 — in [1,80] ✓
  G-04: weeks_available = 10 — in [1,52] ✓
  G-05: background_text len > 10 ✓
  → GuardrailResult(blocked=False)
  → PASS — pipeline continues

[LEARNER PROFILING — b1_mock_profiler.py]
  Input: RawStudentInput(name="Alex Chen", exam="AI-102", email="alex.chen@demo.com", ...)
  Rule engine passes:
    Pass 1 — "cs graduate" matches → ExperienceLevel.BEGINNER
    Pass 2 — "no cloud" → all 6 AI-102 domains set to UNKNOWN/WEAK confidence
    Pass 3 — concern_topics ["Azure OpenAI","Bot Service"] → added to risk_domains
  Output: LearnerProfile(
    domain_profiles=[6 × DomainProfile],
    risk_domains=["D3-NLP","D5-Bots"],
    experience_level=BEGINNER
  )

[GUARDRAIL G-06..G-08 on LearnerProfile]
  G-06: len(domain_profiles) == 6 (AI-102 has 6 domains) ✓
  G-07: all confidence_score in [0,1] ✓
  G-08: all risk_domain IDs in registry ✓
  → PASS

[PARALLEL FAN-OUT — ThreadPoolExecutor(max_workers=2)]

  Thread A — StudyPlanAgent:
    Largest Remainder algorithm over 120 hours, 6 domains
    Assigns weekly blocks: e.g., D3 (0.25 weight) → 30 hours → weeks 1-4
    Prereq gap check: AZ-900 not in existing_certs → prereq_gaps=["AZ-900"]
    Output: StudyPlan(weekly_blocks=[...], prereq_gaps=["AZ-900"])

  Thread B — LearningPathCuratorAgent:
    Skips domains with skip_recommended=True (none for Alex — all weak)
    Maps each domain to top 3 MS Learn modules from MODULE_CATALOGUE
    Validates all URLs with G-17 (must be learn.microsoft.com/...)
    Output: LearningPath(modules=[...], total_modules=18)

  Both threads complete → guardrail checks applied to both outputs
  G-09..G-10: study plan bounds ✓
  G-17: all URLs verified ✓

[SQLITE PERSISTENCE]
  save_learner_profile(profile)
  save_study_plan(plan)
  save_learning_path(learning_path)
  save_raw_input(raw)  — includes email="alex.chen@demo.com"
  record AgentStep per agent

[UI RENDERS — 6 TABS]
  Tab 1: Domain radar chart (Plotly) — all 6 domains at low confidence
  Tab 2: Gantt chart (Plotly, 10 weeks)
  Tab 3: 18 MS Learn module cards
  Tab 4: [HITL Gate 1 form — awaiting user]
  Tab 5: [Locked until Gate 1 submitted]
  Tab 6: [Locked until quiz submitted]
```

### HITL Gate 1 — Progress Check-In

```
User fills Tab 4 form:
  hours_spent = 8
  domain_ratings = {D1:3, D2:2, D3:2, D4:3, D5:2, D6:4}
  practice_score = 45
  notes = "Struggling with Azure OpenAI endpoints"
  Clicks "Submit Progress"

[GUARDRAIL G-11..G-13]
  G-11: hours_spent = 8 >= 0 ✓
  G-12: all ratings in [1,5] ✓
  G-13: practice_score = 45 in [0,100] ✓
  → PASS

[ProgressAgent — readiness formula]
  normalised_confidence = mean([(3-1)/4,(2-1)/4,(2-1)/4,(3-1)/4,(2-1)/4,(4-1)/4])
                        = mean([0.50, 0.25, 0.25, 0.50, 0.25, 0.75]) = 0.417
  hours_utilisation     = 8 / 12 = 0.667
  practice_pct          = 45 / 100 = 0.45

  readiness_pct = 0.55×0.417 + 0.25×0.667 + 0.20×0.45
               = 0.229 + 0.167 + 0.090 = 0.486 → 48.6%
  verdict: NOT YET (< 50%)

  UI: "❌ 48.6% — NOT YET. Extend your study plan before booking."
  Weak domains highlighted: D2 (Vision), D3 (NLP), D5 (Decision AI)
```

### HITL Gate 2 — Mock Quiz

```
[AssessmentAgent — 30-question build]
  domain_weights: {D1:0.15, D2:0.20, D3:0.25, D4:0.20, D5:0.10, D6:0.10}
  Largest Remainder sampling:
    D3 → 7-8 questions (highest weight)
    D1, D2, D4 → 4-6 questions each
    D5, D6 → 3 questions each
    Total = exactly 30

User answers all 30, clicks "Submit Answers"

[GUARDRAIL G-14..G-15]
  G-14: len(questions) = 30 >= 5 ✓
  G-15: no duplicate question IDs ✓
  → PASS

[Scoring]
  domain_scores = {D1:83%, D2:75%, D3:62%, D4:100%, D5:67%, D6:100%}
  weighted_score = 0.15×83 + 0.20×75 + 0.25×62 + 0.20×100 + 0.10×67 + 0.10×100
                 = 12.45 + 15.0 + 15.5 + 20.0 + 6.7 + 10.0 = 79.65%
  verdict: PASS (>= 70%)
```

### Tab 6 — Cert Recommendation

```
[CertRecommendationAgent]
  Input: AssessmentResult(score=79.65%, profile=...)
  score >= 70 → ready_to_book = True
  next_cert = "AZ-204" (highest synergy with AI-102)
  booking_checklist = [
    "Valid government ID",
    "Register at pearsonvue.com/microsoft",
    "Pay exam fee ~$165 USD",
    "Choose exam centre or online proctored"
  ]

Output displayed on Tab 6:
  "✅ You are ready to book AI-102!"
  Next cert recommendation: AZ-204 — Azure Developer Associate
  Booking checklist rendered as step-by-step cards
  Consolidation plan: 2 weeks extra focus on D3 (Azure OpenAI) + D5 (AI Search)
```

---

## S2 — Returning Learner, DP-100 (Profile on File)

**Persona:** Priyanka Sharma — data scientist, completed full pipeline in previous session.  
**Mode:** Mock. Profile restored from SQLite.

### Login and Session Restore

```
User clicks "Priyanka Sharma" card on login screen.

TECHNICAL:
  upsert_student("Priyanka Sharma","1234","learner")
  _db_p = get_student("Priyanka Sharma") → SQLite read
  profile loaded from learner_profiles table
  plan, learning_path loaded from their tables

  st.session_state["is_returning"]   = True
  st.session_state["profile"]        = loaded_profile
  st.session_state["raw"]            = loaded_raw   (includes email)
  st.session_state["plan"]           = loaded_plan
  st.session_state["learning_path"]  = loaded_path

Key code branch:
  if is_returning and not st.session_state.get("editing_profile", False):
      submitted = False   # no form re-submission
      show read-only profile cards
```

### Read-Only Profile View

```
Three profile cards rendered:
  Card 1: Exam=DP-100, Budget=8hr×6wk, Email=priyanka.sharma@demo.com
  Card 2: Certs=AZ-900,AI-900, Focus=Azure ML,MLflow,model deployment
  Card 3: "5 years in data analytics with Python and SQL...", Style=Video+Hands-on

✏️ Edit Profile button shown — clicking it sets:
  st.session_state["editing_profile"] = True
  st.rerun() → shows editable form
```

### Continuing from Previous Session

All 6 tabs render immediately from `st.session_state`:
- If `progress_submitted=True` was stored: Tab 4 shows readiness result (no form shown again)
- If `quiz_submitted=True` was stored: Tab 5 shows quiz result; Tab 6 shows recommendation

No agents re-run on session restore. The pipeline only replays if the user submits new HITL gate input.

---

## S3 — Live Azure OpenAI Mode

**Difference from mock:** `LearnerProfilingAgent` calls GPT-4o instead of the rule-based profiler.

### Credential Setup

```
Sidebar → "☁️ Azure OpenAI Config" expander
  AZURE_OPENAI_ENDPOINT   = https://<resource>.openai.azure.com
  AZURE_OPENAI_API_KEY    = <key>
  AZURE_OPENAI_DEPLOYMENT = gpt-4o
  Toggle "Use live Azure OpenAI?" = ON

  → use_live = True
```

### Technical Difference at Profiling

```python
if use_live:
    os.environ["AZURE_OPENAI_ENDPOINT"]   = az_endpoint
    os.environ["AZURE_OPENAI_API_KEY"]    = az_key
    os.environ["AZURE_OPENAI_DEPLOYMENT"] = az_deployment

    profile = LearnerProfilingAgent().run(raw)
    # LearnerProfilingAgent internally:
    #   1. Builds system prompt with LearnerProfile JSON schema
    #   2. Sends RawStudentInput fields as user message
    #   3. Uses response_format type=json_object
    #   4. temperature=0.2 for deterministic structure
    #   5. Parses JSON → LearnerProfile Pydantic validation
    mode_badge = "Azure OpenAI"
else:
    profile = run_mock_profiling(raw)
    mode_badge = "Mock"
```

### Fallback on Error

```python
except Exception as e:
    st.error(f"Azure OpenAI call failed: {e}")
    st.info("Falling back to mock profiler.")
    profile = run_mock_profiling(raw)
    mode_badge = "Mock (fallback)"
```

All downstream agents, guardrails, and tabs work identically regardless of whether profiling was done by GPT-4o or the rule-based profiler.

---

## S4 — Admin User: Audit Dashboard

**Entry:** Navigate to `/pages/1_Admin_Dashboard.py`  
**Credentials:** username=`admin`, password=`agents2026`

### Dashboard Sections

```
[Student Roster]
  Query: SELECT name, exam_target, experience_level, created_at FROM learner_profiles
  Rendered as st.dataframe

[Agent Trace — Per-Run HTML]
  Query: SELECT * FROM agent_steps ORDER BY run_id, step_index
  Each step rendered as colour-bordered HTML card:
    - Agent name + timestamp + duration_ms
    - input_summary (truncated to 200 chars)
    - output_summary (key fields)
  Performance metric: "⚡ Parallel agents completed in Xms"

[Guardrail Audit]
  Query: SELECT * FROM guardrail_violations
  BLOCK violations: red left-border
  WARN violations: orange left-border
  Useful for judges: proves guardrails are real and firing

[Mode Badge]
  Shows which profile mode was used: "Mock" or "Azure OpenAI"
```

---

## S5 — Remediation Loop (Score < 70%)

**Trigger:** Quiz score < 70% after Tab 5 submission.

```
Quiz score = 58%

[CertRecommendationAgent — remediation branch]
  ready_to_book = False
  weak_domains = [D3 (scored 45%), D5 (scored 55%)]
  remediation_plan = [
    "D3 Azure OpenAI: scored 45%, target 75% — add 8 extra hours",
    "D5 Decision AI: scored 55%, target 75% — switch to hands-on labs"
  ]

UI shows:
  "❌ Not ready to book — targeted review planned"
  Domain breakdown table with scores vs targets
  "🔄 Regenerate Study Plan with Updated Focus" button

User clicks Regenerate:
  st.session_state["remediation_domains"] = ["D3","D5"]
  st.session_state.pop("plan")
  st.session_state.pop("learning_path")
  st.rerun()

StudyPlanAgent re-runs:
  Weak domain confidence reset to 0.1 for D3, D5
  Largest Remainder reallocates more hours to D3, D5
  New StudyPlan overwrites in SQLite (version 2 of plan)

LearningPathCuratorAgent re-runs:
  Selects hands-on-lab variants for D3, D5 (if available)
  New LearningPath overwrites in SQLite
```

---

## S6 — Returning User Edits Profile

**Trigger:** Returning user clicks "✏️ Edit Profile" on profile card.

```
st.session_state["editing_profile"] = True
st.rerun()

Intake form renders with all fields pre-populated from stored raw:
  prefill["email"] = getattr(_raw_r, "email", "") or session email
  User changes exam from AI-102 to AZ-204
  User changes hours from 10 to 15
  User clicks "💾 Save & Regenerate Plan"

[Full pipeline reruns from guardrails onwards]
  G-02: AZ-204 in EXAM_DOMAIN_REGISTRY ✓
  New LearnerProfile generated for AZ-204 (6 AZ-204 domains)
  StudyPlan and LearningPath regenerated for AZ-204 in parallel
  Old plan/path overwritten in SQLite
  st.session_state.pop("editing_profile")
  All 6 tabs updated to reflect AZ-204 content
```

---

## S7 — Guardrail BLOCK Scenarios

### Scenario A: Invalid exam code

```
User attempts to submit with exam "AZ-999" (not in registry)
  G-02: "AZ-999" not in EXAM_DOMAIN_REGISTRY
  → GuardrailViolation(code="G-02", level=BLOCK,
      message="Exam code AZ-999 is not in the supported registry.")
  → st.error("Guardrail [G-02]: Exam code AZ-999 is not in the supported registry.")
  → st.stop()  — pipeline halts, nothing below runs
```

### Scenario B: Hours out of range

```
hours_per_week = 0 (edge case — slider prevents, but programmatic test):
  G-03: 0 not in [1,80]
  → BLOCK: "Hours per week must be between 1 and 80."
  → st.stop()
```

### Scenario C: URL hallucination caught

```
LearningPathCuratorAgent returns module URL:
  "https://www.youtube.com/watch?v=abc123"
  G-17: netloc "youtube.com" not in trusted origins
  → WARN (not BLOCK): "Unverified URL removed: youtube.com"
  → URL excluded from learning path; rest of path delivered
  → st.warning("[G-17] 1 unverified URL was excluded from the learning path.")
```

### Scenario D: Content safety filter

```
background_text contains a blocked keyword
  G-16: heuristic keyword match
  → BLOCK: "[G-16] Background text contains disallowed content."
  → st.stop()
```

---

## Technical Appendix: Session State Schema at Pipeline Completion

```
st.session_state = {
    # Auth
    "logged_in":           True,
    "login_name":          "Alex Chen",
    "user_email":          "alex.chen@demo.com",
    "is_returning":        False,

    # Pipeline outputs
    "raw":                 RawStudentInput,
    "profile":             LearnerProfile,
    "plan":                StudyPlan,
    "learning_path":       LearningPath,
    "guardrail_plan":      GuardrailResult,
    "guardrail_path":      GuardrailResult,

    # HITL Gate 1
    "progress_submitted":  True,
    "progress_snapshot":   ProgressSnapshot,
    "readiness":           ReadinessAssessment,

    # HITL Gate 2
    "quiz_submitted":      True,
    "assessment_result":   AssessmentResult,

    # Cert recommendation
    "cert_recommendation": CertRecommendation,

    # Observability
    "trace":               list_of_AgentSteps,
    "parallel_agent_ms":   4821,
    "mode_badge":          "Mock mode",
}
```

---

## Technical Appendix: Pipeline Exit Points

| Trigger | Guard | Action | Recovery Path |
|---------|-------|--------|---------------|
| `st.stop()` | G-01..G-05 BLOCK | Invalid form input | User corrects form and resubmits |
| `st.stop()` | G-06..G-08 BLOCK | Invalid profiler output | Switch to live mode or report bug |
| `st.stop()` | G-16 BLOCK | Harmful content in background | User rewrites background text |
| `st.warning()` | G-09..G-10 WARN | Plan hours slightly over budget | Pipeline continues with caution banner |
| `st.warning()` | G-17 WARN | Unverified URL in path | URL removed; rest of path delivered |
| Auto-fallback | Azure error | Network / quota / auth failure | Mock profiler used transparently |
