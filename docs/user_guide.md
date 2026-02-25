# User Guide — Certification Prep Multi-Agent System

> Step-by-step walkthrough for learners and admins.
> No technical background required for Sections 1–6.

---

## Getting Started

### First-Time Login

1. Open the app (local: `http://localhost:8501` or live: `agentsleague.streamlit.app`)
2. You land on the **Welcome tab** — the sidebar shows your progress tracker
3. Enter your **Name** and a **4-digit PIN** you'll remember
4. Click **Let's Begin** — your session is created and saved

> **Returning user?** Enter the same name and PIN from your last session. Your study plan and previous results will be restored automatically.

### Demo Personas (for testing)

| Persona | What to use it for |
|---------|-------------------|
| **New Learner** (any name, PIN `1234`) | See the full flow from scratch with no certs |
| **AI Pro** (add AZ-104 + AI-900 in certs field) | See domain boosts and shorter plan |
| **Admin** (username `admin`, password `agents2026`) | View the Admin Dashboard |

---

## Tab-by-Tab Walkthrough

The app starts with an **intake form**. After submitting it, **six output tabs** appear across the top of the page. Complete them in order — some tabs unlock only after earlier ones are filled in.

---

### Intake Form — 📋 Setup

**What it does:** Collects everything the AI profiler needs to build your personalised plan.

**Fields to fill:**
| Field | What to enter | Example |
|-------|--------------|---------|
| Target Exam | The Microsoft certification you're preparing for | `AI-102` |
| Background | Your professional background in 2–3 sentences | "I'm a Python developer with 2 years of REST API experience, new to Azure" |
| Existing Certifications | Any certs you already hold (comma-separated) | `AZ-900, AI-900` |
| Hours per Week | Realistic study hours you can commit | `8` |
| Weeks Available | How many weeks until your exam | `12` |
| Concern Topics | Areas you're unsure about (free text) | "OpenAI, computer vision, managing deployments" |
| Learning Style | How you learn best | Select: Hands-on / Linear / Reference / Mix |

**Tips:**
- Be specific in the Background field — "Python developer with REST APIs" gets a better profile than "software engineer"
- Enter *all* certs you hold, even AI-900 or AZ-900 — each one boosts relevant domain scores
- Concern topics lets the system front-load areas you're weakest in

**Click:** `Create My AI Study Plan` — this runs the profiler and generates your plan.

---

### Tab 1: 📊 Learner Profile

**What it does:** Shows your starting knowledge level for each exam domain as a visual map, plus your PDF download and email buttons.

**Sections on this tab:**
- **Exam Score Contribution** (bar chart): Shows how heavily each domain is weighted on the real exam.
- **Your Confidence per Domain** (bar chart): Initial confidence score from 0–100% based on your background + existing certs.
- **Domain Knowledge Table**: Lists each domain with your `Knowledge Level` (UNKNOWN / WEAK / MODERATE / STRONG) and `Confidence %`.
- **Learning Style Badge**: Your inferred learning style (e.g., LAB_FIRST, LINEAR) and what it means for how resources will be selected.
- **Download PDF Report** / **Email PDF**: Download or send your profile + study plan as a PDF.

**How to read it:**
- Domains with a 🔴 **WEAK** badge are your **risk domains** — the plan will allocate more time here
- Domains with a ✅ **STRONG** badge may have reduced time allocation (you already know this material)
- Compare the weight chart vs confidence chart — a high-weight + low-confidence domain is your biggest risk

---

### Tab 2: 📚 Study Setup

**What it does:** Shows your personalised week-by-week study plan and prerequisite gap check.

**Sections:**
1. **Prerequisite Check** — Lists strongly recommended (⚠️ required) and helpful (💡 optional) prior certifications for your target exam. A red warning banner appears if you're missing strongly-recommended certs.

2. **Study Timeline (Gantt Chart)** — A visual bar chart showing which domains you study in which weeks. Risk domains appear early; review period at the end.

3. **Module Allocation Table** — Each domain with: start week, end week, hours allocated, and priority level (CRITICAL / HIGH / MEDIUM / LOW).

4. **Quick Summary Card** — Total weeks, total hours, number of risk domains, and any prereq gap note.

**How to read the Gantt:**
- Each horizontal bar = one study domain
- Bar position = which weeks you study it
- CRITICAL priority domains appear first (top of chart)
- The final "Review" row is your mock exam prep week

**Tips:**
- If you see a prereq gap warning, consider doing the recommended cert first — it will boost your confidence in multiple domains
- You can change your hours/week input and regenerate the plan from Tab 1

---

### Tab 3: 🛤️ Learning Path

**What it does:** Shows curated learning resources for each domain — mapped to your specific domains and learning style.

**Structure:**
- Each domain has its own expandable section
- Each section contains a list of **MS Learn modules** with: module title, estimated duration, difficulty tag, and a direct link to learn.microsoft.com
- Modules tagged `[LAB]` are hands-on exercises
- Modules tagged `[REFERENCE]` are documentation/conceptual

**Filtering:**
- Domains you already know strongly (`modules_to_skip`) may appear collapsed with a ℹ️ note: "Your profile suggests strong prior knowledge — review optional"
- Risk domains appear expanded by default

---

### Tab 4: 📊 Progress

**What it does:** This is your **first Human-in-the-Loop checkpoint** — you must fill this in honestly for readiness scoring to be meaningful.

**Progress Check-In Form** (fill before your readiness score appears):

| Field | What to enter |
|-------|--------------|
| Hours Studied This Week | How many hours you actually studied (use 0 if you haven't started) |
| Domain Self-Rating | Slide each domain from 1 (very unsure) to 5 (confident) |
| Last Practice Exam Score | Your most recent mock exam percentage (0 if none taken) |

**Click:** `Submit Progress Update`

**After submitting:**
- **Readiness Score** (0–100%): Weighted combination of your domain ratings, hours, and practice score
- **Verdict Banner**: GO ✅ / CONDITIONAL GO 🟡 / NOT YET ❌ with explanation
- **Domain Readiness Grid**: Per-domain mini-bar showing readiness percentage
- **Nudge Messages**: Specific recommendations (e.g., "Spend 2 more hours on Computer Vision before exam")

**Readiness Formula (transparent):**
```
Readiness = 55% × (your domain ratings) + 25% × (hours studied / total budget) + 20% × (practice score)
```

**Tips:**
- Be honest with self-ratings — rating yourself 5/5 on everything when you haven't studied doesn't help you prepare
- if readiness is below 70%, the system shows a remediation plan and suggests specific resources
- Resubmit the form as you study more — readiness updates each time

---

### Tab 5: 🧠 Mock Quiz

**What it does:** This is your **second Human-in-the-Loop checkpoint** — a domain-weighted 30-question practice quiz.

**How it works:**
1. All 30 questions load at once — answer every question (all must be answered before Submit activates)
2. For each question, select one answer (A / B / C / D)
3. Click `Submit Quiz` when all questions are answered

**After submitting:**
- **Score %**: Your percentage correct (weighted by domain)
- **Domain Breakdown**: Which domains you got right vs wrong
- **Answer Review**: Each question with your answer, correct answer, and explanation

The 30 questions are distributed across all exam domains proportionally to real exam weights — this mirrors the actual exam distribution.

---

### Tab 6: 🏆 Certification Advice

**What it does:** Final verdict — next certification path, exam booking checklist, and remediation plan if needed.

**Sections:**
1. **Booking Checklist** (GO path) — Step-by-step Pearson VUE exam registration guide shown when quiz score ≥ 70%
2. **Remediation Plan** (NOT YET path) — Specific domains with resources and estimated additional hours
3. **Next Certification Path** — Recommended cert chain after current exam (e.g., AI-102 → AZ-204)
4. **Verdict Banner** — GO / CONDITIONAL GO / NOT YET with coloured banner and explanation

---

## Admin Dashboard

**Access:** Login with username `admin`, password `agents2026`, then navigate to `Admin Dashboard` in the sidebar.

**What you can see:**

1. **Student Roster** — Table of all students: name, target exam, profile date, plan status, last activity

2. **Agent Execution Gantt** — Select a student run to see a Plotly timeline showing:
   - Each agent as a horizontal bar
   - Length = execution time
   - Colour = status (green=success, red=error, grey=skipped)

3. **Guardrail Violation Log** — All violations across all sessions:
   - Code (G-01 to G-17)
   - Level (BLOCK/WARN/INFO)
   - Message
   - Field that triggered it
   - Student + timestamp

4. **Aggregate Stats** — Average per-agent latency, most frequent guardrail violations, total sessions

---

## FAQ

**Q: Can I change my target exam after starting?**
A: Yes — click **Edit Profile** on the Learner Profile tab, change the exam, and click `Create My AI Study Plan` again. A new profile and plan will be generated. Your previous session data is preserved in the database.

**Q: The system says I'm "NOT YET READY" — what should I do?**
A: The remediation plan in the **Certification Advice** tab (Tab 6) shows exactly which domains need work and links directly to the relevant MS Learn modules. Focus on those domains, then resubmit your progress in Tab 4 to see your readiness update.

**Q: My reading says 0% readiness even though I've studied a lot.**
A: You need to fill in the **Progress Check-In form** in **Tab 4** first. Until you submit real study data, the system doesn't know about your progress.

**Q: How many questions are in the quiz?**
A: The quiz pulls 10 questions from a 30-question bank, proportional to real exam domain weights. This ensures the quiz reflects the actual exam balance.

**Q: Can I retake the quiz?**
A: Yes — click `Reset Quiz` on Tab 5 to clear answers and generate a new sample from the question bank.

**Q: Does the system use AI / ChatGPT?**
A: By default, all profiling and planning runs in **mock mode** — a rule-based system that works without any AI API. If an Azure OpenAI key is configured in settings, the profiler and learning path curator switch to live GPT-4o calls for richer analysis.

**Q: My session data disappeared after closing the browser.**
A: Because your name and PIN were saved to the database, re-enter them on the Welcome tab to restore your plan and progress.

**Q: The Gantt chart shows some domains are skipped — why?**
A: If your profile shows STRONG confidence in a domain (e.g., you hold a cert that covers it), the system marks it as `module_to_skip` and reduces its study time. You can override this by lowering your self-rating in the Progress tab.

---

## Understanding Your Scores

| Score | What It Means |
|-------|--------------|
| Confidence % | Your starting knowledge level for each domain, inferred from your background and certs |
| Readiness % | Current combined score based on study hours, domain ratings, and practice exam |
| Quiz Score % | How well you did on the knowledge check questions |
| Domain Rating | Your own 1–5 self-assessment (1=very weak, 5=confident) |

| Verdict | Readiness Range | Meaning |
|---------|----------------|---------|
| ✅ GO | ≥ 70% | Evidence suggests you're ready — book the exam |
| 🟡 CONDITIONAL GO | 50–69% | Close but not there — targeted review recommended |
| ❌ NOT YET | < 50% | More preparation needed — follow the remediation plan |
