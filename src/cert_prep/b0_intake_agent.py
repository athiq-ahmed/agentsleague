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

from cert_prep.config import get_config, get_settings, AzureOpenAIConfig
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
    Sends RawStudentInput to an LLM and returns a validated LearnerProfile.

    Three-tier execution strategy (chooses the highest available tier):
      1. Azure AI Foundry Agent Service SDK  — when AZURE_AI_PROJECT_CONNECTION_STRING is set
         Uses AIProjectClient to create a managed Foundry agent, thread, and run.
      2. Direct Azure OpenAI                 — when AZURE_OPENAI_ENDPOINT + KEY are set
         Uses AzureOpenAI client with JSON-mode completions (original approach).
      3. Raise EnvironmentError              — neither configured (caller falls back to mock).

    The output contract is identical across all tiers: a validated LearnerProfile.
    """

    def __init__(self, config: AzureOpenAIConfig | None = None) -> None:
        self._cfg      = config or get_config()
        self._settings = get_settings()

        # ── Tier 1 — Azure AI Foundry Agent Service SDK ──────────────────────
        self._foundry_client = None
        self.using_foundry   = False

        if self._settings.foundry.is_configured:
            try:
                from azure.ai.projects import AIProjectClient  # type: ignore
                from azure.identity import DefaultAzureCredential  # type: ignore
                self._foundry_client = AIProjectClient.from_connection_string(
                    conn_str=self._settings.foundry.connection_string,
                    credential=DefaultAzureCredential(),
                )
                self.using_foundry = True
            except Exception as _fe:
                console.print(
                    f"[yellow]⚠ Foundry SDK init failed ({_fe}); "
                    "falling back to direct OpenAI.[/yellow]"
                )

        # ── Tier 2 — Direct Azure OpenAI ─────────────────────────────────────
        self._openai_client = None
        if self._cfg.is_configured:
            self._openai_client = AzureOpenAI(
                azure_endpoint=self._cfg.endpoint,
                api_key=self._cfg.api_key,
                api_version=self._cfg.api_version,
            )

    # ── Routing ──────────────────────────────────────────────────────────────

    def _call_llm(self, user_message: str) -> dict[str, Any]:
        """Dispatch to highest available tier."""
        if self.using_foundry and self._foundry_client is not None:
            return self._call_via_foundry(user_message)
        if self._openai_client is not None:
            return self._call_via_openai(user_message)
        raise EnvironmentError(
            "Neither Azure AI Foundry nor Azure OpenAI is configured. "
            "Set AZURE_AI_PROJECT_CONNECTION_STRING (Foundry) or "
            "AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_API_KEY (direct)."
        )

    # ── Tier 1 implementation ─────────────────────────────────────────────────

    def _call_via_foundry(self, user_message: str) -> dict[str, Any]:
        """
        Create a managed Azure AI Foundry agent, run it on a new thread,
        extract the assistant reply, then clean up.

        Uses azure-ai-projects AIProjectClient — the official Foundry Agent Service SDK.
        """
        client = self._foundry_client
        agent  = client.agents.create_agent(
            model=self._cfg.deployment,
            name="LearnerProfilerAgent",
            instructions=_SYSTEM_PROMPT,
        )
        try:
            thread = client.agents.create_thread()
            client.agents.create_message(
                thread_id=thread.id,
                role="user",
                content=user_message,
            )
            # create_and_process_run polls until the run completes
            run = client.agents.create_and_process_run(
                thread_id=thread.id,
                agent_id=agent.id,
            )
            if run.status == "failed":
                raise RuntimeError(
                    f"Foundry agent run failed: {run.last_error}"
                )
            messages  = client.agents.list_messages(thread_id=thread.id)
            last_msg  = messages.get_last_message_by_role("assistant")
            text      = last_msg.content[0].text.value
            return json.loads(text)
        finally:
            # Always clean up the ephemeral agent to avoid quota accumulation
            client.agents.delete_agent(agent.id)

    # ── Tier 2 implementation ─────────────────────────────────────────────────

    def _call_via_openai(self, user_message: str) -> dict[str, Any]:
        """Direct Azure OpenAI JSON-mode call (original implementation)."""
        with console.status("[bold blue]Profiling agent: analysing background with Azure OpenAI…"):
            response = self._openai_client.chat.completions.create(
                model=self._cfg.deployment,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system",  "content": _SYSTEM_PROMPT},
                    {"role": "user",    "content": user_message},
                ],
                temperature=0.2,
                max_tokens=2000,
            )
        raw_json = response.choices[0].message.content
        return json.loads(raw_json)

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

    # ── Public interface ──────────────────────────────────────────────────────

    def run(self, raw: RawStudentInput) -> LearnerProfile:
        """
        Profile the student and return a validated LearnerProfile.

        Raises:
            EnvironmentError   – Neither Foundry nor OpenAI credentials configured.
            ValidationError    – LLM returned JSON that doesn't match the schema.
            json.JSONDecodeError – LLM response was not valid JSON (rare).
        """
        user_msg = self._build_user_message(raw)
        data     = self._call_llm(user_msg)

        # Patch passthrough fields the LLM might not echo exactly
        data.setdefault("student_name", raw.student_name)
        data.setdefault("exam_target",  raw.exam_target)
        data.setdefault("hours_per_week", raw.hours_per_week)
        data.setdefault("weeks_available", raw.weeks_available)
        data.setdefault(
            "total_budget_hours",
            raw.hours_per_week * raw.weeks_available,
        )

        profile = LearnerProfile.model_validate(data)
        tier    = "Azure AI Foundry Agent SDK" if self.using_foundry else "Azure OpenAI"
        console.print(f"[bold green]✓ Profiling complete.[/bold green] [dim](via {tier})[/dim]")
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
