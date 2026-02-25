"""
Tests for PDF and HTML generation functions (b1_2_progress_agent.py).
All functions should return non-empty, structurally valid output.
"""
import pytest
from factories import make_profile, make_raw, make_snapshot

from cert_prep.b1_2_progress_agent import (
    generate_profile_pdf,
    generate_assessment_pdf,
    generate_intake_summary_html,
    generate_weekly_summary,
    ProgressAgent,
)
from cert_prep.b1_1_study_plan_agent import StudyPlanAgent
from cert_prep.b1_1_learning_path_curator import LearningPathCuratorAgent
from cert_prep.b2_assessment_agent import AssessmentAgent


@pytest.fixture
def plan_ai102(profile_ai102):
    return StudyPlanAgent().run(profile_ai102)


@pytest.fixture
def lp_ai102(profile_ai102):
    return LearningPathCuratorAgent().curate(profile_ai102)


@pytest.fixture
def result_ai102(profile_ai102, snapshot_ai102):
    """ReadinessAssessment (used by generate_weekly_summary)."""
    return ProgressAgent().assess(profile_ai102, snapshot_ai102)


# ─── generate_profile_pdf ─────────────────────────────────────────────────────

class TestGenerateProfilePdf:
    def test_returns_bytes(self, profile_ai102, plan_ai102, lp_ai102):
        data = generate_profile_pdf(profile_ai102, plan=plan_ai102, lp=lp_ai102)
        assert isinstance(data, bytes)

    def test_non_empty_bytes(self, profile_ai102, plan_ai102, lp_ai102):
        data = generate_profile_pdf(profile_ai102, plan=plan_ai102, lp=lp_ai102)
        assert len(data) > 0

    def test_pdf_header_signature(self, profile_ai102, plan_ai102, lp_ai102):
        data = generate_profile_pdf(profile_ai102, plan=plan_ai102, lp=lp_ai102)
        # PDF files start with %PDF
        assert data[:4] == b"%PDF", "Output must start with %PDF header"

    def test_no_plan_no_error(self, profile_ai102):
        data = generate_profile_pdf(profile_ai102, plan=None, lp=None)
        assert isinstance(data, bytes) and len(data) > 0

    def test_with_raw_no_error(self, profile_ai102, plan_ai102):
        raw = make_raw()
        data = generate_profile_pdf(profile_ai102, plan=plan_ai102, lp=None, raw=raw)
        assert isinstance(data, bytes) and len(data) > 0

    def test_none_raw_no_attribute_error(self, profile_ai102, plan_ai102):
        # Must not raise AttributeError when raw=None
        data = generate_profile_pdf(profile_ai102, plan=plan_ai102, lp=None, raw=None)
        assert isinstance(data, bytes)


# ─── generate_assessment_pdf ──────────────────────────────────────────────────

class TestGenerateAssessmentPdf:
    @pytest.fixture
    def assessment_result(self, profile_ai102, snapshot_ai102):
        """generate_assessment_pdf also expects ReadinessAssessment."""
        return ProgressAgent().assess(profile_ai102, snapshot_ai102)

    def test_returns_bytes(self, profile_ai102, snapshot_ai102, assessment_result):
        data = generate_assessment_pdf(profile_ai102, snapshot_ai102, assessment_result)
        assert isinstance(data, bytes)

    def test_non_empty_bytes(self, profile_ai102, snapshot_ai102, assessment_result):
        data = generate_assessment_pdf(profile_ai102, snapshot_ai102, assessment_result)
        assert len(data) > 0

    def test_pdf_header_signature(self, profile_ai102, snapshot_ai102, assessment_result):
        data = generate_assessment_pdf(profile_ai102, snapshot_ai102, assessment_result)
        assert data[:4] == b"%PDF"


# ─── generate_intake_summary_html ─────────────────────────────────────────────

class TestGenerateIntakeSummaryHtml:
    def test_returns_string(self, profile_ai102, plan_ai102, lp_ai102):
        html = generate_intake_summary_html(profile_ai102, plan=plan_ai102, lp=lp_ai102)
        assert isinstance(html, str)

    def test_non_empty_html(self, profile_ai102, plan_ai102, lp_ai102):
        html = generate_intake_summary_html(profile_ai102, plan=plan_ai102, lp=lp_ai102)
        assert len(html.strip()) > 0

    def test_contains_html_tags(self, profile_ai102, plan_ai102, lp_ai102):
        html = generate_intake_summary_html(profile_ai102, plan=plan_ai102, lp=lp_ai102)
        assert "<" in html and ">" in html, "Output must contain HTML tags"

    def test_contains_student_name(self, profile_ai102, plan_ai102, lp_ai102):
        html = generate_intake_summary_html(profile_ai102, plan=plan_ai102, lp=lp_ai102)
        assert profile_ai102.student_name in html, "HTML must include student name"

    def test_no_plan_no_error(self, profile_ai102):
        html = generate_intake_summary_html(profile_ai102, plan=None, lp=None)
        assert isinstance(html, str) and len(html) > 0


# ─── generate_weekly_summary ──────────────────────────────────────────────────

class TestGenerateWeeklySummary:
    def test_returns_string(self, profile_ai102, snapshot_ai102, result_ai102):
        summary = generate_weekly_summary(profile_ai102, snapshot_ai102, result_ai102)
        assert isinstance(summary, str)

    def test_non_empty_summary(self, profile_ai102, snapshot_ai102, result_ai102):
        summary = generate_weekly_summary(profile_ai102, snapshot_ai102, result_ai102)
        assert len(summary.strip()) > 0

    def test_contains_learner_name(self, profile_ai102, snapshot_ai102, result_ai102):
        summary = generate_weekly_summary(profile_ai102, snapshot_ai102, result_ai102)
        assert profile_ai102.student_name in summary, (
            "Weekly summary must include learner name"
        )

    def test_contains_exam_target(self, profile_ai102, snapshot_ai102, result_ai102):
        summary = generate_weekly_summary(profile_ai102, snapshot_ai102, result_ai102)
        assert "AI-102" in summary or "AI" in summary

    # Cross-exam smoke test
    @pytest.mark.parametrize("exam_target", ["DP-100", "AZ-204"])
    def test_other_exams_no_error(self, exam_target):
        profile = make_profile(exam_target=exam_target)
        snap    = make_snapshot(profile)
        ra      = ProgressAgent().assess(profile, snap)
        summary = generate_weekly_summary(profile, snap, ra)
        assert isinstance(summary, str) and len(summary) > 0
