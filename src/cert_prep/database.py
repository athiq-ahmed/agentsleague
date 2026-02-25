"""
cert_prep/database.py – SQLite persistence layer for student data.

Stores learner profiles, progress snapshots, assessments, and study plans
in a local SQLite database so that returning users can resume their journey
and admins can review all student data.
"""

from __future__ import annotations

import json
import sqlite3
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

# Database file lives next to the workspace root
_DB_DIR = Path(__file__).resolve().parent.parent.parent
_DB_PATH = _DB_DIR / "cert_prep_data.db"


def _get_conn() -> sqlite3.Connection:
    """Return a connection with row_factory set."""
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    """Create tables if they don't exist."""
    conn = _get_conn()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS students (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        name            TEXT    UNIQUE NOT NULL,
        pin             TEXT    NOT NULL DEFAULT '1234',
        user_type       TEXT    DEFAULT 'learner',
        exam_target     TEXT,
        profile_json    TEXT,
        raw_input_json  TEXT,
        plan_json       TEXT,
        learning_path_json TEXT,
        progress_snapshot_json  TEXT,
        progress_assessment_json TEXT,
        assessment_json       TEXT,
        assessment_result_json TEXT,
        cert_recommendation_json TEXT,
        trace_json      TEXT,
        badge           TEXT,
        created_at      TEXT    DEFAULT (datetime('now')),
        updated_at      TEXT    DEFAULT (datetime('now'))
    );
    """)
    conn.commit()
    conn.close()


# ─── Student CRUD ─────────────────────────────────────────────────────────────

def get_student(name: str) -> Optional[dict]:
    """Fetch a student by name. Returns dict or None."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM students WHERE name = ?", (name,)).fetchone()
    conn.close()
    if row is None:
        return None
    return dict(row)


def get_all_students() -> list[dict]:
    """Fetch all students for the admin dashboard."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM students ORDER BY updated_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_student(name: str, pin: str = "1234", user_type: str = "learner") -> int:
    """Create a new student record, return the id."""
    conn = _get_conn()
    cur = conn.execute(
        "INSERT INTO students (name, pin, user_type) VALUES (?, ?, ?)",
        (name, pin, user_type),
    )
    conn.commit()
    student_id = cur.lastrowid
    conn.close()
    return student_id


def upsert_student(name: str, pin: str = "1234", user_type: str = "learner") -> int:
    """Create or get existing student, return id."""
    existing = get_student(name)
    if existing:
        return existing["id"]
    return create_student(name, pin, user_type)


def save_profile(name: str, profile_json: str, raw_input_json: str,
                 exam_target: str, badge: str = "") -> None:
    """Save or update the learner profile for a student."""
    conn = _get_conn()
    conn.execute("""
        UPDATE students SET
            profile_json = ?,
            raw_input_json = ?,
            exam_target = ?,
            badge = ?,
            updated_at = datetime('now')
        WHERE name = ?
    """, (profile_json, raw_input_json, exam_target, badge, name))
    conn.commit()
    conn.close()


def save_plan(name: str, plan_json: str) -> None:
    """Save the study plan for a student."""
    conn = _get_conn()
    conn.execute("""
        UPDATE students SET plan_json = ?, updated_at = datetime('now')
        WHERE name = ?
    """, (plan_json, name))
    conn.commit()
    conn.close()


def save_learning_path(name: str, learning_path_json: str) -> None:
    """Save the learning path for a student."""
    conn = _get_conn()
    conn.execute("""
        UPDATE students SET learning_path_json = ?, updated_at = datetime('now')
        WHERE name = ?
    """, (learning_path_json, name))
    conn.commit()
    conn.close()


def save_progress(name: str, snapshot_json: str, assessment_json: str) -> None:
    """Save progress snapshot and readiness assessment."""
    conn = _get_conn()
    conn.execute("""
        UPDATE students SET
            progress_snapshot_json = ?,
            progress_assessment_json = ?,
            updated_at = datetime('now')
        WHERE name = ?
    """, (snapshot_json, assessment_json, name))
    conn.commit()
    conn.close()


def save_assessment(name: str, assessment_json: str, result_json: str = None) -> None:
    """Save the quiz assessment and optionally the result."""
    conn = _get_conn()
    conn.execute("""
        UPDATE students SET
            assessment_json = ?,
            assessment_result_json = ?,
            updated_at = datetime('now')
        WHERE name = ?
    """, (assessment_json, result_json, name))
    conn.commit()
    conn.close()


def save_cert_recommendation(name: str, rec_json: str) -> None:
    """Save certification recommendation."""
    conn = _get_conn()
    conn.execute("""
        UPDATE students SET cert_recommendation_json = ?, updated_at = datetime('now')
        WHERE name = ?
    """, (rec_json, name))
    conn.commit()
    conn.close()


def save_trace(name: str, trace_json: str) -> None:
    """Save agent trace data."""
    conn = _get_conn()
    conn.execute("""
        UPDATE students SET trace_json = ?, updated_at = datetime('now')
        WHERE name = ?
    """, (trace_json, name))
    conn.commit()
    conn.close()


def delete_student(name: str) -> None:
    """Delete a student record."""
    conn = _get_conn()
    conn.execute("DELETE FROM students WHERE name = ?", (name,))
    conn.commit()
    conn.close()


# ─── Demo seed data ───────────────────────────────────────────────────────────

_SEED_STUDENTS: list[dict] = [
    # ── Student 1: Layla Hassan — AI-102, Advanced Azure, full pipeline, GO ────
    {
        "name": "Layla Hassan",
        "pin": "1234",
        "exam_target": "AI-102",
        "badge": "🏅",
        "profile_json": json.dumps({
            "student_name": "Layla Hassan",
            "exam_target": "AI-102",
            "experience_level": "advanced_azure",
            "learning_style": "lab_first",
            "hours_per_week": 12.0,
            "weeks_available": 6,
            "total_budget_hours": 72.0,
            "domain_profiles": [
                {"domain_id": "plan_manage",          "domain_name": "Plan & Manage Azure AI Solutions",              "knowledge_level": "strong",   "confidence_score": 0.85, "skip_recommended": False, "notes": "Strong Azure admin background; resource provisioning well understood."},
                {"domain_id": "computer_vision",      "domain_name": "Implement Computer Vision Solutions",           "knowledge_level": "moderate", "confidence_score": 0.65, "skip_recommended": False, "notes": "Used Azure AI Vision in a PoC; needs depth on Custom Vision."},
                {"domain_id": "nlp",                  "domain_name": "Implement NLP Solutions",                      "knowledge_level": "moderate", "confidence_score": 0.70, "skip_recommended": False, "notes": "Familiar with Language Studio; CLU needs more practice."},
                {"domain_id": "document_intelligence","domain_name": "Implement Document Intelligence & Knowledge Mining","knowledge_level": "weak","confidence_score": 0.45, "skip_recommended": False, "notes": "Limited hands-on with Form Recognizer; plan extra lab time."},
                {"domain_id": "conversational_ai",    "domain_name": "Implement Conversational AI Solutions",         "knowledge_level": "weak",     "confidence_score": 0.40, "skip_recommended": False, "notes": "Bot Service unfamiliar; flag as risk domain."},
                {"domain_id": "generative_ai",        "domain_name": "Implement Generative AI Solutions",             "knowledge_level": "moderate", "confidence_score": 0.60, "skip_recommended": False, "notes": "Used Azure OpenAI API; prompt engineering needs refinement."}
            ],
            "modules_to_skip": [],
            "risk_domains": ["document_intelligence", "conversational_ai"],
            "analogy_map": {"RBAC": "Azure AI resource scope management"},
            "recommended_approach": "Prioritise Document Intelligence and Conversational AI labs first. Layla's strong Azure foundation means governance and deployment topics can be covered quickly.",
            "engagement_notes": "Weekly lab challenges recommended. Layla is goal-oriented; use pass/fail milestones to maintain momentum."
        }),
        "raw_input_json": json.dumps({
            "student_name": "Layla Hassan",
            "exam_target": "AI-102",
            "background_text": "5 years Azure infrastructure, 1 year using Azure AI services in production",
            "existing_certs": ["AZ-104", "AZ-305"],
            "hours_per_week": 12.0,
            "weeks_available": 6,
            "concern_topics": ["Bot Service", "Form Recognizer"],
            "preferred_style": "Hands-on labs before theory",
            "goal_text": "Get promoted to AI Engineer role",
            "email": ""
        }),
        "plan_json": json.dumps({
            "weeks": [
                {"week": 1, "focus": "Plan & Manage + Computer Vision labs", "hours": 12},
                {"week": 2, "focus": "NLP Solutions — Language Studio deep dive", "hours": 12},
                {"week": 3, "focus": "Document Intelligence labs + Form Recognizer", "hours": 12},
                {"week": 4, "focus": "Conversational AI — Bot Framework Composer", "hours": 12},
                {"week": 5, "focus": "Generative AI — Azure OpenAI & RAG patterns", "hours": 12},
                {"week": 6, "focus": "Full mock exams + weak area review", "hours": 12}
            ],
            "total_hours": 72,
            "strategy": "Lab-first with theory consolidation on weekends."
        }),
        "progress_snapshot_json": json.dumps({
            "domains_completed": ["plan_manage", "computer_vision", "nlp", "generative_ai"],
            "domains_in_progress": ["document_intelligence"],
            "domains_not_started": ["conversational_ai"],
            "hours_logged": 58,
            "labs_completed": 14
        }),
        "progress_assessment_json": json.dumps({
            "readiness_pct": 78,
            "exam_go_nogo": "GO",
            "strengths": ["Plan & Manage", "NLP"],
            "gaps": ["Conversational AI"],
            "recommended_action": "Complete Bot Service lab then book exam."
        }),
        "assessment_json": json.dumps({"questions_attempted": 40, "correct": 34}),
        "assessment_result_json": json.dumps({"score_pct": 85, "passed": True}),
        "cert_recommendation_json": json.dumps({
            "primary": "AI-102",
            "next_recommended": "DP-100",
            "rationale": "Strong foundation; Data Scientist cert is a natural progression."
        }),
    },
    # ── Student 2: Marcus Chen — DP-100, Intermediate, partial completion, CONDITIONAL GO ──
    {
        "name": "Marcus Chen",
        "pin": "1234",
        "exam_target": "DP-100",
        "badge": "📊",
        "profile_json": json.dumps({
            "student_name": "Marcus Chen",
            "exam_target": "DP-100",
            "experience_level": "intermediate",
            "learning_style": "adaptive",
            "hours_per_week": 8.0,
            "weeks_available": 10,
            "total_budget_hours": 80.0,
            "domain_profiles": [
                {"domain_id": "ml_solution_design",  "domain_name": "Design & Prepare an ML Solution",   "knowledge_level": "moderate", "confidence_score": 0.60, "skip_recommended": False, "notes": "Familiar with Azure ML workspace; compute setup needs practice."},
                {"domain_id": "explore_train_models", "domain_name": "Explore Data & Train Models",        "knowledge_level": "strong",   "confidence_score": 0.82, "skip_recommended": True,  "notes": "Data science background; pandas, scikit-learn proficient."},
                {"domain_id": "prepare_deployment",   "domain_name": "Prepare a Model for Deployment",    "knowledge_level": "weak",     "confidence_score": 0.38, "skip_recommended": False, "notes": "MLflow and model packages are unfamiliar territory."},
                {"domain_id": "deploy_retrain",       "domain_name": "Deploy & Retrain a Model",          "knowledge_level": "weak",     "confidence_score": 0.35, "skip_recommended": False, "notes": "Online endpoints need hands-on. Flag as highest risk."}
            ],
            "modules_to_skip": ["Explore Data & Train Models"],
            "risk_domains": ["prepare_deployment", "deploy_retrain"],
            "analogy_map": {"scikit-learn pipelines": "Azure ML pipelines"},
            "recommended_approach": "Skip data exploration since Marcus has strong ML background. Focus weeks 1–6 on deployment and retraining patterns.",
            "engagement_notes": "Marcus is self-directed; provide weekly challenge labs and monitor progress checkpoints."
        }),
        "raw_input_json": json.dumps({
            "student_name": "Marcus Chen",
            "exam_target": "DP-100",
            "background_text": "Data scientist with 3 years Python and ML experience, new to Azure ML platform",
            "existing_certs": ["DP-900"],
            "hours_per_week": 8.0,
            "weeks_available": 10,
            "concern_topics": ["MLflow", "Managed endpoints", "Data drift"],
            "preferred_style": "Mixed theory and practice",
            "goal_text": "Certify cloud ML skills for a new job application",
            "email": ""
        }),
        "plan_json": json.dumps({
            "weeks": [
                {"week": 1, "focus": "Azure ML workspace + compute deep dive", "hours": 8},
                {"week": 2, "focus": "AutoML and responsible AI dashboards",    "hours": 8},
                {"week": 3, "focus": "MLflow tracking and model registration",  "hours": 8},
                {"week": 4, "focus": "Scoring scripts and deployment packages", "hours": 8},
                {"week": 5, "focus": "Managed endpoints — online and batch",    "hours": 8},
                {"week": 6, "focus": "Model monitoring and data drift labs",    "hours": 8},
                {"week": 7, "focus": "Retraining pipelines",                   "hours": 8},
                {"week": 8, "focus": "Mock exams and gap analysis",             "hours": 8},
                {"week": 9, "focus": "Weak area remediation",                  "hours": 8},
                {"week": 10,"focus": "Final practice tests",                   "hours": 8}
            ],
            "total_hours": 80,
            "strategy": "Skip known-strong areas; double down on deployment track."
        }),
        "progress_snapshot_json": json.dumps({
            "domains_completed": ["ml_solution_design", "explore_train_models"],
            "domains_in_progress": ["prepare_deployment"],
            "domains_not_started": ["deploy_retrain"],
            "hours_logged": 40,
            "labs_completed": 9
        }),
        "progress_assessment_json": json.dumps({
            "readiness_pct": 62,
            "exam_go_nogo": "CONDITIONAL GO",
            "strengths": ["Explore Data & Train Models"],
            "gaps": ["Deploy & Retrain a Model"],
            "recommended_action": "Complete managed endpoints module before booking."
        }),
        "assessment_json": json.dumps({"questions_attempted": 35, "correct": 25}),
        "assessment_result_json": json.dumps({"score_pct": 71, "passed": True}),
        "cert_recommendation_json": json.dumps({
            "primary": "DP-100",
            "next_recommended": "AI-102",
            "rationale": "After DP-100, Azure AI Engineer cert would complete the ML + AI portfolio."
        }),
    },
    # ── Student 3: Priya Sharma — AI-900, Beginner, full pipeline, GO ──────────
    {
        "name": "Priya Sharma",
        "pin": "1234",
        "exam_target": "AI-900",
        "badge": "🌟",
        "profile_json": json.dumps({
            "student_name": "Priya Sharma",
            "exam_target": "AI-900",
            "experience_level": "beginner",
            "learning_style": "linear",
            "hours_per_week": 6.0,
            "weeks_available": 5,
            "total_budget_hours": 30.0,
            "domain_profiles": [
                {"domain_id": "ai_workloads",       "domain_name": "AI Workloads & Considerations",          "knowledge_level": "weak",     "confidence_score": 0.42, "skip_recommended": False, "notes": "Basic awareness of AI from news; no hands-on experience."},
                {"domain_id": "ml_fundamentals",    "domain_name": "Fundamental Principles of ML on Azure",  "knowledge_level": "unknown",  "confidence_score": 0.25, "skip_recommended": False, "notes": "No prior ML exposure; start from fundamentals."},
                {"domain_id": "cv_fundamentals",    "domain_name": "Computer Vision Workloads on Azure",      "knowledge_level": "unknown",  "confidence_score": 0.20, "skip_recommended": False, "notes": "Unfamiliar; needs conceptual grounding first."},
                {"domain_id": "nlp_fundamentals",   "domain_name": "NLP Workloads on Azure",                 "knowledge_level": "weak",     "confidence_score": 0.35, "skip_recommended": False, "notes": "Uses chatbots daily; understands intent at a user level."},
                {"domain_id": "genai_fundamentals", "domain_name": "Generative AI Workloads on Azure",        "knowledge_level": "weak",     "confidence_score": 0.38, "skip_recommended": False, "notes": "Familiar with ChatGPT concepts; needs Azure-specific knowledge."}
            ],
            "modules_to_skip": [],
            "risk_domains": ["ml_fundamentals", "cv_fundamentals"],
            "analogy_map": {},
            "recommended_approach": "Start with AI Workloads concepts to build vocabulary. Use Microsoft Learn modules in sequence with daily 1-hour sessions.",
            "engagement_notes": "Priya is motivated by career change. Short daily sessions with milestone celebrations will keep engagement high."
        }),
        "raw_input_json": json.dumps({
            "student_name": "Priya Sharma",
            "exam_target": "AI-900",
            "background_text": "Business analyst with no prior coding or cloud experience, curious about AI",
            "existing_certs": [],
            "hours_per_week": 6.0,
            "weeks_available": 5,
            "concern_topics": ["Machine learning", "Neural networks"],
            "preferred_style": "Step-by-step structured learning",
            "goal_text": "Start AI career transition from business analysis",
            "email": ""
        }),
        "plan_json": json.dumps({
            "weeks": [
                {"week": 1, "focus": "AI concepts and workload types",         "hours": 6},
                {"week": 2, "focus": "ML fundamentals on Azure ML Studio",     "hours": 6},
                {"week": 3, "focus": "Computer Vision + NLP demo labs",        "hours": 6},
                {"week": 4, "focus": "Generative AI and Azure OpenAI overview","hours": 6},
                {"week": 5, "focus": "Practice tests and exam readiness",      "hours": 6}
            ],
            "total_hours": 30,
            "strategy": "Microsoft Learn path with short daily sessions; no coding required."
        }),
        "progress_snapshot_json": json.dumps({
            "domains_completed": ["ai_workloads", "ml_fundamentals", "cv_fundamentals", "nlp_fundamentals"],
            "domains_in_progress": ["genai_fundamentals"],
            "domains_not_started": [],
            "hours_logged": 27,
            "labs_completed": 8
        }),
        "progress_assessment_json": json.dumps({
            "readiness_pct": 83,
            "exam_go_nogo": "GO",
            "strengths": ["AI Workloads", "NLP Fundamentals"],
            "gaps": [],
            "recommended_action": "Complete GenAI module then book the exam — you're ready!"
        }),
        "assessment_json": json.dumps({"questions_attempted": 30, "correct": 26}),
        "assessment_result_json": json.dumps({"score_pct": 87, "passed": True}),
        "cert_recommendation_json": json.dumps({
            "primary": "AI-900",
            "next_recommended": "AI-102",
            "rationale": "Great foundation. AI-102 is the logical next step after AI-900."
        }),
    },
    # ── Student 4: James O'Brien — AZ-305, Advanced Azure, progress only, NOT YET ─────
    {
        "name": "James O'Brien",
        "pin": "1234",
        "exam_target": "AZ-305",
        "badge": "",
        "profile_json": json.dumps({
            "student_name": "James O'Brien",
            "exam_target": "AZ-305",
            "experience_level": "advanced_azure",
            "learning_style": "reference",
            "hours_per_week": 10.0,
            "weeks_available": 8,
            "total_budget_hours": 80.0,
            "domain_profiles": [
                {"domain_id": "identity_governance",    "domain_name": "Design Identity, Governance & Monitoring",     "knowledge_level": "strong",   "confidence_score": 0.88, "skip_recommended": True,  "notes": "Entra ID and RBAC are daily tasks; high confidence."},
                {"domain_id": "data_storage_solutions", "domain_name": "Design Data Storage Solutions",                "knowledge_level": "moderate", "confidence_score": 0.58, "skip_recommended": False, "notes": "Storage accounts familiar; Cosmos DB and SQL HA patterns need review."},
                {"domain_id": "business_continuity",    "domain_name": "Design Business Continuity Solutions",         "knowledge_level": "moderate", "confidence_score": 0.55, "skip_recommended": False, "notes": "Backup and ASR concepts known; multi-region failover design is weak."},
                {"domain_id": "infrastructure_solutions","domain_name": "Design Infrastructure Solutions",             "knowledge_level": "strong",   "confidence_score": 0.78, "skip_recommended": True,  "notes": "Landing zones and hub-spoke well practiced."}
            ],
            "modules_to_skip": ["Design Identity, Governance & Monitoring", "Design Infrastructure Solutions"],
            "risk_domains": ["business_continuity"],
            "analogy_map": {"on-prem AD": "Microsoft Entra ID"},
            "recommended_approach": "Skip identity and infrastructure tracks. Focus on data storage HA patterns and multi-region business continuity design.",
            "engagement_notes": "James is time-constrained. Provide concise reference cards and scenario-based questions rather than lengthy reading."
        }),
        "raw_input_json": json.dumps({
            "student_name": "James O'Brien",
            "exam_target": "AZ-305",
            "background_text": "Senior Azure architect with 7 years experience; strong on IaC and governance",
            "existing_certs": ["AZ-104", "AZ-500", "AZ-204"],
            "hours_per_week": 10.0,
            "weeks_available": 8,
            "concern_topics": ["Multi-region failover", "Cosmos DB consistency levels"],
            "preferred_style": "Quick reference cards and scenario questions",
            "goal_text": "Complete the Architect Expert path for client credibility",
            "email": ""
        }),
        "plan_json": json.dumps({
            "weeks": [
                {"week": 1, "focus": "Data Storage — Cosmos DB and SQL HA",       "hours": 10},
                {"week": 2, "focus": "Business Continuity — multi-region design",  "hours": 10},
                {"week": 3, "focus": "ASR + Backup + Traffic Manager patterns",    "hours": 10},
                {"week": 4, "focus": "Scenario-based mock questions — data+BC",    "hours": 10},
                {"week": 5, "focus": "Full mock exam 1 + gap analysis",            "hours": 10},
                {"week": 6, "focus": "Targeted remediation — weak scenarios",      "hours": 10},
                {"week": 7, "focus": "Full mock exam 2",                           "hours": 10},
                {"week": 8, "focus": "Final review and exam booking",              "hours": 10}
            ],
            "total_hours": 80,
            "strategy": "Skip known-strong domains. Scenario-based learning throughout."
        }),
        "progress_snapshot_json": json.dumps({
            "domains_completed": ["identity_governance", "infrastructure_solutions"],
            "domains_in_progress": ["data_storage_solutions"],
            "domains_not_started": ["business_continuity"],
            "hours_logged": 22,
            "labs_completed": 5
        }),
        "progress_assessment_json": json.dumps({
            "readiness_pct": 48,
            "exam_go_nogo": "NOT YET",
            "strengths": ["Identity & Governance", "Infrastructure"],
            "gaps": ["Business Continuity", "Multi-region data patterns"],
            "recommended_action": "Complete business continuity and data HA modules before attempting the exam."
        }),
        "assessment_json": None,
        "assessment_result_json": None,
        "cert_recommendation_json": json.dumps({
            "primary": "AZ-305",
            "next_recommended": "AZ-400",
            "rationale": "DevOps Engineer Expert would round out the architecture + delivery portfolio."
        }),
    },
    # ── Student 5: Sofia Rodriguez — AI-102, Intermediate, full pipeline, CONDITIONAL GO ──
    {
        "name": "Sofia Rodriguez",
        "pin": "1234",
        "exam_target": "AI-102",
        "badge": "🎯",
        "profile_json": json.dumps({
            "student_name": "Sofia Rodriguez",
            "exam_target": "AI-102",
            "experience_level": "intermediate",
            "learning_style": "adaptive",
            "hours_per_week": 10.0,
            "weeks_available": 8,
            "total_budget_hours": 80.0,
            "domain_profiles": [
                {"domain_id": "plan_manage",          "domain_name": "Plan & Manage Azure AI Solutions",              "knowledge_level": "moderate", "confidence_score": 0.62, "skip_recommended": False, "notes": "Some Azure governance exposure from cloud ops role."},
                {"domain_id": "computer_vision",      "domain_name": "Implement Computer Vision Solutions",           "knowledge_level": "moderate", "confidence_score": 0.68, "skip_recommended": False, "notes": "Worked with Cognitive Services Vision API in a hackathon."},
                {"domain_id": "nlp",                  "domain_name": "Implement NLP Solutions",                      "knowledge_level": "strong",   "confidence_score": 0.80, "skip_recommended": True,  "notes": "NLP specialist background; CLU and QnA Maker well understood."},
                {"domain_id": "document_intelligence","domain_name": "Implement Document Intelligence & Knowledge Mining","knowledge_level": "weak","confidence_score": 0.40, "skip_recommended": False, "notes": "No prior Document Intelligence experience."},
                {"domain_id": "conversational_ai",    "domain_name": "Implement Conversational AI Solutions",         "knowledge_level": "moderate", "confidence_score": 0.55, "skip_recommended": False, "notes": "Built Power Virtual Agents bot; Bot Framework needs study."},
                {"domain_id": "generative_ai",        "domain_name": "Implement Generative AI Solutions",             "knowledge_level": "moderate", "confidence_score": 0.65, "skip_recommended": False, "notes": "Experimenting with Azure OpenAI; RAG patterns unfamiliar."}
            ],
            "modules_to_skip": ["Implement NLP Solutions"],
            "risk_domains": ["document_intelligence"],
            "analogy_map": {"spaCy NER": "Azure AI Language NER"},
            "recommended_approach": "Skip NLP track given strong background. Concentrate on Document Intelligence and RAG patterns for GenAI.",
            "engagement_notes": "Sofia learns best with real-world scenarios. Link all labs to industry use cases."
        }),
        "raw_input_json": json.dumps({
            "student_name": "Sofia Rodriguez",
            "exam_target": "AI-102",
            "background_text": "NLP researcher with 4 years Python, transitioning to Azure cloud AI role",
            "existing_certs": ["AZ-900"],
            "hours_per_week": 10.0,
            "weeks_available": 8,
            "concern_topics": ["Document Intelligence", "Azure AI Search", "RAG"],
            "preferred_style": "Real-world scenario labs",
            "goal_text": "Move from research to industry AI engineering",
            "email": ""
        }),
        "plan_json": json.dumps({
            "weeks": [
                {"week": 1, "focus": "Plan & Manage governance + Computer Vision labs", "hours": 10},
                {"week": 2, "focus": "Document Intelligence — Form Recognizer deep dive","hours": 10},
                {"week": 3, "focus": "Azure AI Search and knowledge mining",             "hours": 10},
                {"week": 4, "focus": "Conversational AI — Bot Framework + CLU channels", "hours": 10},
                {"week": 5, "focus": "Generative AI — Azure OpenAI + RAG patterns",      "hours": 10},
                {"week": 6, "focus": "Mock exams + targeted review",                     "hours": 10},
                {"week": 7, "focus": "Weak area deep dive — Document Intelligence",      "hours": 10},
                {"week": 8, "focus": "Final mock exam and exam booking",                 "hours": 10}
            ],
            "total_hours": 80,
            "strategy": "Scenario-based labs; skip NLP to gain extra time for Doc Intelligence."
        }),
        "progress_snapshot_json": json.dumps({
            "domains_completed": ["plan_manage", "computer_vision", "nlp", "conversational_ai"],
            "domains_in_progress": ["document_intelligence"],
            "domains_not_started": ["generative_ai"],
            "hours_logged": 55,
            "labs_completed": 12
        }),
        "progress_assessment_json": json.dumps({
            "readiness_pct": 67,
            "exam_go_nogo": "CONDITIONAL GO",
            "strengths": ["NLP Solutions", "Computer Vision"],
            "gaps": ["Document Intelligence", "Generative AI"],
            "recommended_action": "Complete GenAI module and run one full mock exam before booking."
        }),
        "assessment_json": json.dumps({"questions_attempted": 40, "correct": 29}),
        "assessment_result_json": json.dumps({"score_pct": 73, "passed": True}),
        "cert_recommendation_json": json.dumps({
            "primary": "AI-102",
            "next_recommended": "DP-100",
            "rationale": "Combining AI Engineer with Data Scientist cert strengthens ML + AI profile."
        }),
    },
    # ── Student 6: Tariq Ibrahim — AZ-900, Beginner, profile only ──────────────
    {
        "name": "Tariq Ibrahim",
        "pin": "1234",
        "exam_target": "AZ-900",
        "badge": "",
        "profile_json": json.dumps({
            "student_name": "Tariq Ibrahim",
            "exam_target": "AZ-900",
            "experience_level": "beginner",
            "learning_style": "linear",
            "hours_per_week": 5.0,
            "weeks_available": 4,
            "total_budget_hours": 20.0,
            "domain_profiles": [
                {"domain_id": "cloud_concepts",        "domain_name": "Cloud Concepts",                         "knowledge_level": "weak",    "confidence_score": 0.35, "skip_recommended": False, "notes": "Basic awareness of cloud from personal use; no formal training."},
                {"domain_id": "azure_architecture",    "domain_name": "Azure Architecture & Services",          "knowledge_level": "unknown", "confidence_score": 0.18, "skip_recommended": False, "notes": "No prior Azure exposure; start from zero."},
                {"domain_id": "azure_management",      "domain_name": "Azure Management & Governance",          "knowledge_level": "unknown", "confidence_score": 0.15, "skip_recommended": False, "notes": "Governance entirely new; needs foundational reading first."}
            ],
            "modules_to_skip": [],
            "risk_domains": ["azure_architecture", "azure_management"],
            "analogy_map": {},
            "recommended_approach": "Follow the Microsoft Learn AZ-900 learning path in sequence. 5 hours per week over 4 weeks is achievable for this fundamentals exam.",
            "engagement_notes": "Tariq is new to cloud; use relatable analogies and keep sessions short (45–60 min max) to avoid overwhelm."
        }),
        "raw_input_json": json.dumps({
            "student_name": "Tariq Ibrahim",
            "exam_target": "AZ-900",
            "background_text": "IT support technician with no prior cloud certification, wants to move into cloud ops",
            "existing_certs": [],
            "hours_per_week": 5.0,
            "weeks_available": 4,
            "concern_topics": ["Azure pricing", "Compliance"],
            "preferred_style": "Short daily study sessions",
            "goal_text": "Get first cloud certification to transition into cloud support role",
            "email": ""
        }),
        "plan_json": json.dumps({
            "weeks": [
                {"week": 1, "focus": "Cloud concepts — SaaS/IaaS/PaaS, benefits of cloud", "hours": 5},
                {"week": 2, "focus": "Azure core services — compute, storage, networking",   "hours": 5},
                {"week": 3, "focus": "Azure management — portal, CLI, pricing, SLAs",        "hours": 5},
                {"week": 4, "focus": "Practice tests + exam readiness review",               "hours": 5}
            ],
            "total_hours": 20,
            "strategy": "Microsoft Learn path + daily 45-min sessions. Take practice test on day 25."
        }),
        "progress_snapshot_json": None,
        "progress_assessment_json": None,
        "assessment_json": None,
        "assessment_result_json": None,
        "cert_recommendation_json": None,
    },
]


def seed_demo_students() -> None:
    """Populate the database with demo student records if it is empty.

    Called automatically by init_db() on every startup so that Streamlit Cloud
    deployments always show meaningful data in the admin dashboard even after
    the ephemeral filesystem is wiped.
    """
    conn = _get_conn()
    count = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    conn.close()
    if count > 0:
        return  # real data already present — do not overwrite

    now = datetime.utcnow()
    offsets_days = [0, -3, -7, -14, -21, -28]
    for student, offset in zip(_SEED_STUDENTS, offsets_days):
        ts = now.replace(
            hour=14, minute=0, second=0, microsecond=0
        )
        # Vary timestamps so the dashboard list looks natural
        from datetime import timedelta
        ts = ts - timedelta(days=abs(offset))
        created_ts = (ts - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
        updated_ts = ts.strftime("%Y-%m-%d %H:%M:%S")

        conn = _get_conn()
        conn.execute(
            """
            INSERT OR IGNORE INTO students (
                name, pin, user_type, exam_target, badge,
                profile_json, raw_input_json, plan_json,
                progress_snapshot_json, progress_assessment_json,
                assessment_json, assessment_result_json,
                cert_recommendation_json,
                created_at, updated_at
            ) VALUES (?, ?, 'learner', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                student["name"],
                student["pin"],
                student["exam_target"],
                student.get("badge", ""),
                student.get("profile_json"),
                student.get("raw_input_json"),
                student.get("plan_json"),
                student.get("progress_snapshot_json"),
                student.get("progress_assessment_json"),
                student.get("assessment_json"),
                student.get("assessment_result_json"),
                student.get("cert_recommendation_json"),
                created_ts,
                updated_ts,
            ),
        )
        conn.commit()
        conn.close()


# ─── Initialize on import ────────────────────────────────────────────────────
init_db()
seed_demo_students()
