"""
Data models for the Certification Prep Multi-Agent System.

Block 1 (Intake + Profiling) models are defined here;
later blocks will extend this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ─── Enumerations ────────────────────────────────────────────────────────────

class DomainKnowledge(str, Enum):
    """How well the student already knows a domain."""
    UNKNOWN  = "unknown"   # never studied
    WEAK     = "weak"      # aware but not confident
    MODERATE = "moderate"  # working knowledge
    STRONG   = "strong"    # confident – candidate for skip


class LearningStyle(str, Enum):
    """Preferred learning modality inferred from student description."""
    LINEAR    = "linear"     # structured, step-by-step
    LAB_FIRST = "lab_first"  # hands-on before reading theory
    REFERENCE = "reference"  # quick-scan cards, API docs
    ADAPTIVE  = "adaptive"   # let the system decide per domain


class ExperienceLevel(str, Enum):
    """Overall AI/Azure background of the student."""
    BEGINNER       = "beginner"       # no prior Azure or AI services exposure
    INTERMEDIATE   = "intermediate"   # some Azure; limited AI services hands-on
    ADVANCED_AZURE = "advanced_azure" # strong Azure IaC/admin; new to AI services
    EXPERT_ML      = "expert_ml"      # data science / ML engineering background


# ─── Microsoft Exam Domain Registry ─────────────────────────────────────────

# Default / sample domain blueprint (AI-102).  The system is exam-agnostic;
# swap or extend via EXAM_DOMAIN_REGISTRY for any Microsoft certification.

EXAM_DOMAINS: list[dict] = [
    {
        "id":     "plan_manage",
        "name":   "Plan & Manage Azure AI Solutions",
        "weight": 0.175,   # midpoint of 15–20 %
        "description": (
            "Security, monitoring, responsible AI, cost management, "
            "resource provisioning and deployment of Azure AI services."
        ),
    },
    {
        "id":     "computer_vision",
        "name":   "Implement Computer Vision Solutions",
        "weight": 0.225,
        "description": (
            "Azure AI Vision, Custom Vision, Face API, Video Indexer, "
            "image classification, object detection, OCR."
        ),
    },
    {
        "id":     "nlp",
        "name":   "Implement NLP Solutions",
        "weight": 0.225,
        "description": (
            "Azure AI Language, CLU, sentiment analysis, NER, "
            "text summarisation, question answering, translator."
        ),
    },
    {
        "id":     "document_intelligence",
        "name":   "Implement Document Intelligence & Knowledge Mining",
        "weight": 0.175,
        "description": (
            "Azure AI Document Intelligence, Cognitive Search, "
            "custom skills, indexers, knowledge stores."
        ),
    },
    {
        "id":     "conversational_ai",
        "name":   "Implement Conversational AI Solutions",
        "weight": 0.10,
        "description": (
            "Azure Bot Service, Bot Framework Composer, Adaptive Dialogs, "
            "CLU channel integration, Power Virtual Agents."
        ),
    },
    {
        "id":     "generative_ai",
        "name":   "Implement Generative AI Solutions",
        "weight": 0.10,
        "description": (
            "Azure OpenAI Service, prompt engineering, RAG patterns, "
            "content filters, DALL-E, responsible generative AI."
        ),
    },
]

DOMAIN_IDS = [d["id"] for d in EXAM_DOMAINS]


# ─── Multi-exam registry (extensible) ─────────────────────────────────────────

EXAM_DOMAIN_REGISTRY: dict[str, list[dict]] = {
    "AI-102": EXAM_DOMAINS,
    # Add more exams here, e.g.:
    # "DP-100": [ ... ],
    # "AZ-204": [ ... ],
}


def get_exam_domains(exam_code: str) -> list[dict]:
    """Return domain list for *exam_code*, falling back to the default blueprint."""
    return EXAM_DOMAIN_REGISTRY.get(exam_code.upper(), EXAM_DOMAINS)


# ─── Block 1 Input Model ─────────────────────────────────────────────────────

@dataclass
class RawStudentInput:
    """
    Raw, unprocessed input collected by LearnerIntakeAgent.
    This is the exact information the student provides – no inference yet.
    """
    student_name:      str
    exam_target:       str                    # e.g. "AI-102"
    background_text:   str                    # free-text background description
    existing_certs:    list[str]              # e.g. ["AZ-104", "AZ-305"]
    hours_per_week:    float                  # e.g. 10.0
    weeks_available:   int                    # e.g. 8
    concern_topics:    list[str]              # e.g. ["Azure OpenAI", "Bot Service"]
    preferred_style:   str                    # free-text learning preference
    goal_text:         str                    # why they want to pass


# ─── Block 1 Output Models ───────────────────────────────────────────────────

class DomainProfile(BaseModel):
    """Per-domain profiling result produced by LearnerProfilingAgent."""
    domain_id:          str
    domain_name:        str
    knowledge_level:    DomainKnowledge
    confidence_score:   float = Field(ge=0.0, le=1.0,
                                      description="0=no knowledge, 1=expert")
    skip_recommended:   bool  = Field(
        description="True if student's background makes this domain coverable quickly"
    )
    notes:              str   = Field(description="1–2 sentence rationale")


class LearnerProfile(BaseModel):
    """
    Structured learner profile output of Block 1 (Intake + Profiling).
    This is passed downstream to Block 1.1 (Learning Path Planner).
    """
    student_name:        str
    exam_target:         str
    experience_level:    ExperienceLevel
    learning_style:      LearningStyle
    hours_per_week:      float
    weeks_available:     int
    total_budget_hours:  float

    domain_profiles:     list[DomainProfile] = Field(
        description="One entry per exam domain, in blueprint order"
    )
    modules_to_skip:     list[str] = Field(
        description="Human-readable module names that can be safely skipped"
    )
    risk_domains:        list[str] = Field(
        description="Domain IDs most likely to need remediation"
    )
    analogy_map:         dict[str, str] = Field(
        description="Existing skill → Azure AI equivalent (empty if not applicable)"
    )
    recommended_approach: str = Field(
        description="2–3 sentence personalisation summary for downstream agents"
    )
    engagement_notes:    str = Field(
        description="Motivational tone and reminder cadence recommendation"
    )

    # ── Derived helpers ──────────────────────────────────────────────────────

    def domains_to_skip(self) -> list[str]:
        return [dp.domain_id for dp in self.domain_profiles if dp.skip_recommended]

    def weak_domains(self) -> list[str]:
        return [
            dp.domain_id for dp in self.domain_profiles
            if dp.knowledge_level in (DomainKnowledge.UNKNOWN, DomainKnowledge.WEAK)
        ]

    def domain_by_id(self, domain_id: str) -> Optional[DomainProfile]:
        return next((d for d in self.domain_profiles if d.domain_id == domain_id), None)
