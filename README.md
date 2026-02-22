# Agents League – Certification Prep MVP

This project implements an MVP multi-agent system for Microsoft certification prep:

1. Learner intake and profiling
2. Preparation orchestration with sub-agents
3. Assessment generation + critic/verifier gate
4. Gap analysis + readiness decision
5. Remediation/replan loop

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .
python -m cert_prep.demo_cli
```

## Notes

- Current MVP runs fully local with deterministic heuristics.
- Designed for easy replacement with LLM/tool-backed agents later.
- Sample scenario uses AI-102 style domains.
