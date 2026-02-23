"""
Smoke tests for guardrails pipeline.
Run: python -m pytest tests/ -v
"""
import sys
import os

# Ensure src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cert_prep.guardrails import (
    OutputContentGuardrails,
    InputGuardrails,
    GuardrailLevel,
)
from cert_prep.models import RawStudentInput


class TestG16PiiPatterns:
    """G-16: PII detection should WARN (not block)."""

    def setup_method(self):
        self.guard = OutputContentGuardrails()

    def test_ssn_detected(self):
        result = self.guard.check_text(
            "My SSN is 123-45-6789 and I have 5 years exp.", "background_text"
        )
        pii_violations = [v for v in result.violations if v.code == "G-16"]
        assert pii_violations, "SSN should trigger G-16 PII violation"
        assert pii_violations[0].level == GuardrailLevel.WARN

    def test_credit_card_detected(self):
        result = self.guard.check_text(
            "Card: 4111 1111 1111 1111 — please ignore.", "background_text"
        )
        pii_violations = [v for v in result.violations if v.code == "G-16"]
        assert pii_violations, "Credit card should trigger G-16 PII violation"

    def test_email_detected(self):
        result = self.guard.check_text(
            "I'm jane.doe@company.com, senior engineer.", "background_text"
        )
        pii_violations = [v for v in result.violations if v.code == "G-16"]
        assert pii_violations, "Email address should trigger G-16 PII violation"

    def test_phone_detected(self):
        result = self.guard.check_text(
            "Call me at (555) 867-5309 anytime.", "background_text"
        )
        pii_violations = [v for v in result.violations if v.code == "G-16"]
        assert pii_violations, "Phone number should trigger G-16 PII violation"

    def test_ip_detected(self):
        result = self.guard.check_text(
            "My dev machine is at 192.168.1.42.", "background_text"
        )
        pii_violations = [v for v in result.violations if v.code == "G-16"]
        assert pii_violations, "IP address should trigger G-16 PII violation"

    def test_clean_text_no_pii(self):
        result = self.guard.check_text(
            "I am a software engineer with 8 years of Python and Azure experience.",
            "background_text",
        )
        pii_violations = [v for v in result.violations if v.code == "G-16"]
        assert not pii_violations, "Clean professional bio should not trigger PII"

    def test_pii_does_not_block(self):
        """PII should warn but not halt the pipeline."""
        result = self.guard.check_text("SSN: 987-65-4321", "background_text")
        assert not result.blocked, "PII alone should NOT set blocked=True"


class TestG16HarmfulPatterns:
    """G-16: Harmful content should BLOCK the pipeline."""

    def setup_method(self):
        self.guard = OutputContentGuardrails()

    def test_harmful_content_blocks(self):
        result = self.guard.check_text(
            "I want to hack the exam system.", "background_text"
        )
        harmful = [
            v
            for v in result.violations
            if v.code == "G-16" and v.level == GuardrailLevel.BLOCK
        ]
        assert harmful or result.blocked, "Harmful keyword should trigger BLOCK"

    def test_clean_exam_language_not_blocked(self):
        """Common exam idioms must not be false-positives."""
        result = self.guard.check_text(
            "I want to ace the AI-102 exam and crush my certification goals.",
            "background_text",
        )
        assert not result.blocked, "Positive exam language should not be blocked"


class TestInputGuardrailsPiiScan:
    """G-16 PII scan at InputGuardrails.check() level."""

    def test_pii_in_background_text_warns(self):
        raw = RawStudentInput(
            student_name="Test User",
            exam_target="AI-102",
            background_text="Hello, my SSN is 123-45-6789.",
            existing_certs=[],
            hours_per_week=10.0,
            weeks_available=8,
            concern_topics=[],
            preferred_style="videos",
            goal_text="I want to pass AI-102.",
        )
        ig = InputGuardrails()
        result = ig.check(raw)
        pii_v = [v for v in result.violations if v.code == "G-16"]
        assert pii_v, "G-16 should surface PII violation from background_text"

    def test_clean_input_passes(self):
        raw = RawStudentInput(
            student_name="Test User",
            exam_target="AI-102",
            background_text="I am a cloud engineer with Azure experience.",
            existing_certs=[],
            hours_per_week=10.0,
            weeks_available=8,
            concern_topics=[],
            preferred_style="videos",
            goal_text="I want to pass AI-102.",
        )
        ig = InputGuardrails()
        result = ig.check(raw)
        pii_v = [v for v in result.violations if v.code == "G-16"]
        assert not pii_v, "Clean background text should produce no G-16 violations"
