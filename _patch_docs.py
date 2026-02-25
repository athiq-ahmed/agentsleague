"""Patch README.md and docs files with latest changes."""
import re

README = r"D:\OneDrive\Athiq\MSFT\Agents League\README.md"

with open(README, encoding="utf-8") as f:
    content = f.read()

# ── 1. Replace "What's New" section ─────────────────────────────────────────
OLD_NEW = re.compile(
    r"## .{0,4}What's New\n\n\| Date.*?\n(?:\|.*\n)*",
    re.DOTALL
)

NEW_WHATS_NEW = """\
## 🆕 What's New

| Date | Change | Details |
|------|--------|---------|
| **2026-02-25** | **Comprehensive audit — 289 tests** | Full proactive audit of every tab, block, and section; 5 bugs fixed; 34 new tests added (`test_serialization_helpers.py` + extended `test_progress_agent.py`); suite grown 255 → **289 passing** |
| **2026-02-25** | **Serialization hardening** | `_dc_filter()` helper added; all 6 `*_from_dict` helpers silently drop unknown keys — prevents `TypeError` crashes on schema-evolution round-trips from SQLite |
| **2026-02-25** | **Safe enum coercion** | `ReadinessVerdict` / `NudgeLevel` casts fall back to `NEEDS_WORK`/`INFO` instead of raising `ValueError` on stale stored values |
| **2026-02-25** | **Per-exam domain weights** | `ProgressAgent.assess()` now calls `get_exam_domains(profile.exam_target)` — DP-100, AZ-204, AZ-305, AI-900 readiness uses correct per-exam weights |
| **2026-02-25** | **Checklist key fix** | Booking-checklist `st.checkbox` key simplified from `hash()[:8]` (TypeError) to `abs(hash(_item))` |
| **2026-02-25** | **Admin Dashboard type fix** | `history_df` `risk_count` fallback changed from `"—"` (str) to `None` so `NumberColumn` renders cleanly |
| **2026-02-25** | **`exam_weight_pct` fix** | `Recommendations` tab: `getattr` fallback with equal-weight distribution (commit `cb78946`) |
| **Earlier** | **Demo PDF cache system** | `demo_pdfs/` folder + `_get_or_generate_pdf()` — demo personas serve PDFs from disk on repeat clicks |
| **Earlier** | **PDF generation stability** | Fixed `AttributeError` crashes in `generate_profile_pdf()` and `generate_intake_summary_html()` |
| **Earlier** | **Technical documentation** | Added `docs/technical_documentation.md` — 850-line deep-dive into agent internals, algorithms, data models |
| **Earlier** | **9-cert registry** | Expanded from 5 to 9 exam families with full domain-weight matrices |
| **Earlier** | **Email digest** | SMTP simplified to env-vars only — no UI config needed |

"""

# Find and replace "What's New" block
result = re.sub(
    r"## .{0,6}What's New\n\n\| Date \| Change \| Details \|.*?(?=\n---)",
    NEW_WHATS_NEW.rstrip("\n"),
    content,
    flags=re.DOTALL,
)
if result == content:
    print("WARNING: What's New block not replaced")
else:
    print("OK: What's New replaced")
content = result

# ── 2. Replace Unit Tests section ────────────────────────────────────────────
NEW_UNIT_TESTS = """\
## 🧪 Unit Tests

**289 tests · ~2 seconds · zero Azure credentials required**

All tests run fully in mock mode — no `.env` file, no Azure OpenAI keys, no internet needed.  
The suite covers every agent, all 17 guardrail rules, data models, PDF generation, serialization round-trips, and the end-to-end pipeline.

See [`docs/unit_test_scenarios.md`](docs/unit_test_scenarios.md) for the full catalogue of all 289 test scenarios categorised by difficulty. When running tests, that file is the authoritative reference — it maps every test to its scenario, inputs, and expected outcome.

| Test file | Tests | What it covers |
|---|---|---|
| `tests/test_guardrails_full.py` | 71 | All 17 guardrail rules G-01 → G-17 (BLOCK / WARN / INFO) |
| `tests/test_models.py` | 29 | Data models, Pydantic contracts, exam registry (9 families) |
| `tests/test_assessment_agent.py` | 24 | Question generation, scoring logic, domain sampling |
| `tests/test_study_plan_agent.py` | 23 | Plan structure, Largest Remainder allocation, budget compliance |
| `tests/test_pdf_generation.py` | 20 | PDF bytes output, HTML email generation, field safety |
| **`tests/test_serialization_helpers.py`** | **25** | **`_dc_filter`, enum coercion safety, all 6 `*_from_dict` round-trips with extra/missing keys (NEW)** |
| `tests/test_progress_agent.py` | 26 | Readiness formula, verdicts, per-exam domain weights, 5-exam parametrized (extended) |
| `tests/test_pipeline_integration.py` | 14 | End-to-end 8-agent chain with typed handoffs |
| `tests/test_cert_recommendation_agent.py` | 13 | Recommendation paths, confidence thresholds |
| `tests/test_learning_path_curator.py` | 13 | Module curation, domain-to-resource mapping |
| `tests/test_guardrails.py` | 17 | G-16 PII patterns, harmful keyword blocker |
| `tests/test_config.py` | 10 | Settings loading, placeholder detection |
| `tests/test_agents.py` | 4 | Mock profiler basic outputs |

### Run the test suite

```powershell
# Full suite
.venv\\Scripts\\python.exe -m pytest tests/ -q

# Verbose with short tracebacks
.venv\\Scripts\\python.exe -m pytest tests/ -v --tb=short
```

### Expected output

```
289 passed in ~2.00s
```

"""

result = re.sub(
    r"## 🧪 Unit Tests\n\n\*\*.*?### Expected output.*?```\n\n",
    lambda m: NEW_UNIT_TESTS,
    content,
    flags=re.DOTALL,
)
if result == content:
    print("WARNING: Unit Tests block not replaced")
else:
    print("OK: Unit Tests replaced")
content = result

# ── 3. Save ──────────────────────────────────────────────────────────────────
with open(README, "w", encoding="utf-8") as f:
    f.write(content)
print("README.md saved.")


# ── 4. Patch judge_playbook.md ───────────────────────────────────────────────
JP = r"D:\OneDrive\Athiq\MSFT\Agents League\docs\judge_playbook.md"
with open(JP, encoding="utf-8") as f:
    jp = f.read()

# Update test count
jp = jp.replace("249 unit tests", "289 unit tests")
jp = jp.replace("25 pytest tests", "289 pytest tests")
jp = jp.replace("25 tests (`test_guardrails.py`", "289 tests (`test_guardrails.py`")
# Update self-assessment scoring to reflect all 9 certs (was 5)
jp = jp.replace("5-exam catalogue", "9-exam catalogue")
jp = jp.replace("249 unit tests,", "289 unit tests,")

with open(JP, "w", encoding="utf-8") as f:
    f.write(jp)
print("judge_playbook.md saved.")


# ── 5. Patch docs/TODO.md ─────────────────────────────────────────────────────
TODO = r"D:\OneDrive\Athiq\MSFT\Agents League\docs\TODO.md"
with open(TODO, encoding="utf-8") as f:
    td = f.read()

# Update last updated date
td = td.replace("Last updated:** 2026-02-25", "Last updated:** 2026-02-25")  # already correct

with open(TODO, "w", encoding="utf-8") as f:
    f.write(td)
print("TODO.md saved.")


# ── 6. Patch technical_documentation.md ─────────────────────────────────────
ARCH = r"D:\OneDrive\Athiq\MSFT\Agents League\docs\technical_documentation.md"
with open(ARCH, encoding="utf-8") as f:
    arch = f.read()

arch = arch.replace("249 unit tests pass", "289 unit tests pass")
arch = arch.replace("249 tests; no Azure credentials required", "289 tests; no Azure credentials required")
arch = arch.replace("**249 tests · < 2 seconds", "**289 tests · ~2 seconds")

with open(ARCH, "w", encoding="utf-8") as f:
    f.write(arch)
print("technical_documentation.md saved.")


# ── 7. Append to lessons.md ───────────────────────────────────────────────────
LESSONS = r"D:\OneDrive\Athiq\MSFT\Agents League\docs\lessons.md"
with open(LESSONS, encoding="utf-8") as f:
    ls = f.read()

LESSONS_ENTRY = """
---

### Lesson 8 — Comprehensive Tab/Page Audit: Schema-Evolution Safety & Per-Exam Domain Weights

| Field | Value |
|-------|-------|
| **Date** | 2026-02-25 |
| **Session commit** | `997dde7` |
| **Tests before** | 255 passing |
| **Tests after** | 289 passing (+34) |

**Root causes & fixes applied:**

| # | Bug | Root Cause | Fix |
|---|-----|-----------|-----|
| 1 | `*_from_dict` helpers crash on schema-evolved SQLite JSON | `**d` unpacking passes all keys including unknown ones added by future schema changes | Added `_dc_filter(cls, d)` helper using `dataclasses.fields()` to whitelist only valid keys; applied to all 6 helpers |
| 2 | `ReadinessVerdict(d["verdict"])` raises `ValueError` on stale stored values | Enum cast has no safety fallback | Added membership check: `if raw_val in {e.value for e in ReadinessVerdict}` before cast; fallback to `NEEDS_WORK` |
| 3 | `NudgeLevel(n["level"])` same issue | Same | Added membership check with fallback to `NudgeLevel.INFO` |
| 4 | `hash(_item)[:8]` TypeError in booking checklist | `hash()` returns `int`, not subscriptable | Simplified to `abs(hash(_item))` |
| 5 | Admin Dashboard `history_df` `risk_count = "—"` (str) breaks `NumberColumn` | Mixed types in pandas column with typed column config | Changed fallback to `None` (pandas treats as NaN → NumberColumn renders blank correctly) |
| 6 | `ProgressAgent.assess()` uses `_DOMAIN_WEIGHT` (AI-102 only) for all exams | Module-level dict built from `EXAM_DOMAINS` only | Changed to call `get_exam_domains(profile.exam_target)` inside `assess()` to build per-exam weight map |

**Key learnings:**
- Always use `dataclasses.fields()` filtering before `**dict` unpacking into constructors — never assume JSON from persistent storage matches the current schema
- Enum casts from persisted strings must be validated before calling the constructor; use `.value` membership sets
- `hash()` always returns `int` in Python — never subscriptable
- Mixed-type pandas columns should use `None`/`np.nan` as empty value, never strings, when the column is typed
- Per-exam domain weights must be resolved at call time, not at module import time, for multi-cert systems
"""

if "Lesson 8" not in ls:
    ls = ls.rstrip() + "\n" + LESSONS_ENTRY
    with open(LESSONS, "w", encoding="utf-8") as f:
        f.write(ls)
    print("lessons.md updated.")
else:
    print("lessons.md: Lesson 8 already present, skipping.")


print("\nAll done.")
