"""
learning_path_curator.py – Learning Path Curator Agent (Block 1.1)
===================================================================
Maps each AI-102 domain in a LearnerProfile to curated Microsoft Learn
modules, producing a personalised reading list ordered by study priority.

Architecture role:
  Block 1 (Intake) → Block 1.1 (LearningPathCuratorAgent) → Block 1.2 (StudyPlanAgent)

The mock implementation returns hard-coded MS Learn module metadata.
A live implementation can call the Microsoft Learn Catalog API:
  GET https://learn.microsoft.com/api/catalog/?locale=en-us&type=modules

Output
------
LearningPath
  └── List[LearningModule]  (one per relevant MS Learn module)
  └── curated_paths: dict[domain_id → list[LearningModule]]
  └── total_hours_est: float  (sum of all module duration estimates)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


# ─── Data models ─────────────────────────────────────────────────────────────

@dataclass
class LearningModule:
    """A single Microsoft Learn module or learning path entry."""
    title:        str
    url:          str
    domain_id:    str
    duration_min: int    = 30       # estimated completion in minutes
    difficulty:   str   = "intermediate"   # beginner | intermediate | advanced
    module_type:  str   = "module"  # module | learning-path | collection
    priority:     str   = "core"    # core | supplemental | optional
    ms_learn_uid: str   = ""        # unique ID for deep-linking


@dataclass
class LearningPath:
    """Curated learning path output from LearningPathCuratorAgent."""
    student_name:     str
    exam_target:      str
    curated_paths:    dict = field(default_factory=dict)   # domain_id → list[LearningModule]
    all_modules:      list = field(default_factory=list)   # flat list, priority-sorted
    total_hours_est:  float = 0.0
    skipped_domains:  list = field(default_factory=list)   # domain IDs that were skipped
    summary:          str  = ""


# ─── MS Learn module catalogue (mock / offline) ───────────────────────────────
# Each tuple: (title, relative_url, duration_min, difficulty, type, priority)

_LEARN_CATALOGUE: dict[str, list[tuple]] = {
    "plan_manage": [
        (
            "Plan and manage an Azure AI solution",
            "https://learn.microsoft.com/en-us/training/paths/prepare-for-ai-engineering/",
            120, "intermediate", "learning-path", "core",
            "ai-102-plan-manage",
        ),
        (
            "Secure Azure AI services",
            "https://learn.microsoft.com/en-us/training/modules/secure-ai-services/",
            45, "intermediate", "module", "core",
            "secure-ai-services",
        ),
        (
            "Monitor Azure AI services",
            "https://learn.microsoft.com/en-us/training/modules/monitor-ai-services/",
            30, "intermediate", "module", "core",
            "monitor-ai-services",
        ),
        (
            "Implement responsible AI with Azure AI Content Safety",
            "https://learn.microsoft.com/en-us/training/modules/intro-to-azure-content-safety/",
            40, "intermediate", "module", "supplemental",
            "azure-content-safety",
        ),
    ],
    "computer_vision": [
        (
            "Create computer vision solutions with Azure AI Vision",
            "https://learn.microsoft.com/en-us/training/paths/create-computer-vision-solutions-azure-ai/",
            180, "intermediate", "learning-path", "core",
            "create-computer-vision",
        ),
        (
            "Analyze images with the Azure AI Vision service",
            "https://learn.microsoft.com/en-us/training/modules/analyze-images/",
            60, "beginner", "module", "core",
            "analyze-images",
        ),
        (
            "Classify images with a custom Azure AI Vision model",
            "https://learn.microsoft.com/en-us/training/modules/custom-model-ai-vision-image-classification/",
            45, "intermediate", "module", "core",
            "custom-vision-classification",
        ),
        (
            "Detect, analyze, and recognize faces",
            "https://learn.microsoft.com/en-us/training/modules/detect-analyze-recognize-faces/",
            50, "intermediate", "module", "core",
            "detect-faces",
        ),
        (
            "Read text with Azure AI Vision",
            "https://learn.microsoft.com/en-us/training/modules/read-text-images-documents-with-computer-vision-service/",
            40, "beginner", "module", "core",
            "read-text-vision",
        ),
        (
            "Analyze video with Azure AI Video Indexer",
            "https://learn.microsoft.com/en-us/training/modules/analyze-video/",
            35, "intermediate", "module", "supplemental",
            "analyze-video",
        ),
    ],
    "nlp": [
        (
            "Develop natural language processing solutions with Azure AI Language",
            "https://learn.microsoft.com/en-us/training/paths/develop-language-solutions-azure-ai/",
            200, "intermediate", "learning-path", "core",
            "nlp-learning-path",
        ),
        (
            "Analyze text with Azure AI Language",
            "https://learn.microsoft.com/en-us/training/modules/analyze-text-with-text-analytics-service/",
            60, "beginner", "module", "core",
            "analyze-text",
        ),
        (
            "Build a conversational language understanding model",
            "https://learn.microsoft.com/en-us/training/modules/build-language-understanding-model/",
            55, "intermediate", "module", "core",
            "clu-model",
        ),
        (
            "Create a question answering solution",
            "https://learn.microsoft.com/en-us/training/modules/create-question-answer-solution-ai-language/",
            50, "intermediate", "module", "core",
            "question-answering",
        ),
        (
            "Translate text and speech with Azure AI",
            "https://learn.microsoft.com/en-us/training/modules/translate-text-with-translation-service/",
            40, "beginner", "module", "supplemental",
            "translate-text",
        ),
    ],
    "document_intelligence": [
        (
            "Extract data from forms with Azure Document Intelligence",
            "https://learn.microsoft.com/en-us/training/paths/extract-data-from-forms-document-intelligence/",
            150, "intermediate", "learning-path", "core",
            "document-intelligence-path",
        ),
        (
            "Get started with Azure AI Document Intelligence",
            "https://learn.microsoft.com/en-us/training/modules/intro-to-form-recognizer/",
            45, "beginner", "module", "core",
            "intro-document-intelligence",
        ),
        (
            "Implement an Azure AI Search solution",
            "https://learn.microsoft.com/en-us/training/paths/implement-knowledge-mining-azure-cognitive-search/",
            180, "intermediate", "learning-path", "core",
            "azure-search-path",
        ),
        (
            "Enrich your search index using language understanding models",
            "https://learn.microsoft.com/en-us/training/modules/enrich-search-index-using-language-models/",
            40, "advanced", "module", "supplemental",
            "enrich-search-index",
        ),
    ],
    "conversational_ai": [
        (
            "Create conversational AI solutions",
            "https://learn.microsoft.com/en-us/training/paths/create-conversational-ai-solutions/",
            160, "intermediate", "learning-path", "core",
            "conversational-ai-path",
        ),
        (
            "Build a bot with the Azure Bot Service",
            "https://learn.microsoft.com/en-us/training/modules/design-bot-conversation-flow/",
            55, "intermediate", "module", "core",
            "bot-service",
        ),
        (
            "Create a bot with Bot Framework Composer",
            "https://learn.microsoft.com/en-us/training/modules/create-bot-with-bot-framework-composer/",
            60, "intermediate", "module", "supplemental",
            "bot-framework-composer",
        ),
    ],
    "generative_ai": [
        (
            "Develop generative AI solutions with Azure OpenAI Service",
            "https://learn.microsoft.com/en-us/training/paths/develop-ai-solutions-azure-openai/",
            200, "intermediate", "learning-path", "core",
            "generative-ai-path",
        ),
        (
            "Get started with Azure OpenAI Service",
            "https://learn.microsoft.com/en-us/training/modules/get-started-openai/",
            50, "beginner", "module", "core",
            "get-started-openai",
        ),
        (
            "Apply prompt engineering with Azure OpenAI Service",
            "https://learn.microsoft.com/en-us/training/modules/apply-prompt-engineering-azure-openai/",
            45, "intermediate", "module", "core",
            "prompt-engineering",
        ),
        (
            "Build natural language solutions with Azure OpenAI Service",
            "https://learn.microsoft.com/en-us/training/modules/build-language-solution-azure-openai/",
            50, "intermediate", "module", "core",
            "openai-nlp",
        ),
        (
            "Implement Retrieval Augmented Generation (RAG) with Azure OpenAI",
            "https://learn.microsoft.com/en-us/training/modules/use-own-data-azure-openai/",
            55, "advanced", "module", "core",
            "openai-rag",
        ),
        (
            "Generate images with Azure OpenAI DALL-E models",
            "https://learn.microsoft.com/en-us/training/modules/generate-images-azure-openai/",
            35, "intermediate", "module", "supplemental",
            "openai-dalle",
        ),
    ],
}

# Priority bump for risk domains
_RISK_PRIORITY_BOOST = {"supplemental": "core", "optional": "supplemental"}


class LearningPathCuratorAgent:
    """
    Block 1.1 — Learning Path Curator Agent.

    Selects and orders Microsoft Learn modules for a learner based on:
    - Their domain knowledge levels (skip strong domains)
    - Risk domains (promote supplemental → core)
    - Learning style preferences
    - Estimated study budget

    Usage::

        agent = LearningPathCuratorAgent()
        path  = agent.curate(profile)
    """

    # Guardrail: cap total curated hours to 2× budget so the list stays manageable
    MAX_HOURS_MULTIPLIER = 2.0

    def curate(self, profile) -> LearningPath:
        """Return a `LearningPath` personalised for the given `LearnerProfile`."""
        from cert_prep.models import DomainKnowledge

        curated: dict[str, list[LearningModule]] = {}
        all_modules: list[LearningModule] = []
        skipped: list[str] = []
        budget_minutes = profile.total_budget_hours * 60 * self.MAX_HOURS_MULTIPLIER
        spent_minutes  = 0.0

        # Process domains ordered by priority: risk first, then regular, skip last
        sorted_profiles = sorted(
            profile.domain_profiles,
            key=lambda dp: (
                0 if dp.domain_id in profile.risk_domains else
                2 if dp.skip_recommended else
                1
            ),
        )

        for dp in sorted_profiles:
            raw_modules = _LEARN_CATALOGUE.get(dp.domain_id, [])
            domain_modules: list[LearningModule] = []

            # Skip strong domains that were already flagged
            if dp.skip_recommended and dp.knowledge_level.value in ("strong",):
                skipped.append(dp.domain_id)
                curated[dp.domain_id] = []
                continue

            for item in raw_modules:
                title, url, dur, diff, mtype, pri, uid = item

                # Boost priority for risk domains
                if dp.domain_id in profile.risk_domains:
                    pri = _RISK_PRIORITY_BOOST.get(pri, pri)

                # For advanced learners, skip beginner-only modules unless risk domain
                if (
                    diff == "beginner"
                    and dp.knowledge_level.value in ("moderate", "strong")
                    and dp.domain_id not in profile.risk_domains
                ):
                    pri = "optional"

                # Respect budget cap
                if spent_minutes + dur > budget_minutes and pri == "optional":
                    continue

                mod = LearningModule(
                    title=title,
                    url=url,
                    domain_id=dp.domain_id,
                    duration_min=dur,
                    difficulty=diff,
                    module_type=mtype,
                    priority=pri,
                    ms_learn_uid=uid,
                )
                domain_modules.append(mod)
                all_modules.append(mod)
                spent_minutes += dur

            curated[dp.domain_id] = domain_modules

        # Sort flat list: core → supplemental → optional; then by domain risk
        _pri_order = {"core": 0, "supplemental": 1, "optional": 2}
        all_modules.sort(key=lambda m: (
            _pri_order.get(m.priority, 9),
            0 if m.domain_id in profile.risk_domains else 1,
        ))

        total_hours = sum(m.duration_min for m in all_modules) / 60.0

        summary = (
            f"Curated **{len(all_modules)} MS Learn modules** across "
            f"**{len(curated) - len(skipped)} active domains** "
            f"(~{total_hours:.1f}h total). "
            f"{len(skipped)} domain(s) skipped based on strong prior knowledge."
        )

        return LearningPath(
            student_name=profile.student_name,
            exam_target=profile.exam_target,
            curated_paths=curated,
            all_modules=all_modules,
            total_hours_est=total_hours,
            skipped_domains=skipped,
            summary=summary,
        )
