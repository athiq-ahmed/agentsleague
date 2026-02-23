"""
Block 1: Learner Intake & Profiling
====================================
Two agents that together form the first block of the Certification Prep pipeline.

LearnerIntakeAgent
    Collects raw student input via an interactive CLI interview (7 questions).
    Returns: RawStudentInput

LearnerProfilingAgent
    Sends the raw input to Azure OpenAI and extracts a structured LearnerProfile.
    Uses JSON-mode with a schema-anchored system prompt so the output is
    deterministic and directly parseable.
    Returns: LearnerProfile
"""

from __future__ import annotations

import json
import textwrap
from typing import Any

from openai import AzureOpenAI
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, FloatPrompt, Confirm
from rich.table import Table
from rich import box

from cert_prep.config import get_config, AzureOpenAIConfig
from cert_prep.models import (
    EXAM_DOMAINS,
    DomainKnowledge,
    ExperienceLevel,
    LearnerProfile,
    LearningStyle,
    RawStudentInput,
)

console = Console()


# ─────────────────────────────────────────────────────────────────────────────
# AGENT 1 – Learner Intake (CLI interview)
# ─────────────────────────────────────────────────────────────────────────────

class LearnerIntakeAgent:
    """
    Conducts a guided 7-question interview with the student and returns a
    RawStudentInput dataclass.  All input is collected via Rich prompts so
    the CLI feels polished.
    """

    BANNER = "[bold magenta]Microsoft Certification Prep — Learner Intake[/bold magenta]"

    def run(self) -> RawStudentInput:
        console.print()
        console.print(Panel(self.BANNER, subtitle="Answer a few questions to personalise your plan", expand=False))
        console.print()

        # Q1 – Name
        student_name = Prompt.ask("[cyan]1.[/cyan] Your name")

        # Q2 – Target exam (default AI-102)
        exam_target = Prompt.ask(
            "[cyan]2.[/cyan] Which exam are you preparing for?",
            default="AI-102",
        )

        # Q3 – Background / experience
        console.print(
            "[cyan]3.[/cyan] Briefly describe your background "
            "[dim](e.g. job role, years of experience, tools you know)[/dim]:"
        )
        background_text = Prompt.ask("   >")

        # Q4 – Existing certifications
        certs_raw = Prompt.ask(
            "[cyan]4.[/cyan] List any Azure/Microsoft certifications you already hold "
            "[dim](comma-separated, or leave blank)[/dim]",
            default="",
        )
        existing_certs = [c.strip() for c in certs_raw.split(",") if c.strip()]

        # Q5 – Time budget
        hours_per_week = FloatPrompt.ask(
            "[cyan]5.[/cyan] How many hours per week can you study?",
            default=10.0,
        )
        weeks_available = IntPrompt.ask(
            "       How many weeks do you have until your exam?",
            default=8,
        )

        # Q6 – Topics of concern
        concerns_raw = Prompt.ask(
            "[cyan]6.[/cyan] Which topics worry you most? "
            "[dim](comma-separated, e.g. Azure OpenAI, Bot Service)[/dim]",
            default="",
        )
        concern_topics = [t.strip() for t in concerns_raw.split(",") if t.strip()]

        # Q7 – Learning preferences
        console.print(
            "[cyan]7.[/cyan] How do you prefer to learn? "
            "[dim](e.g. hands-on labs first, structured reading, quick reference cards)[/dim]:"
        )
        preferred_style = Prompt.ask("   >")

        # Q8 – Goal
        console.print("[cyan]8.[/cyan] Why do you want this certification?")
        goal_text = Prompt.ask("   >")

        result = RawStudentInput(
            student_name=student_name,
            exam_target=exam_target,
            background_text=background_text,
            existing_certs=existing_certs,
            hours_per_week=hours_per_week,
            weeks_available=weeks_available,
            concern_topics=concern_topics,
            preferred_style=preferred_style,
            goal_text=goal_text,
        )

        console.print()
        console.print("[bold green]✓ Intake complete.[/bold green] Sending to profiling agent…")
        console.print()
        return result


# ─────────────────────────────────────────────────────────────────────────────
# AGENT 2 – Learner Profiling (LLM-powered)
# ─────────────────────────────────────────────────────────────────────────────

# The exact JSON schema we expect back from the LLM.
# Keeping this in one place makes prompt engineering maintainable.
_PROFILE_JSON_SCHEMA = {
    "student_name": "string",
    "exam_target":  "string",
    "experience_level": "beginner | intermediate | advanced_azure | expert_ml",
    "learning_style": "linear | lab_first | reference | adaptive",
    "hours_per_week": "number",
    "weeks_available": "integer",
    "total_budget_hours": "number",
    "domain_profiles": [
        {
            "domain_id":        "plan_manage | computer_vision | nlp | document_intelligence | conversational_ai | generative_ai",
            "domain_name":      "string",
            "knowledge_level":  "unknown | weak | moderate | strong",
            "confidence_score": "float 0.0-1.0",
            "skip_recommended": "boolean",
            "notes":            "string (1-2 sentences)",
        }
    ],
    "modules_to_skip": ["string"],
    "risk_domains":    ["string (domain_id)"],
    "analogy_map":     {"existing skill": "Azure AI equivalent"},
    "recommended_approach": "string (2-3 sentences)",
    "engagement_notes":     "string",
}

_DOMAIN_REF = json.dumps(
    [
        {
            "id":          d["id"],
            "name":        d["name"],
            "exam_weight": f"{int(d['weight'] * 100)} %",
            "covers":      d["description"],
        }
        for d in EXAM_DOMAINS
    ],
    indent=2,
)

_PROFILE_SCHEMA_STR = json.dumps(_PROFILE_JSON_SCHEMA, indent=2)

_SYSTEM_PROMPT = textwrap.dedent("""
    You are an expert Microsoft certification coach.

    Your task is to analyse a student's background and produce a structured
    learner profile that will personalise their study plan.

    ## Exam Domain Reference
""") + _DOMAIN_REF + textwrap.dedent("""

    ## Personalisation Rules
    1. If the student holds AZ-104 or AZ-305, mark plan_manage as STRONG / skip_recommended=true.
    2. If they have a data science / ML background, mark generative_ai as MODERATE.
    3. If they explicitly mention worry about a topic, mark its domain as WEAK unless
       their background clearly contradicts that.
    4. total_budget_hours = hours_per_week × weeks_available.
    5. risk_domains = domains where confidence_score < 0.50.
    6. analogy_map: only populate if the student has non-Azure skills that map to
       Azure AI services (e.g. "scikit-learn pipeline" → "Azure ML Pipeline").
    7. experience_level: beginner = no Azure; intermediate = some Azure services;
       advanced_azure = infra certs (AZ-104/305); expert_ml = DS/ML certs (DP-100/AI-900).

    ## Output
    Respond with ONLY a valid JSON object matching this schema exactly:
""") + _PROFILE_SCHEMA_STR + "\n\nDo NOT include any explanation, markdown, or extra text outside the JSON."


class LearnerProfilingAgent:
    """
    Sends RawStudentInput to Azure OpenAI and returns a validated LearnerProfile.

    The LLM is instructed to return strict JSON matching _PROFILE_JSON_SCHEMA.
    Pydantic validates and coerces the response so callers always get a typed object.
    """

    def __init__(self, config: AzureOpenAIConfig | None = None) -> None:
        self._cfg = config or get_config()
        self._client = AzureOpenAI(
            azure_endpoint=self._cfg.endpoint,
            api_key=self._cfg.api_key,
            api_version=self._cfg.api_version,
        )

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _build_user_message(self, raw: RawStudentInput) -> str:
        certs = ", ".join(raw.existing_certs) if raw.existing_certs else "None"
        concerns = ", ".join(raw.concern_topics) if raw.concern_topics else "None stated"
        return textwrap.dedent(f"""
            Student: {raw.student_name}
            Exam: {raw.exam_target}
            Background: {raw.background_text}
            Existing certifications: {certs}
            Time budget: {raw.hours_per_week} hours/week for {raw.weeks_available} weeks
            Topics of concern: {concerns}
            Learning preference: {raw.preferred_style}
            Goal: {raw.goal_text}

            Please produce the learner profile JSON.
        """).strip()

    def _call_llm(self, user_message: str) -> dict[str, Any]:
        with console.status("[bold blue]Profiling agent: analysing background with Azure OpenAI…"):
            response = self._client.chat.completions.create(
                model=self._cfg.deployment,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system",  "content": _SYSTEM_PROMPT},
                    {"role": "user",    "content": user_message},
                ],
                temperature=0.2,   # low for deterministic structured output
                max_tokens=2000,
            )
        raw_json = response.choices[0].message.content
        return json.loads(raw_json)

    # ── Public interface ──────────────────────────────────────────────────────

    def run(self, raw: RawStudentInput) -> LearnerProfile:
        """
        Profile the student and return a validated LearnerProfile.

        Raises:
            EnvironmentError  – Azure OpenAI credentials not configured.
            ValidationError   – LLM returned JSON that doesn't match the schema.
            json.JSONDecodeError – LLM response was not valid JSON (rare with json_object mode).
        """
        user_msg = self._build_user_message(raw)
        data = self._call_llm(user_msg)

        # Patch passthrough fields that the LLM might not echo exactly
        data.setdefault("student_name", raw.student_name)
        data.setdefault("exam_target", raw.exam_target)
        data.setdefault("hours_per_week", raw.hours_per_week)
        data.setdefault("weeks_available", raw.weeks_available)
        data.setdefault(
            "total_budget_hours",
            raw.hours_per_week * raw.weeks_available,
        )

        profile = LearnerProfile.model_validate(data)
        console.print("[bold green]✓ Profiling complete.[/bold green]")
        return profile


# ─────────────────────────────────────────────────────────────────────────────
# Convenience: run both agents as a single pipeline step
# ─────────────────────────────────────────────────────────────────────────────

def run_intake_and_profiling(
    config: AzureOpenAIConfig | None = None,
) -> tuple[RawStudentInput, LearnerProfile]:
    """
    Full Block 1 pipeline:
      1. LearnerIntakeAgent  → RawStudentInput
      2. LearnerProfilingAgent → LearnerProfile

    Returns both so callers have the raw input for auditing.
    """
    raw     = LearnerIntakeAgent().run()
    profile = LearnerProfilingAgent(config).run(raw)
    return raw, profile
