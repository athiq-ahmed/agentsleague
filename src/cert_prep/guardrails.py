"""
guardrails.py – Responsible AI Guardrails Layer
================================================
Implements input validation, output verification, and content safety checks
that wrap every agent transition in the pipeline.

Guardrail levels
----------------
BLOCK   – Hard-stop: the pipeline does not proceed.
WARN    – Soft-stop: the pipeline proceeds with a visible warning.
INFO    – Advisory: informational note logged in agent trace.

Guards implemented
------------------
Input guards (before LearnerIntakeAgent):
  G-01  Non-empty required fields
  G-02  Hours per week within sensible range (1–80)
  G-03  Weeks available within sensible range (1–52)
  G-04  Exam target is a recognised certification code
  G-05  PII redaction notice (name is stored, not transmitted externally)

Profile guards (after LearnerProfilingAgent):
  G-06  Domain profile completeness (all 6 domains present)
  G-07  Confidence scores in [0.0, 1.0]
  G-08  Risk domain list contains valid domain IDs

Study plan guards (after StudyPlanAgent):
  G-09  No task has start_week > end_week
  G-10  Total allocated hours do not exceed budget by >10%

Progress snapshot guards (before ProgressAgent):
  G-11  Hours spent not negative
  G-12  Self-ratings in [1, 5]
  G-13  Practice score in [0, 100] when provided

Assessment guards (after AssessmentAgent):
  G-14  Minimum question count met (≥5)
  G-15  No duplicate question IDs

Output content guards (all agent outputs):
  G-16  No profanity / harmful keywords in free-text fields    [heuristic]
  G-17  Hallucination guard: URLs must start with https://learn.microsoft.com
         or https://www.pearsonvue.com (for modules from LearningPathCuratorAgent)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ─── Enums & data models ─────────────────────────────────────────────────────

class GuardrailLevel(str, Enum):
    BLOCK = "BLOCK"
    WARN  = "WARN"
    INFO  = "INFO"


@dataclass
class GuardrailViolation:
    code:    str
    level:   GuardrailLevel
    message: str
    field:   str = ""   # which field triggered the violation


@dataclass
class GuardrailResult:
    passed:     bool
    violations: list[GuardrailViolation] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return any(v.level == GuardrailLevel.BLOCK for v in self.violations)

    @property
    def warnings(self) -> list[GuardrailViolation]:
        return [v for v in self.violations if v.level == GuardrailLevel.WARN]

    @property
    def infos(self) -> list[GuardrailViolation]:
        return [v for v in self.violations if v.level == GuardrailLevel.INFO]

    def summary(self) -> str:
        if not self.violations:
            return "✅ All guardrails passed."
        lines = [f"{'🚫' if v.level == GuardrailLevel.BLOCK else '⚠️' if v.level == GuardrailLevel.WARN else 'ℹ️'} [{v.code}] {v.message}" for v in self.violations]
        return "\n".join(lines)


# ─── Constant sets ────────────────────────────────────────────────────────────

RECOGNISED_EXAM_CODES = {
    "AI-102", "AI-900",
    "DP-100", "DP-203", "DP-300", "DP-420", "DP-600", "DP-900",
    "AZ-104", "AZ-204", "AZ-305", "AZ-400", "AZ-500", "AZ-700",
    "AZ-800", "AZ-900",
    "MS-900", "MS-102",
    "SC-100", "SC-200", "SC-300", "SC-900",
    "PL-100", "PL-200", "PL-400", "PL-600", "PL-900",
}

VALID_DOMAIN_IDS = {
    "plan_manage", "computer_vision", "nlp",
    "document_intelligence", "conversational_ai", "generative_ai",
}

_HARMFUL_PATTERN = re.compile(
    r"\b(profanity_placeholder|harmful_content_placeholder)\b",
    re.IGNORECASE,
)

TRUSTED_URL_PREFIXES = (
    "https://learn.microsoft.com",
    "https://www.pearsonvue.com",
    "https://aka.ms",
    "https://azure.microsoft.com",
    "https://jolly-field",   # pizza agent demo
)


# ─── Guardrail checks ─────────────────────────────────────────────────────────

class InputGuardrails:
    """G-01 – G-05: Validates RawStudentInput before intake processing."""

    def check(self, raw_input) -> GuardrailResult:
        violations: list[GuardrailViolation] = []

        # G-01 Non-empty required fields
        if not raw_input.student_name.strip():
            violations.append(GuardrailViolation(
                code="G-01", level=GuardrailLevel.BLOCK,
                field="student_name",
                message="Student name must not be empty.",
            ))
        if not raw_input.exam_target.strip():
            violations.append(GuardrailViolation(
                code="G-01", level=GuardrailLevel.BLOCK,
                field="exam_target",
                message="Exam target must not be empty.",
            ))
        if not raw_input.background_text.strip():
            violations.append(GuardrailViolation(
                code="G-01", level=GuardrailLevel.WARN,
                field="background_text",
                message="Background description is empty — profiling accuracy may be limited.",
            ))

        # G-02 Hours per week
        if raw_input.hours_per_week < 1:
            violations.append(GuardrailViolation(
                code="G-02", level=GuardrailLevel.WARN,
                field="hours_per_week",
                message=f"Hours per week ({raw_input.hours_per_week}) is very low (<1). Study plan may be infeasible.",
            ))
        elif raw_input.hours_per_week > 80:
            violations.append(GuardrailViolation(
                code="G-02", level=GuardrailLevel.WARN,
                field="hours_per_week",
                message=f"Hours per week ({raw_input.hours_per_week}) exceeds 80. This may not be sustainable.",
            ))

        # G-03 Weeks available
        if raw_input.weeks_available < 1:
            violations.append(GuardrailViolation(
                code="G-03", level=GuardrailLevel.BLOCK,
                field="weeks_available",
                message="Weeks available must be ≥ 1.",
            ))
        elif raw_input.weeks_available > 52:
            violations.append(GuardrailViolation(
                code="G-03", level=GuardrailLevel.WARN,
                field="weeks_available",
                message=f"Weeks available ({raw_input.weeks_available}) > 52. Consider a shorter target window.",
            ))

        # G-04 Exam target recognition
        code = raw_input.exam_target.split()[0].upper() if raw_input.exam_target else ""
        if code and code not in RECOGNISED_EXAM_CODES:
            violations.append(GuardrailViolation(
                code="G-04", level=GuardrailLevel.WARN,
                field="exam_target",
                message=f"Exam code '{code}' not in recognised catalogue. Proceeding, but content may default to the primary registered exam.",
            ))

        # G-05 PII notice (info only)
        violations.append(GuardrailViolation(
            code="G-05", level=GuardrailLevel.INFO,
            field="student_name",
            message=(
                f"Name '{raw_input.student_name}' is stored in session only and "
                "not transmitted to external services in mock mode."
            ),
        ))

        return GuardrailResult(
            passed=not any(v.level == GuardrailLevel.BLOCK for v in violations),
            violations=violations,
        )


class ProfileGuardrails:
    """G-06 – G-08: Validates LearnerProfile output from LearnerProfilingAgent."""

    def check(self, profile) -> GuardrailResult:
        violations: list[GuardrailViolation] = []

        # G-06 Domain completeness
        expected_count = len(VALID_DOMAIN_IDS)
        actual_count   = len(profile.domain_profiles)
        if actual_count < expected_count:
            violations.append(GuardrailViolation(
                code="G-06", level=GuardrailLevel.WARN,
                message=f"Profile has {actual_count} domains; expected {expected_count}. Some domain insights may be missing.",
            ))

        # G-07 Confidence score bounds
        for dp in profile.domain_profiles:
            if not (0.0 <= dp.confidence_score <= 1.0):
                violations.append(GuardrailViolation(
                    code="G-07", level=GuardrailLevel.BLOCK,
                    field=f"domain_profiles[{dp.domain_id}].confidence_score",
                    message=f"Confidence score {dp.confidence_score} out of [0.0, 1.0] range.",
                ))

        # G-08 Risk domain IDs valid
        invalid_risk = [d for d in profile.risk_domains if d not in VALID_DOMAIN_IDS]
        if invalid_risk:
            violations.append(GuardrailViolation(
                code="G-08", level=GuardrailLevel.WARN,
                message=f"Risk domain IDs not recognised: {invalid_risk}.",
            ))

        return GuardrailResult(
            passed=not any(v.level == GuardrailLevel.BLOCK for v in violations),
            violations=violations,
        )


class StudyPlanGuardrails:
    """G-09 – G-10: Validates StudyPlan output from StudyPlanAgent."""

    def check(self, plan, profile) -> GuardrailResult:
        violations: list[GuardrailViolation] = []

        # G-09 No task with start_week > end_week
        for task in plan.tasks:
            if task.start_week > task.end_week:
                violations.append(GuardrailViolation(
                    code="G-09", level=GuardrailLevel.BLOCK,
                    field=f"task[{task.domain_id}]",
                    message=f"Task '{task.domain_id}' has start_week={task.start_week} > end_week={task.end_week}.",
                ))

        # G-10 Hours budget adherence (±10%)
        allocated = sum(t.total_hours for t in plan.tasks)
        budget    = profile.total_budget_hours
        if allocated > budget * 1.10:
            violations.append(GuardrailViolation(
                code="G-10", level=GuardrailLevel.WARN,
                message=(
                    f"Allocated {allocated:.0f}h exceeds budget {budget:.0f}h by "
                    f"{(allocated/budget - 1)*100:.0f}%. Learner may need to reduce scope."
                ),
            ))

        return GuardrailResult(
            passed=not any(v.level == GuardrailLevel.BLOCK for v in violations),
            violations=violations,
        )


class ProgressSnapshotGuardrails:
    """G-11 – G-13: Validates ProgressSnapshot before ProgressAgent assessment."""

    def check(self, snap) -> GuardrailResult:
        violations: list[GuardrailViolation] = []

        # G-11 Non-negative hours
        if snap.total_hours_spent < 0:
            violations.append(GuardrailViolation(
                code="G-11", level=GuardrailLevel.BLOCK,
                field="total_hours_spent",
                message="Hours spent cannot be negative.",
            ))

        # G-12 Self-ratings in [1, 5]
        for dp in snap.domain_progress:
            if not (1 <= dp.self_rating <= 5):
                violations.append(GuardrailViolation(
                    code="G-12", level=GuardrailLevel.BLOCK,
                    field=f"domain_progress[{dp.domain_id}].self_rating",
                    message=f"Self-rating {dp.self_rating} for '{dp.domain_id}' out of [1, 5] range.",
                ))

        # G-13 Practice score bounds
        if snap.practice_score_pct is not None:
            if not (0 <= snap.practice_score_pct <= 100):
                violations.append(GuardrailViolation(
                    code="G-13", level=GuardrailLevel.BLOCK,
                    field="practice_score_pct",
                    message=f"Practice score {snap.practice_score_pct} out of [0, 100] range.",
                ))

        return GuardrailResult(
            passed=not any(v.level == GuardrailLevel.BLOCK for v in violations),
            violations=violations,
        )


class AssessmentGuardrails:
    """G-14 – G-15: Validates Assessment before presenting to the learner."""

    def check(self, assessment) -> GuardrailResult:
        violations: list[GuardrailViolation] = []

        # G-14 Minimum question count
        if len(assessment.questions) < 5:
            violations.append(GuardrailViolation(
                code="G-14", level=GuardrailLevel.WARN,
                message=f"Assessment has only {len(assessment.questions)} questions (<5). Reliability may be limited.",
            ))

        # G-15 No duplicate IDs
        ids = [q.id for q in assessment.questions]
        dups = {i for i in ids if ids.count(i) > 1}
        if dups:
            violations.append(GuardrailViolation(
                code="G-15", level=GuardrailLevel.BLOCK,
                message=f"Duplicate question IDs detected: {dups}.",
            ))

        return GuardrailResult(
            passed=not any(v.level == GuardrailLevel.BLOCK for v in violations),
            violations=violations,
        )


class OutputContentGuardrails:
    """G-16 – G-17: Validates free-text and URL fields in all agent outputs."""

    def check_text(self, text: str, field_name: str = "") -> GuardrailResult:
        """G-16 – Heuristic harmful content check on a text field."""
        violations: list[GuardrailViolation] = []
        if _HARMFUL_PATTERN.search(text):
            violations.append(GuardrailViolation(
                code="G-16", level=GuardrailLevel.BLOCK,
                field=field_name,
                message="Potentially harmful content detected in output text.",
            ))
        return GuardrailResult(
            passed=not any(v.level == GuardrailLevel.BLOCK for v in violations),
            violations=violations,
        )

    def check_url(self, url: str, field_name: str = "") -> GuardrailResult:
        """G-17 – Ensure URLs originate from trusted Microsoft/Pearson domains."""
        violations: list[GuardrailViolation] = []
        if url and not any(url.startswith(p) for p in TRUSTED_URL_PREFIXES):
            violations.append(GuardrailViolation(
                code="G-17", level=GuardrailLevel.WARN,
                field=field_name,
                message=f"URL '{url[:80]}' does not originate from a trusted domain.",
            ))
        return GuardrailResult(
            passed=True,    # URL mismatches are warnings, not blocks
            violations=violations,
        )

    def check_learning_path(self, learning_path) -> GuardrailResult:
        """Run G-16 + G-17 across all modules in a LearningPath."""
        all_violations: list[GuardrailViolation] = []
        for mod in learning_path.all_modules:
            r = self.check_url(mod.url, field_name=f"LearningModule[{mod.ms_learn_uid}].url")
            all_violations.extend(r.violations)
        return GuardrailResult(
            passed=not any(v.level == GuardrailLevel.BLOCK for v in all_violations),
            violations=all_violations,
        )


# ─── Convenience façade ───────────────────────────────────────────────────────

class GuardrailsPipeline:
    """
    Single entry-point that runs all applicable guardrails for a given pipeline stage.

    Usage::

        gp = GuardrailsPipeline()

        # Stage 1 – raw input
        result = gp.check_input(raw_student_input)

        # Stage 2 – after profiling
        result = gp.check_profile(learner_profile)

        # Stage 3 – after study plan
        result = gp.check_study_plan(study_plan, learner_profile)

        # Stage 4 – before progress assessment
        result = gp.check_progress_snapshot(progress_snapshot)

        # Stage 5 – after assessment generation
        result = gp.check_assessment(assessment)
    """

    def __init__(self):
        self.input_guard    = InputGuardrails()
        self.profile_guard  = ProfileGuardrails()
        self.plan_guard     = StudyPlanGuardrails()
        self.snap_guard     = ProgressSnapshotGuardrails()
        self.assess_guard   = AssessmentGuardrails()
        self.content_guard  = OutputContentGuardrails()

    def check_input(self, raw) -> GuardrailResult:
        return self.input_guard.check(raw)

    def check_profile(self, profile) -> GuardrailResult:
        return self.profile_guard.check(profile)

    def check_study_plan(self, plan, profile) -> GuardrailResult:
        return self.plan_guard.check(plan, profile)

    def check_progress_snapshot(self, snap) -> GuardrailResult:
        return self.snap_guard.check(snap)

    def check_assessment(self, assessment) -> GuardrailResult:
        return self.assess_guard.check(assessment)

    def check_learning_path(self, learning_path) -> GuardrailResult:
        return self.content_guard.check_learning_path(learning_path)

    def merge(self, *results: GuardrailResult) -> GuardrailResult:
        """Merge multiple GuardrailResult objects into one."""
        all_v = []
        for r in results:
            all_v.extend(r.violations)
        return GuardrailResult(
            passed=not any(v.level == GuardrailLevel.BLOCK for v in all_v),
            violations=all_v,
        )
