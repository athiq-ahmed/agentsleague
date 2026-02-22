"""
assessment_agent.py – Readiness Assessment Agent (Block 2)
===========================================================
Generates domain-weighted multiple-choice questions, evaluates the learner's
answers, and returns a scored `AssessmentResult`.

Architecture role:
  Block 1.1 / Progress Check-In
    ↓
  AssessmentAgent  ←  (human confirms ready for assessment)
    ↓
  Block 3: CertificationRecommendationAgent

The mock bank contains 5 questions per AI-102 domain (30 total).
In live mode the agent calls Azure OpenAI to generate novel questions.

Output
------
Assessment
  └── questions: list[QuizQuestion]

AssessmentResult
  └── score_pct: float
  └── passed: bool
  └── domain_scores: dict[domain_id → float]
  └── feedback: list[QuestionFeedback]
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional


# ─── Data models ─────────────────────────────────────────────────────────────

@dataclass
class QuizQuestion:
    """A single multiple-choice question."""
    id:            str
    domain_id:     str
    domain_name:   str
    question:      str
    options:       list[str]    # exactly 4 options (A–D)
    correct_index: int          # 0-based index of the correct option
    explanation:   str          # why the correct answer is right
    difficulty:    str = "medium"   # easy | medium | hard


@dataclass
class QuestionFeedback:
    """Per-question result after the learner answers."""
    question_id:    str
    correct:        bool
    learner_index:  int        # which option the learner chose
    correct_index:  int
    explanation:    str


@dataclass
class Assessment:
    """A generated assessment instance ready to be presented."""
    student_name:  str
    exam_target:   str
    questions:     list[QuizQuestion] = field(default_factory=list)
    total_marks:   int = 0
    pass_mark_pct: float = 60.0    # ≥60% to pass


@dataclass
class AssessmentResult:
    """Scored result after the learner submits their answers."""
    student_name:    str
    exam_target:     str
    score_pct:       float
    passed:          bool
    correct_count:   int
    total_count:     int
    domain_scores:   dict = field(default_factory=dict)   # domain_id → pct
    feedback:        list = field(default_factory=list)   # list[QuestionFeedback]
    verdict:         str  = ""
    recommendation:  str  = ""


# ─── Question bank ────────────────────────────────────────────────────────────
# Format: (id, question, [A, B, C, D], correct_index_0based, explanation, difficulty)

_QUESTION_BANK: dict[str, list[tuple]] = {
    "plan_manage": [
        (
            "pm_01",
            "Which Azure feature allows you to restrict Azure AI services access "
            "to specific virtual networks and IP ranges?",
            [
                "A. Azure Role-Based Access Control (RBAC)",
                "B. Network Service Endpoints and IP firewall rules",
                "C. Azure Policy assignments",
                "D. Private DNS zones",
            ],
            1,
            "Azure AI services support network access restrictions via Virtual Network "
            "Service Endpoints and IP firewall rules configured in the resource's "
            "Networking blade.",
            "medium",
        ),
        (
            "pm_02",
            "What is the recommended approach to store Azure AI service keys securely "
            "in a production application?",
            [
                "A. Hard-code them in the application configuration file",
                "B. Commit them to a private GitHub repository",
                "C. Store them in Azure Key Vault and reference via Managed Identity",
                "D. Pass them as environment variables in Docker compose",
            ],
            2,
            "Azure Key Vault + Managed Identity is the recommended zero-secret approach. "
            "It avoids credential exposure and simplifies rotation.",
            "easy",
        ),
        (
            "pm_03",
            "Which metric would you monitor to detect when an Azure AI service is "
            "being throttled due to exceeding its quota?",
            [
                "A. Latency (ms)",
                "B. RateLimit429Errors",
                "C. SuccessfulCalls",
                "D. TokensConsumed",
            ],
            1,
            "HTTP 429 (Too Many Requests) responses indicate rate limiting / throttling. "
            "The RateLimit429Errors metric in Azure Monitor captures these events.",
            "hard",
        ),
        (
            "pm_04",
            "A developer needs the minimum permissions to call a deployed Azure AI "
            "Vision endpoint. Which built-in role should be assigned?",
            [
                "A. Contributor",
                "B. Owner",
                "C. Cognitive Services User",
                "D. Cognitive Services Contributor",
            ],
            2,
            "Cognitive Services User grants inference-only access (calling the endpoint) "
            "without allowing resource management actions.",
            "medium",
        ),
        (
            "pm_05",
            "Which principle of Responsible AI relates to ensuring that AI systems "
            "treat all individuals and groups fairly?",
            [
                "A. Reliability & Safety",
                "B. Privacy & Security",
                "C. Fairness",
                "D. Inclusiveness",
            ],
            2,
            "The Fairness principle focuses on avoiding bias and treating all people "
            "equitably regardless of race, gender, or other attributes.",
            "easy",
        ),
    ],
    "computer_vision": [
        (
            "cv_01",
            "Which Azure AI Vision feature returns a detailed description of an "
            "image in natural language?",
            [
                "A. Optical Character Recognition (OCR)",
                "B. Smart Crop",
                "C. Image Captioning (DenseCaptions)",
                "D. Background Removal",
            ],
            2,
            "Image Captioning (and the DenseCaptions feature in Azure AI Vision 4.0) "
            "generates human-readable descriptions of image content.",
            "easy",
        ),
        (
            "cv_02",
            "You need to detect and locate 20 custom product types on a conveyor "
            "belt. Which Azure service is most appropriate?",
            [
                "A. Azure AI Vision — Image Analysis (pre-built tags)",
                "B. Custom Vision — Object Detection project",
                "C. Azure AI Vision — Smart Crop",
                "D. Azure AI Face API",
            ],
            1,
            "Custom Vision Object Detection lets you train a model on your own labelled "
            "images to detect and locate custom objects.",
            "medium",
        ),
        (
            "cv_03",
            "Which API endpoint is used by the Azure AI Vision Read feature to "
            "asynchronously extract text from large documents?",
            [
                "A. POST /analyze",
                "B. POST /ocr",
                "C. POST /imageanalysis:analyze",
                "D. POST /vision/v3.2/read/analyze",
            ],
            3,
            "The Read (OCR) API uses the /vision/v3.2/read/analyze endpoint (or the "
            "newer /computervision/imageanalysis:analyze in v4.0) for high-accuracy "
            "text extraction from complex documents.",
            "hard",
        ),
        (
            "cv_04",
            "What type of output does the Azure AI Face API 'Verify' operation return?",
            [
                "A. A list of all faces detected in the image",
                "B. A boolean indicating whether two faces belong to the same person "
                   "and a confidence score",
                "C. Facial landmarks coordinates",
                "D. Emotion classification probabilities",
            ],
            1,
            "The Verify operation compares two faces and returns isIdentical (boolean) "
            "plus a confidence score.",
            "medium",
        ),
        (
            "cv_05",
            "Which Azure AI Video Indexer insight category identifies and transcribes "
            "spoken words in a video?",
            [
                "A. Visual labels",
                "B. Key frames",
                "C. Audio Transcription",
                "D. Object tracking",
            ],
            2,
            "Audio Transcription generates time-stamped transcripts of all speech in "
            "the video, supporting search and retrieval.",
            "easy",
        ),
    ],
    "nlp": [
        (
            "nlp_01",
            "Which Azure AI Language feature extracts structured data entities such "
            "as dates, people, and locations from unstructured text?",
            [
                "A. Sentiment Analysis",
                "B. Named Entity Recognition (NER)",
                "C. Text Summarization",
                "D. Language Detection",
            ],
            1,
            "NER identifies pre-defined entity categories (PII, dates, organisations, "
            "locations, etc.) in free-form text.",
            "easy",
        ),
        (
            "nlp_02",
            "A travel company wants to route customer complaints to the right support "
            "team based on the topic. Which feature of Azure AI Language should they use?",
            [
                "A. Sentiment Analysis",
                "B. Key Phrase Extraction",
                "C. Custom Text Classification",
                "D. Language Detection",
            ],
            2,
            "Custom Text Classification trains a multi-class or multi-label model on "
            "the company's own labelled tickets to route them accurately.",
            "medium",
        ),
        (
            "nlp_03",
            "In Conversational Language Understanding (CLU), what is an 'intent'?",
            [
                "A. A piece of information extracted from a user utterance",
                "B. The purpose or goal expressed in a user utterance",
                "C. A synonym list used to normalise vocabulary",
                "D. A pre-built entity category",
            ],
            1,
            "An intent represents the user's goal (e.g., BookFlight, CheckBalance). "
            "Entities are the extracted data values within that intent.",
            "easy",
        ),
        (
            "nlp_04",
            "Which Azure AI Language API operation generates an abstractive summary "
            "of a long document?",
            [
                "A. extractive summarization",
                "B. abstractive summarization",
                "C. conversation summarization",
                "D. key phrase extraction",
            ],
            1,
            "Abstractive summarization uses generative techniques to produce novel "
            "summary text rather than extracting sentences verbatim.",
            "hard",
        ),
        (
            "nlp_05",
            "The 'opinionMining' parameter in the Sentiment Analysis API enables which feature?",
            [
                "A. Document-level positive/negative scoring",
                "B. Per-sentence language detection",
                "C. Aspect-based sentiment — linking opinion to specific entities",
                "D. Sarcasm detection",
            ],
            2,
            "Opinion mining (aspect-based sentiment) provides sentiment polarity for "
            "specific aspects/entities within a sentence, e.g., 'food was great, "
            "service was slow'.",
            "hard",
        ),
    ],
    "document_intelligence": [
        (
            "di_01",
            "Which Azure AI Document Intelligence model is best for extracting "
            "key-value pairs from general-purpose forms without prior training?",
            [
                "A. Custom extraction model",
                "B. prebuilt-invoice",
                "C. prebuilt-document (General Document model)",
                "D. prebuilt-idDocument",
            ],
            2,
            "The prebuilt-document (General Document) model extracts key-value pairs, "
            "tables and entities from any form type without custom training.",
            "medium",
        ),
        (
            "di_02",
            "In Azure AI Search, what is the purpose of a 'skillset'?",
            [
                "A. Defining which fields to index",
                "B. Specifying the search algorithm",
                "C. Enriching documents with AI-extracted insights during indexing",
                "D. Configuring synonyms for semantic search",
            ],
            2,
            "A skillset chains AI skills (OCR, entity extraction, language detection, "
            "custom skills) that run during the indexing pipeline to enrich documents.",
            "medium",
        ),
        (
            "di_03",
            "Which Azure AI Search feature uses large language models to find "
            "semantically relevant results beyond keyword matching?",
            [
                "A. Full-text search (Lucene)",
                "B. Scoring profiles",
                "C. Semantic ranker",
                "D. Fuzzy matching",
            ],
            2,
            "Semantic ranker re-ranks results using deep learning to understand "
            "meaning and context, improving relevance beyond BM25 keyword scoring.",
            "medium",
        ),
        (
            "di_04",
            "A knowledge store in Azure AI Search stores enriched data in which "
            "storage destinations?",
            [
                "A. Azure SQL Database and Cosmos DB only",
                "B. Azure Blob Storage (projections) and Azure Table Storage",
                "C. Azure Data Lake Storage Gen2 only",
                "D. Azure Queue Storage",
            ],
            1,
            "Knowledge store projections can target Azure Blob Storage (for complex "
            "objects like images) and Azure Table Storage (for structured tabular data).",
            "hard",
        ),
        (
            "di_05",
            "What type of document layout analysis can the Azure AI Document "
            "Intelligence 'Layout' model perform?",
            [
                "A. Language translation of extracted text",
                "B. Sentiment analysis of extracted paragraphs",
                "C. Extraction of paragraphs, tables, selection marks, and reading order",
                "D. Signature detection only",
            ],
            2,
            "The Layout model identifies paragraphs, tables, selection marks (checkboxes), "
            "and the natural reading order of complex documents.",
            "medium",
        ),
    ],
    "conversational_ai": [
        (
            "ca_01",
            "Which service is used to host and manage a multi-turn chatbot deployed "
            "to multiple channels (Teams, Web Chat, Slack)?",
            [
                "A. Azure AI Language",
                "B. Azure Logic Apps",
                "C. Azure Bot Service",
                "D. Azure API Management",
            ],
            2,
            "Azure Bot Service provides the channel integration layer that connects "
            "a bot's logic to multiple client channels.",
            "easy",
        ),
        (
            "ca_02",
            "In Bot Framework Composer, what component defines conditional branching "
            "based on user input or variable values?",
            [
                "A. Trigger",
                "B. Action — Branch: If/Else",
                "C. Recognizer",
                "D. Dialog",
            ],
            1,
            "The 'Branch: If/Else' action in Composer conditionally executes different "
            "action sequences based on property expressions.",
            "medium",
        ),
        (
            "ca_03",
            "Which Bot Framework concept maps users' natural-language messages to "
            "specific handler methods in your bot code?",
            [
                "A. Activity handlers",
                "B. Middleware pipeline",
                "C. Adaptive Cards",
                "D. Memory scopes",
            ],
            0,
            "Activity handlers (e.g., onMessage, onMembersAdded) are methods on the "
            "ActivityHandler base class that dispatch incoming activities.",
            "medium",
        ),
        (
            "ca_04",
            "A bot must remember context from earlier in a conversation (multi-turn). "
            "Which Bot Framework memory scope stores data for the current conversation?",
            [
                "A. user scope",
                "B. turn scope",
                "C. conversation scope",
                "D. dialog scope",
            ],
            2,
            "Conversation scope persists data for the lifetime of an active conversation, "
            "making it ideal for multi-turn context retention.",
            "hard",
        ),
        (
            "ca_05",
            "Which feature of CLU (Conversational Language Understanding) allows "
            "you to add variations of entity values so the model recognises synonyms?",
            [
                "A. Prebuilt entities",
                "B. List entities with synonyms",
                "C. Regex entities",
                "D. ML entities",
            ],
            1,
            "List entities let you define canonical values plus synonym lists so the "
            "model recognises multiple surface forms of the same concept.",
            "medium",
        ),
    ],
    "generative_ai": [
        (
            "gen_01",
            "What prompt engineering technique helps a model perform a task by "
            "providing a few input-output examples in the prompt?",
            [
                "A. Zero-shot prompting",
                "B. Chain-of-thought prompting",
                "C. Few-shot prompting",
                "D. System message injection",
            ],
            2,
            "Few-shot prompting includes labelled examples (shots) in the prompt, "
            "helping the model understand the task format without fine-tuning.",
            "easy",
        ),
        (
            "gen_02",
            "Which Azure OpenAI parameter controls the randomness of generated "
            "tokens — higher values produce more creative, varied outputs?",
            [
                "A. max_tokens",
                "B. top_p (nucleus sampling)",
                "C. temperature",
                "D. presence_penalty",
            ],
            2,
            "Temperature scales the probability distribution over tokens. Higher values "
            "(e.g., 0.9) make outputs more diverse; lower values (e.g., 0.1) make them "
            "more deterministic.",
            "easy",
        ),
        (
            "gen_03",
            "In a RAG (Retrieval-Augmented Generation) architecture, what is the "
            "primary purpose of the retrieval step?",
            [
                "A. To fine-tune the base model on domain data",
                "B. To reduce hallucination by grounding responses in retrieved documents",
                "C. To compress the prompt to fit within the context window",
                "D. To translate non-English queries to English",
            ],
            1,
            "RAG retrieves relevant document chunks from a knowledge store and injects "
            "them into the prompt context, grounding the model's answer in factual sources.",
            "medium",
        ),
        (
            "gen_04",
            "Which Azure OpenAI feature restricts the model to only answer questions "
            "based on uploaded documents (your own data)?",
            [
                "A. Assistants API file search",
                "B. Azure OpenAI On Your Data",
                "C. Prompt flow grounding",
                "D. Azure AI Search semantic ranker",
            ],
            1,
            "'Azure OpenAI On Your Data' lets you connect Azure AI Search or Blob Storage "
            "so the model answers only from your uploaded documents, reducing hallucination.",
            "medium",
        ),
        (
            "gen_05",
            "A developer needs to block generation of violent or sexual content in an "
            "Azure OpenAI deployment. Which service provides configurable content filters?",
            [
                "A. Azure AI Content Safety",
                "B. Azure Policy",
                "C. Azure OpenAI built-in content filtering (harm categories)",
                "D. Microsoft Defender for Cloud",
            ],
            2,
            "Azure OpenAI's built-in content filtering allows configuring severity "
            "thresholds for hate, self-harm, sexual, and violence categories at the "
            "deployment level.",
            "medium",
        ),
    ],
}


class AssessmentAgent:
    """
    Block 2 — Readiness Assessment Agent.

    Samples questions from the mock bank (weighted by exam domain weight),
    presents them in random order, and scores the submission.

    Usage::

        agent      = AssessmentAgent()
        assessment = agent.generate(profile, n_questions=10)
        result     = agent.evaluate(assessment, answers)   # answers: list[int]
    """

    PASS_MARK_PCT: float = 60.0

    def generate(self, profile, n_questions: int = 10) -> Assessment:
        """Return an `Assessment` of `n_questions` questions, domain-weighted."""
        from cert_prep.models import EXAM_DOMAINS

        # Build domain → weight map
        weight_map = {d["id"]: d["weight"] for d in EXAM_DOMAINS}

        # Exclude skipped domains
        skip_ids = set(profile.domains_to_skip())
        domain_by_id = {dp.domain_id: dp for dp in profile.domain_profiles}

        # Allocate question counts proportional to domain weight
        active_domains = [
            d_id for d_id in weight_map if d_id not in skip_ids
        ]
        raw_alloc = {
            d: weight_map[d] for d in active_domains
        }
        total_w = sum(raw_alloc.values()) or 1.0
        alloc = {d: max(1, round(n_questions * w / total_w)) for d, w in raw_alloc.items()}

        # Fix rounding to ensure exactly n_questions
        while sum(alloc.values()) > n_questions:
            max_d = max(alloc, key=alloc.get)
            alloc[max_d] -= 1
        while sum(alloc.values()) < n_questions:
            min_d = min(alloc, key=alloc.get)
            alloc[min_d] += 1

        selected: list[QuizQuestion] = []
        for d_id, count in alloc.items():
            pool = _QUESTION_BANK.get(d_id, [])
            if not pool:
                continue
            dp = domain_by_id.get(d_id)
            d_name = dp.domain_name if dp else d_id

            sampled = random.sample(pool, min(count, len(pool)))
            for q in sampled:
                q_id, question, options, correct_idx, explanation, diff = q
                selected.append(QuizQuestion(
                    id=q_id,
                    domain_id=d_id,
                    domain_name=d_name,
                    question=question,
                    options=options,
                    correct_index=correct_idx,
                    explanation=explanation,
                    difficulty=diff,
                ))

        random.shuffle(selected)

        return Assessment(
            student_name=profile.student_name,
            exam_target=profile.exam_target,
            questions=selected,
            total_marks=len(selected),
            pass_mark_pct=self.PASS_MARK_PCT,
        )

    def evaluate(self, assessment: Assessment, answers: list[int]) -> AssessmentResult:
        """
        Score the assessment.

        Parameters
        ----------
        assessment : Assessment  — the generated assessment object
        answers    : list[int]   — 0-based option index chosen for each question,
                                   in the same order as assessment.questions

        Returns
        -------
        AssessmentResult
        """
        if len(answers) != len(assessment.questions):
            raise ValueError(
                f"Expected {len(assessment.questions)} answers, got {len(answers)}"
            )

        feedback: list[QuestionFeedback] = []
        domain_correct: dict[str, int] = {}
        domain_total:   dict[str, int] = {}
        correct_count   = 0

        for q, chosen in zip(assessment.questions, answers):
            is_correct = (chosen == q.correct_index)
            if is_correct:
                correct_count += 1

            domain_correct[q.domain_id] = domain_correct.get(q.domain_id, 0) + int(is_correct)
            domain_total[q.domain_id]   = domain_total.get(q.domain_id, 0) + 1

            feedback.append(QuestionFeedback(
                question_id=q.id,
                correct=is_correct,
                learner_index=chosen,
                correct_index=q.correct_index,
                explanation=q.explanation,
            ))

        score_pct = (correct_count / len(assessment.questions)) * 100 if assessment.questions else 0
        passed = score_pct >= assessment.pass_mark_pct

        domain_scores = {
            d: (domain_correct.get(d, 0) / domain_total[d]) * 100
            for d in domain_total
        }

        # Verdict
        if score_pct >= 80:
            verdict = "Excellent — exam ready with high confidence."
        elif score_pct >= 60:
            verdict = "Pass — review weak domains before booking exam."
        elif score_pct >= 40:
            verdict = "Near-miss — focused remediation recommended."
        else:
            verdict = "Needs significant study — revisit core domains."

        # Weak domain list for recommendation
        weak_domains = sorted(
            [d for d, s in domain_scores.items() if s < 60],
            key=lambda d: domain_scores[d],
        )
        rec = (
            f"Focus on: {', '.join(weak_domains)}" if weak_domains
            else "All domains passed — consider booking the exam."
        )

        return AssessmentResult(
            student_name=assessment.student_name,
            exam_target=assessment.exam_target,
            score_pct=score_pct,
            passed=passed,
            correct_count=correct_count,
            total_count=len(assessment.questions),
            domain_scores=domain_scores,
            feedback=feedback,
            verdict=verdict,
            recommendation=rec,
        )
