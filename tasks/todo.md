# 📋 Task Plan — Agents League Battle #2

> **Workflow rules enforced by this file:**
> - Any task with > 3 implementation steps must be written here **before** coding starts (Plan Node Default)
> - Only **one** task may be `[IN PROGRESS]` at a time
> - A task is `[DONE]` only when: syntax check passes + behaviour verified + git diff reviewed
> - After every correction, add a row to `tasks/lessons.md`
> - "Do the simplest thing that could possibly work" — no patch-over-patch

---

## 🔴 Sprint — Current (Feb 2026 — Submission)

| # | Task | Status | Notes |
|---|------|--------|-------|
| T-01 | Fix email service reference in `docs/TODO.md` (ACS → SMTP) | ✅ DONE | Section D rewritten; "Should Do" task updated |
| T-02 | Add Responsible AI Considerations section to `README.md` | ✅ DONE | 7-principle table with implementation status + honest gaps |
| T-03 | Replace Starter Kit Compliance with full Submission Requirements Checklist | ✅ DONE | Mandatory + optional + self-improvement governance |
| T-04 | Create `tasks/lessons.md` (self-improvement loop) | ✅ DONE | 4 lessons logged from current session |
| T-05 | Create `tasks/todo.md` (plan-first task management) | ✅ DONE | This file |
| T-06 | Extend Azure AI Foundry SDK to remaining 4 agents | 🔲 NOT STARTED | `StudyPlanAgent`, `LearningPathCuratorAgent`, `AssessmentAgent`, `CertRecommendationAgent` |
| T-07 | Upgrade G-16 content safety from heuristic to Azure Content Safety API | 🔲 NOT STARTED | Stub + env vars already present; needs `AZURE_CONTENT_SAFETY_ENDPOINT/KEY` in `.env` |
| T-08 | Wire MCP MS Learn server into `LearningPathCuratorAgent` | 🔲 NOT STARTED | `MCP_MSLEARN_URL` placeholder in `.env`; needs Node.js MCP sidecar + `httpx` client in agent |
| T-09 | Record demo video (3–5 min): new learner → profile → plan → quiz → recommendation | 🔲 NOT STARTED | Show Admin Dashboard trace + G-16 PII scenario |
| T-10 | Deploy to Streamlit Cloud with `AZURE_CLIENT_ID/SECRET/TENANT_ID` secrets | 🔲 NOT STARTED | `DefaultAzureCredential` picks up service principal from secrets |

---

## 🟡 Backlog — Should Do

| # | Task | Notes |
|---|------|-------|
| B-01 | Foundry Evaluation SDK harness for bias + relevance metrics | Use `azure-ai-evaluation` package; test across 9 cert families |
| B-02 | Azure Monitor / App Insights telemetry | Agent latency, guardrail fire rate, parallel speedup ratio |
| B-03 | Add DP-420, AZ-500, AZ-700 exam domains to registry | Currently 9; extend to 12 |
| B-04 | Adaptive quiz engine with GPT-4o item generation | Replace static question bank with dynamic IRT-based questions |
| B-05 | Upgrade email from SMTP to Azure Communication Services | `azure-communication-email` SDK; ACS resource + sender domain |

---

## 🟢 Backlog — Nice to Have

| # | Task | Notes |
|---|------|-------|
| N-01 | Persistent Cosmos DB storage (replace SQLite) | Cross-session learner profiles; multi-device sync |
| N-02 | Azure AI Search for live MS Learn module discovery | Semantic vector search across ~4,000 modules |
| N-03 | Enterprise LMS export (LTI/xAPI) | Cornerstone, SAP SuccessFactors integration |
| N-04 | Multimodal input — PDF CV → profiler | Azure Document Intelligence → profile enrichment |
| N-05 | Multi-language support | Azure OpenAI Whisper + Azure AI Translator |

---

## ✅ Completed Tasks (Archive)

| Task | Commit | Date |
|------|--------|------|
| Project scaffolding + folder structure | initial | 2026 |
| Mock profiler (rule-based, zero Azure) | — | 2026 |
| Streamlit UI with 7 tabs + login gate | — | 2026 |
| 8 agents implemented (mock + live fallback) | — | 2026 |
| 17-rule GuardrailsPipeline (G-01..G-17) | — | 2026 |
| Agent trace logging + Admin Dashboard | — | 2026 |
| Glassmorphism login page + sidebar cards | — | 2026 |
| `.env` / `.env.example` / `config.py` scaffolding | — | 2026 |
| Dev Approach + Reasoning Patterns docs | `5fe246f` | 2026-02-24 |
| SMTP email clarification (`.env.example` + README) | `5745863` | 2026-02-24 |
| `azure-ai-projects` Foundry SDK integration (`LearnerProfilingAgent` 3-tier) | `9895ef2` | 2026-02-24 |
| Admin Dashboard per-agent HTML rendering fix | *(latest)* | 2026-02-24 |
| Responsible AI section + Submission Requirements checklist | *(this session)* | 2026-02-24 |

---

## 🔬 Verification Checklist (run before any commit)

```powershell
# 1. Syntax check
& "D:/OneDrive/Athiq/MSFT/Agents League/.venv/Scripts/python.exe" -m py_compile streamlit_app.py
& "D:/OneDrive/Athiq/MSFT/Agents League/.venv/Scripts/python.exe" -m py_compile src/cert_prep/b0_intake_agent.py

# 2. Unit tests
& "D:/OneDrive/Athiq/MSFT/Agents League/.venv/Scripts/python.exe" -m pytest tests/ -x -q

# 3. Kill port + launch to verify no runtime crash
$p = (netstat -ano | Select-String "0.0.0.0:8501 " | ForEach-Object { ($_ -split '\s+')[-1] } | Select-Object -First 1)
if ($p) { taskkill /PID $p /F }
& "D:/OneDrive/Athiq/MSFT/Agents League/.venv/Scripts/python.exe" -m streamlit run streamlit_app.py

# 4. Git diff review
git diff --stat HEAD
```
