# 📋 Project TODO — Agents League Battle #2

> **Owner:** Athiq Ahmed  
> **Project:** Microsoft Certification Prep Multi-Agent System  
> **Track:** Reasoning Agents with Microsoft Foundry  
> **Subscription:** Pay-As-You-Go (recommended) or MSDN/Visual Studio  
> **Last updated:** 2026-02-22

---

## 1️⃣ Azure Services to Enable

### A. Azure OpenAI Service ⭐ (Primary — powers all agents)

| Setting | Value |
|---------|-------|
| **Resource Group** | `rg-agentsleague` |
| **Region** | `East US 2` or `Sweden Central` (best GPT-4o availability) |
| **Pricing tier** | `S0` (Standard) |
| **Model to deploy** | `gpt-4o` (version `2024-11-20` or latest) |
| **Deployment name** | `gpt-4o` |
| **TPM quota** | Request at least `30K` tokens/min |

**How to set up:**
1. Portal → **Create a resource** → search "Azure OpenAI" → **Create**
2. Pick `rg-agentsleague`, region, name (e.g. `aoai-agentsleague`)
3. After deployment → **Keys and Endpoint** blade → copy:
   - `AZURE_OPENAI_ENDPOINT` (e.g. `https://aoai-agentsleague.openai.azure.com`)
   - `AZURE_OPENAI_API_KEY` (Key 1)
4. **Model deployments** → **Create new deployment**:
   - Model: `gpt-4o`, Deployment name: `gpt-4o`, TPM: `30K`
5. Paste into `.env`:
   ```
   AZURE_OPENAI_ENDPOINT=https://aoai-agentsleague.openai.azure.com
   AZURE_OPENAI_API_KEY=<your-key>
   AZURE_OPENAI_DEPLOYMENT=gpt-4o
   AZURE_OPENAI_API_VERSION=2024-12-01-preview
   ```
6. Test: `.venv\Scripts\python.exe -c "from src.cert_prep.config import get_config; c=get_config(); print(c)"`

- [ ] Resource created
- [ ] Model deployed
- [ ] `.env` updated & tested

---

### B. Azure AI Foundry (Agent orchestration + evaluation)

| Setting | Value |
|---------|-------|
| **Hub name** | `hub-agentsleague` |
| **Project name** | `certprep-agents` |
| **Region** | Same as OpenAI resource |
| **Connected service** | Link your Azure OpenAI resource |

**How to set up:**
1. Go to [ai.azure.com](https://ai.azure.com) → **Create project**
2. Create or select a Hub → name the project `certprep-agents`
3. Under **Connected resources** → attach your Azure OpenAI resource
4. **Settings** → copy the **Project Connection String**
5. Add to `.env`:
   ```
   AZURE_AI_PROJECT_CONNECTION_STRING=<your-connection-string>
   ```
6. Install SDK: `pip install azure-ai-projects azure-ai-agents`

- [ ] Hub + Project created
- [ ] OpenAI resource connected
- [ ] Connection string in `.env`
- [ ] SDK installed

---

### C. Azure AI Content Safety (Responsible AI guardrails)

| Setting | Value |
|---------|-------|
| **Resource name** | `aics-agentsleague` |
| **Region** | `East US` or `West Europe` |
| **Pricing tier** | `F0` (Free — 5K transactions/month) or `S0` |

**How to set up:**
1. Portal → **Create a resource** → "Content Safety" → **Create**
2. Copy endpoint + key
3. Add to `.env`:
   ```
   AZURE_CONTENT_SAFETY_ENDPOINT=https://aics-agentsleague.cognitiveservices.azure.com
   AZURE_CONTENT_SAFETY_KEY=<key>
   ```
4. Used by `guardrails.py` for PII filtering and content moderation

- [ ] Resource created
- [ ] Integrated into guardrails pipeline

---

### D. Azure Communication Services (Optional — weekly email nudges)

| Setting | Value |
|---------|-------|
| **Resource name** | `acs-agentsleague` |
| **Pricing** | Pay-per-message (first 100 emails free) |

**How to set up:**
1. Portal → **Create a resource** → "Communication Services" → **Create**
2. **Email** → **Provision domains** → use Azure-managed domain (`*.azurecomm.net`)
3. Copy connection string → `.env`:
   ```
   AZURE_COMM_CONNECTION_STRING=<connection-string>
   AZURE_COMM_SENDER_EMAIL=DoNotReply@<guid>.azurecomm.net
   ```
4. Used by `progress_agent.py` → `attempt_send_email()` for weekly summaries

- [ ] Resource created (optional — app works without it)

---

### E. Microsoft Learn MCP Server (Tool use — real learning paths)

**No Azure resource needed** — runs locally as a sidecar process.

**How to set up:**
1. `npm install -g @microsoftdocs/mcp` (requires Node.js 18+)
2. Or clone: `git clone https://github.com/microsoftdocs/mcp`
3. Start server: `npx @microsoftdocs/mcp`
4. Add to `.env`:
   ```
   MCP_MSLEARN_URL=http://localhost:3001
   ```
5. Used by `learning_path_curator.py` to fetch real MS Learn modules + exam blueprints

- [ ] Node.js 18+ installed
- [ ] MCP server running
- [ ] Integrated into Learning Path Curator agent

---

## 2️⃣ Development Tasks

### 🔴 Must Do (Before Submission)

- [ ] **Wire agents to Azure OpenAI** — switch from mock → live for:
  - `intake_agent.py` — LLM-based learner profiling
  - `study_plan_agent.py` — LLM-generated personalised study plans
  - `learning_path_curator.py` — LLM-curated MS Learn modules
  - `assessment_agent.py` — LLM-generated exam-style quiz questions
  - `cert_recommendation_agent.py` — LLM-powered certification path suggestions
- [ ] **Multi-agent orchestration in Foundry**
  - Define agent pipeline: Intake → Profiling → Learning Path → Study Plan → Assessment → Progress
  - Add human-in-the-loop confirmation at readiness gate
- [ ] **Evaluation harness**
  - Add Foundry's built-in evaluation for each agent
  - Track: latency, token usage, answer relevance, factual accuracy
  - Create rubric for grading agent reasoning quality

### 🟡 Should Do (Strengthens Submission)

- [ ] **MCP integration** — real MS Learn content instead of static mock data
- [ ] **Content Safety** — wire guardrails to Azure AI Content Safety API
- [ ] **Email engagement** — wire `attempt_send_email()` to Azure Communication Services
- [ ] **Record demo video** (3–5 min) showing:
  - New learner flow → profile generation → study plan → quiz
  - Returning learner → progress tracking → readiness assessment
  - Admin dashboard → agent trace inspection

### 🟢 Nice to Have

- [ ] Add more exam domain blueprints (DP-100, AZ-204, AZ-305) to `EXAM_DOMAIN_REGISTRY`
- [ ] Persistent storage (Cosmos DB or SQLite) for learner profiles across sessions
- [ ] Deploy to Azure App Service or Container Apps
- [ ] Add Bing Grounding for up-to-date exam change announcements

---

## 3️⃣ Cost Estimate (Monthly)

| Service | Tier | Est. Cost |
|---------|------|-----------|
| Azure OpenAI (gpt-4o) | S0, ~50K tokens/day dev usage | ~$5–15/mo |
| AI Foundry | Free tier for project mgmt | $0 |
| Content Safety | F0 free tier | $0 |
| Communication Services | <100 emails | $0 |
| **Total dev/test** | | **~$5–15/mo** |

> 💡 **Tip:** Set a **budget alert** at $20 in Cost Management to avoid surprises.

---

## ✅ Completed

- [x] Project scaffolding & folder structure
- [x] Mock profiler (rule-based inference — works without Azure)
- [x] Streamlit UI with 7 tabs (conditional by user type)
- [x] Study Plan Agent (mock, rule-based)
- [x] Learning Path Curator Agent (mock)
- [x] Assessment Agent (mock quiz generation + scoring)
- [x] Certification Recommendation Agent (mock)
- [x] Progress Agent with readiness assessment + email summary
- [x] Guardrails pipeline (17 rules: G-01 to G-17 — PII filter, anti-cheat, content safety, URL trust)
- [x] Agent trace logging & Admin Dashboard
- [x] Login gate with glassmorphism design (new / existing / admin)
- [x] Tab visibility based on user type
- [x] Genericized naming — supports any Microsoft cert exam
- [x] `.gitignore` updated per starter kit guidelines
- [x] GitHub repo: [athiq-ahmed/agentsleague](https://github.com/athiq-ahmed/agentsleague)
- [x] Creative login page (glassmorphism + gradient design)
- [x] Folder cleanup + archive of old planning files
- [x] Agent orchestration patterns documented (Sequential Pipeline, Typed Handoff, HITL Gates, Conditional Routing)
- [x] Judge playbook created (`docs/judge_playbook.md`)
- [x] Guardrails documented across README, architecture, and judge playbook

---

## 📝 Quick Reference

| Item | Value |
|------|-------|
| Student PIN | `1234` |
| Admin username | `admin` |
| Admin password | `agents2026` |
| GitHub repo | `athiq-ahmed/agentsleague` |
| Python venv | `.venv\Scripts\python.exe` |
| Run app | `streamlit run streamlit_app.py` |
| Mock mode | Works without any Azure credentials |
| Resource group | `rg-agentsleague` (create this first) |
