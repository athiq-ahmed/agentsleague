"""
streamlit_app.py – Microsoft Certification Prep  •  Block 1 Interactive UI

Run:
    streamlit run streamlit_app.py

Modes:
  • Mock mode  – rule-based profiler, no credentials needed (default)
  • Live mode  – calls Azure OpenAI; requires .env with API credentials
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
import os

# make src/ importable without installing the package
sys.path.insert(0, str(Path(__file__).parent / "src"))

import streamlit as st
import plotly.graph_objects as go

from cert_prep.models import (
    EXAM_DOMAINS,
    DomainKnowledge,
    RawStudentInput,
    LearnerProfile,
)
from cert_prep.b1_mock_profiler import run_mock_profiling, run_mock_profiling_with_trace
from cert_prep.b1_1_study_plan_agent import StudyPlanAgent, StudyPlan, PRIORITY_COLOUR as PLAN_COLOUR
from cert_prep.b1_2_progress_agent import (
    ProgressAgent, ProgressSnapshot, DomainProgress,
    ReadinessAssessment, DomainStatusLine, Nudge,
    generate_weekly_summary, attempt_send_email,
    NudgeLevel, ReadinessVerdict,
)
from cert_prep.b1_1_learning_path_curator import LearningPathCuratorAgent, LearningPath, LearningModule
from cert_prep.b2_assessment_agent import (
    AssessmentAgent, Assessment, AssessmentResult,
    QuizQuestion, QuestionFeedback,
)
import dataclasses as _dc
import json as _json_mod


def _dc_to_json(obj) -> str:
    """Serialize a dataclass instance to a JSON string."""
    return _json_mod.dumps(_dc.asdict(obj), default=str)


def _progress_snapshot_from_dict(d: dict) -> ProgressSnapshot:
    d["domain_progress"] = [DomainProgress(**dp) for dp in d.get("domain_progress", [])]
    return ProgressSnapshot(**d)


def _readiness_assessment_from_dict(d: dict) -> ReadinessAssessment:
    d["verdict"] = ReadinessVerdict(d["verdict"])
    d["domain_status"] = [DomainStatusLine(**ds) for ds in d.get("domain_status", [])]
    d["nudges"] = [Nudge(level=NudgeLevel(n["level"]), title=n["title"], message=n["message"]) for n in d.get("nudges", [])]
    return ReadinessAssessment(**d)


def _assessment_from_dict(d: dict) -> Assessment:
    d["questions"] = [QuizQuestion(**q) for q in d.get("questions", [])]
    return Assessment(**d)


def _assessment_result_from_dict(d: dict) -> AssessmentResult:
    d["feedback"] = [QuestionFeedback(**f) for f in d.get("feedback", [])]
    return AssessmentResult(**d)


def _study_plan_from_dict(d: dict) -> StudyPlan:
    from cert_prep.b1_1_study_plan_agent import StudyTask, PrereqInfo
    d["tasks"] = [StudyTask(**t) for t in d.get("tasks", [])]
    d["prerequisites"] = [PrereqInfo(**p) for p in d.get("prerequisites", [])]
    return StudyPlan(**d)


def _learning_path_from_dict(d: dict) -> LearningPath:
    d["all_modules"] = [LearningModule(**m) for m in d.get("all_modules", [])]
    # curated_paths is dict[str, list[LearningModule]]
    cp = d.get("curated_paths", {})
    d["curated_paths"] = {
        k: [LearningModule(**m) for m in v] for k, v in cp.items()
    }
    return LearningPath(**d)

from cert_prep.b3_cert_recommendation_agent import (
    CertificationRecommendationAgent, CertRecommendation,
)
from cert_prep.guardrails import (
    GuardrailsPipeline, GuardrailResult, GuardrailLevel,
)
from cert_prep.database import (
    init_db, get_student, get_all_students, create_student, upsert_student,
    save_profile, save_plan, save_learning_path, save_progress,
    save_assessment, save_cert_recommendation, save_trace,
)
import plotly.express as px
import datetime

# ─── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Microsoft Cert Prep - Student Learning App",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Login gate ──────────────────────────────────────────────────────────────
APP_PIN = "1234"
ADMIN_USER = "admin"
ADMIN_PASS = "agents2026"

# Default demo accounts for quick login
DEMO_USERS = {
    "new":      {"name": "Alex Chen",    "pin": "1234",       "desc": "First-time user · AI-102"},
    "existing": {"name": "Priya Sharma", "pin": "1234",       "desc": "Returning · AZ-305 prep"},
    "admin":    {"name": "admin",        "pin": "agents2026", "desc": "Dashboard & traces"},
}

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["user_type"] = None  # "new", "existing", or "admin"

if not st.session_state["authenticated"]:
    # ── Microsoft Learn-inspired login CSS ───────────────────────────────────
    st.markdown("""
    <style>
      /* Hide sidebar & header, collapse top padding */
      [data-testid="stSidebar"] { display: none; }
      [data-testid="stHeader"] { display: none; }
      .block-container { padding-top: 0 !important; padding-bottom: 0.5rem !important; }
      /* MS Learn light background */
      [data-testid="stAppViewContainer"] {
        background: #f5f5f5;
        font-family: 'Segoe UI', -apple-system, system-ui, sans-serif;
      }
      /* ── Blue top banner (half text, half image) ─── */
      .ms-top-bar {
        background: linear-gradient(135deg, #0078D4 0%, #005A9E 100%);
        padding: 3.5rem 3rem;
        margin: 0 -3rem 0 -3rem;
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 3rem;
        align-items: center;
      }
      .ms-top-left h1 {
        color: #fff !important; font-size: 2.5rem; font-weight: 600;
        margin: 0 0 18px; font-family: 'Segoe UI', sans-serif;
        letter-spacing: -0.02em; line-height: 1.2;
      }
      .ms-top-left h1 a { display: none !important; }
      .ms-top-left p {
        color: rgba(255,255,255,0.9); font-size: 1rem;
        margin: 0; line-height: 1.65; max-width: 540px;
      }
      .ms-top-right {
        position: relative;
        height: 280px;
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 16px;
        padding: 0 20px;
      }
      .hero-visual-col {
        display: flex;
        flex-direction: column;
        gap: 16px;
      }
      .hero-box {
        border-radius: 12px;
        overflow: hidden;
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 2.2rem;
      }
      .hero-box.tall { height: 180px; }
      .hero-box.short { height: 100px; }
      .hero-box.grad1 { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
      .hero-box.grad2 { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
      .hero-box.grad3 { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
      .hero-box.grad4 { background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); }
      .hero-box.grad5 { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); }
      .hero-box.grad6 { background: linear-gradient(135deg, #30cfd0 0%, #330867 100%); }
      /* ── Benefit cards (vertical, MS Learn style) ─── */
      .ben-grid {
        display: grid; grid-template-columns: 1fr 1fr; gap: 20px;
        margin: 28px 0 0 0;
        padding: 0;
      }
      .ben-card {
        background: #fff;
        border: 1px solid #E1DFDD;
        border-radius: 10px;
        overflow: hidden;
        transition: box-shadow 0.2s;
      }
      .ben-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.1); }
      .ben-card .card-banner {
        height: 64px;
        display: flex; align-items: center; justify-content: center;
        font-size: 1.8rem;
      }
      .ben-card .card-body {
        padding: 18px 22px 22px;
      }
      .ben-card .card-body h4 {
        color: #1B1B1B; font-size: 1.05rem; font-weight: 600;
        margin: 0 0 8px; font-family: 'Segoe UI', sans-serif;
        line-height: 1.3;
      }
      .ben-card .card-body h4 a { display: none !important; }
      .ben-card .card-body p {
        color: #505050; font-size: 0.85rem;
        margin: 0; line-height: 1.6;
      }
      .banner-blue   { background: linear-gradient(135deg, #EFF6FF 0%, #DCEAFE 100%); }
      .banner-teal   { background: linear-gradient(135deg, #E6FAFA 0%, #CCF5F5 100%); }
      .banner-green  { background: linear-gradient(135deg, #F0FFF4 0%, #D1FAE5 100%); }
      .banner-purple { background: linear-gradient(135deg, #F3E8FF 0%, #E9D5FF 100%); }
      /* Tech stack strip */
      .tech-strip {
        margin-top: 8px; padding: 8px 0 0;
        border-top: 1px solid #E8E6E3;
      }
      .tech-strip-label {
        color: #8A8886; font-size: 0.55rem; text-transform: uppercase;
        letter-spacing: 0.1em; font-weight: 600; margin-bottom: 6px;
      }
      .tech-pills {
        display: flex; flex-wrap: wrap; gap: 6px;
      }
      .tech-pill {
        display: inline-flex; align-items: center; gap: 5px;
        background: #fff; border: 1px solid #E1DFDD;
        border-radius: 20px; padding: 4px 10px 4px 7px;
        font-size: 0.65rem; color: #323130; font-weight: 600;
        font-family: 'Segoe UI', sans-serif; transition: all 0.15s;
      }
      .tech-pill:hover { border-color: #0078D4; background: #F3F9FF; }
      .tech-pill svg, .tech-pill img { width: 16px; height: 16px; }
      .tech-pill .tp-icon { font-size: 0.85rem; line-height: 1; }
      /* ── Sign-in card ───────────────────────────── */
      .signin-card {
        background: #fff;
        border: 1px solid #E1DFDD;
        border-radius: 4px;
        padding: 24px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.06);
      }
      .signin-title {
        text-align: center; color: #1B1B1B; font-size: 1rem;
        font-weight: 600; margin-bottom: 0px;
        font-family: 'Segoe UI', sans-serif;
      }
      .signin-sub {
        text-align: center; color: #616161;
        font-size: 0.7rem; margin-bottom: 6px;
      }
      /* Quick-login demo user cards */
      .demo-grid { display: flex; gap: 6px; margin-bottom: 4px; }
      .demo-card {
        flex: 1; background: #EFF6FF;
        border: 1px solid #BFD4EF;
        border-radius: 4px; padding: 6px 4px;
        text-align: center; transition: all 0.2s;
      }
      .demo-card:hover { background: #DCEAFE; border-color: #0078D4; }
      .demo-card .dm-ic { font-size: 1rem; margin-bottom: 1px; }
      .demo-card .dm-nm { color: #1B1B1B; font-size: 0.68rem; font-weight: 600; }
      .demo-card .dm-rl { color: #616161; font-size: 0.6rem; }
      /* Quick-login Streamlit buttons */
      .stButton > button {
        background: #0078D4 !important;
        border: none !important;
        border-radius: 4px !important;
        color: #fff !important;
        font-size: 0.7rem !important;
        font-weight: 600 !important;
        padding: 4px 6px !important;
        font-family: 'Segoe UI', sans-serif !important;
        transition: background 0.15s;
      }
      .stButton > button:hover {
        background: #106EBE !important;
      }
      /* Divider */
      .or-sep {
        display: flex; align-items: center; gap: 8px;
        margin: 4px 0; color: #a0a0a0;
        font-size: 0.65rem;
      }
      .or-sep::before, .or-sep::after {
        content: ''; flex: 1; height: 1px;
        background: #E1DFDD;
      }
      /* Radio role selector */
      div[data-testid="stRadio"] label,
      div[data-testid="stRadio"] [role="radiogroup"] label {
        background: #FAFAFA !important;
        border: 1px solid #E1DFDD !important;
        border-radius: 4px !important;
        padding: 9px 14px !important;
        transition: all 0.2s ease; cursor: pointer;
        margin-bottom: 2px !important;
      }
      div[data-testid="stRadio"] label:hover {
        background: #EFF6FF !important;
        border-color: #0078D4 !important;
      }
      /* Force ALL radio label text visible */
      div[data-testid="stRadio"] label *,
      div[data-testid="stRadio"] label span,
      div[data-testid="stRadio"] label p,
      div[data-testid="stRadio"] label div,
      div[data-testid="stRadio"] [role="radiogroup"] label *,
      div[data-testid="stHorizontalRadio"] label *,
      div[data-testid="stHorizontalRadio"] label {
        color: #1B1B1B !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        font-family: 'Segoe UI', sans-serif !important;
      }
      /* Selected radio */
      div[data-testid="stRadio"] label:has(input:checked) {
        background: #EFF6FF !important;
        border-color: #0078D4 !important;
      }
      div[data-testid="stRadio"] label:has(input:checked) *,
      div[data-testid="stRadio"] label:has(input:checked) span,
      div[data-testid="stRadio"] label:has(input:checked) p {
        color: #0078D4 !important;
      }
      div[data-testid="stHorizontalRadio"] label:has(input:checked) {
        background: #EFF6FF !important;
        border-color: #0078D4 !important;
      }
      div[data-testid="stHorizontalRadio"] label:has(input:checked) * {
        color: #0078D4 !important;
      }
      /* Text inputs */
      .stTextInput input {
        background: #fff !important;
        border: 1px solid #E1DFDD !important;
        border-radius: 4px !important;
        color: #1B1B1B !important; padding: 6px 10px !important;
        font-size: 0.8rem !important;
        font-family: 'Segoe UI', sans-serif !important;
      }
      .stTextInput input:focus {
        border-color: #0078D4 !important;
        box-shadow: 0 0 0 1px #0078D4 !important;
      }
      .stTextInput input::placeholder { color: #a0a0a0 !important; }
      /* Submit button — Microsoft blue */
      .stFormSubmitButton button {
        background: #0078D4 !important;
        border: none !important; border-radius: 4px !important;
        padding: 7px !important; font-size: 0.8rem !important;
        font-weight: 600 !important; color: #fff !important;
        font-family: 'Segoe UI', sans-serif !important;
        transition: background 0.15s ease;
      }
      .stFormSubmitButton button:hover {
        background: #106EBE !important;
      }
      .role-desc {
        text-align: center; color: #616161;
        font-size: 0.76rem; margin: 4px 0 8px;
        min-height: 24px;
      }
    </style>
    """, unsafe_allow_html=True)

    # ── Blue top banner (half text, half visual) ────────────────────────────────────
    st.markdown("""
    <div class="ms-top-bar">
      <div class="ms-top-left">
        <h1>Agents League for Organizations</h1>
        <p>Drive more success by boosting your team's technical skills with curated AI-powered certification pathways. Jump-start team training and close skills gaps with personalized study plans and Microsoft-verified credentials your workforce needs to keep pace with fast-evolving technology and new roles.</p>
      </div>
      <div class="ms-top-right">
        <div class="hero-visual-col">
          <div class="hero-box tall grad1">🎯</div>
          <div class="hero-box short grad2">📊</div>
        </div>
        <div class="hero-visual-col">
          <div class="hero-box short grad3">🧠</div>
          <div class="hero-box tall grad4">✨</div>
        </div>
        <div class="hero-visual-col">
          <div class="hero-box tall grad5">🚀</div>
          <div class="hero-box short grad6">💡</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Two-panel layout ─────────────────────────────────────────────────────
    _left, _spacer, _right = st.columns([1.2, 0.08, 0.72])

    # ── LEFT: 4 Benefit cards (2x2 grid) ───────────────────────────────────
    with _left:
        st.markdown("""
        <div class="ben-grid">
          <div class="ben-card">
            <div class="card-banner banner-blue">🎯</div>
            <div class="card-body">
              <h4>Personalised Skill Profiling</h4>
              <p>AI analyses your background and domain knowledge to pinpoint exactly where you stand — data-driven insights across every exam domain.</p>
            </div>
          </div>
          <div class="ben-card">
            <div class="card-banner banner-teal">📅</div>
            <div class="card-body">
              <h4>Smart Study Plans</h4>
              <p>Priority-weighted, week-by-week schedules built around your available hours. Focus on high-impact domains first.</p>
            </div>
          </div>
          <div class="ben-card">
            <div class="card-banner banner-green">✅</div>
            <div class="card-body">
              <h4>Exam-Ready Confidence</h4>
              <p>Track progress with mid-journey check-ins, practice quizzes, and a clear GO / NO-GO readiness verdict.</p>
            </div>
          </div>
          <div class="ben-card">
            <div class="card-banner banner-purple">🧠</div>
            <div class="card-body">
              <h4>Adaptive Learning Paths</h4>
              <p>Curated Microsoft Learn modules matched to your gaps with smart sequencing — learn what matters, skip what you know.</p>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # ── RIGHT: Sign-in form ──────────────────────────────────────────────────
    with _right:
        st.markdown('<div class="signin-title">Sign In</div>', unsafe_allow_html=True)
        st.markdown('<div class="signin-sub">Pick a demo account or sign in manually</div>', unsafe_allow_html=True)

        # Quick-login visual cards
        st.markdown("""
        <div class="demo-grid">
          <div class="demo-card">
            <div class="dm-ic">👩‍🎓</div>
            <div class="dm-nm">Alex Chen</div>
            <div class="dm-rl">New Learner</div>
          </div>
          <div class="demo-card">
            <div class="dm-ic">👨‍💻</div>
            <div class="dm-nm">Priya Sharma</div>
            <div class="dm-rl">Returning</div>
          </div>
          <div class="demo-card">
            <div class="dm-ic">🔧</div>
            <div class="dm-nm">Admin</div>
            <div class="dm-rl">Dashboard</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # Functional quick-login buttons
        _d1, _d2, _d3 = st.columns(3)
        with _d1:
            if st.button("▶ Alex", key="demo_new", use_container_width=True):
                upsert_student("Alex Chen", "1234", "learner")
                st.session_state["authenticated"] = True
                st.session_state["login_name"] = "Alex Chen"
                st.session_state["user_type"] = "learner"
                st.rerun()
        with _d2:
            if st.button("▶ Priya", key="demo_existing", use_container_width=True):
                upsert_student("Priya Sharma", "1234", "learner")
                st.session_state["authenticated"] = True
                st.session_state["login_name"] = "Priya Sharma"
                st.session_state["user_type"] = "learner"
                st.rerun()
        with _d3:
            if st.button("▶ Admin", key="demo_admin", use_container_width=True):
                st.session_state["authenticated"] = True
                st.session_state["login_name"] = "Admin"
                st.session_state["user_type"] = "admin"
                st.session_state["admin_logged_in"] = True
                st.rerun()

        st.markdown('<div class="or-sep">or sign in manually</div>', unsafe_allow_html=True)

        # Manual login form (unified — no role selector)
        with st.form("login_form"):
            user_name = st.text_input("Your name", placeholder="Enter your name or 'admin'", label_visibility="collapsed")
            credential = st.text_input("PIN / Password", type="password", placeholder="PIN: 1234", label_visibility="collapsed")
            login_btn = st.form_submit_button("Sign In →", type="primary", use_container_width=True)

        st.markdown("""
        <div class="tech-strip">
          <div class="tech-strip-label">Built with Microsoft</div>
          <div class="tech-pills">
            <div class="tech-pill">
              <svg viewBox="0 0 23 23"><rect width="11" height="11" fill="#f25022"/><rect x="12" width="11" height="11" fill="#7fba00"/><rect y="12" width="11" height="11" fill="#00a4ef"/><rect x="12" y="12" width="11" height="11" fill="#ffb900"/></svg>
              Azure AI Foundry
            </div>
            <div class="tech-pill">
              <span class="tp-icon">🤖</span> Azure OpenAI · GPT-4o
            </div>
            <div class="tech-pill">
              <span class="tp-icon">📚</span> Microsoft Learn API
            </div>
            <div class="tech-pill">
              <span class="tp-icon">🧠</span> Semantic Kernel
            </div>
            <div class="tech-pill">
              <span class="tp-icon">⚡</span> Streamlit
            </div>
            <div class="tech-pill">
              <span class="tp-icon">🐙</span> GitHub Copilot
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        if login_btn:
            if not user_name.strip():
                st.error("Please enter your name.")
            elif user_name.strip().lower() == ADMIN_USER and credential == ADMIN_PASS:
                # Admin login
                st.session_state["authenticated"] = True
                st.session_state["login_name"] = "Admin"
                st.session_state["user_type"] = "admin"
                st.session_state["admin_logged_in"] = True
                st.rerun()
            elif credential != APP_PIN:
                st.error("Incorrect PIN. Please try again.")
            else:
                # Learner login — upsert student in DB
                _login_nm = user_name.strip()
                upsert_student(_login_nm, APP_PIN, "learner")
                st.session_state["authenticated"] = True
                st.session_state["login_name"] = _login_nm
                st.session_state["user_type"] = "learner"
                # Load existing profile from DB if available
                _db_student = get_student(_login_nm)
                if _db_student and _db_student.get("profile_json"):
                    import json as _json
                    from cert_prep.models import LearnerProfile, RawStudentInput
                    st.session_state["profile"] = LearnerProfile.model_validate_json(_db_student["profile_json"])
                    st.session_state["raw"] = RawStudentInput(**_json.loads(_db_student["raw_input_json"]))
                    st.session_state["badge"] = _db_student.get("badge", "🧪 Mock mode")
                    if _db_student.get("plan_json"):
                        st.session_state["plan"] = _study_plan_from_dict(_json_mod.loads(_db_student["plan_json"]))
                    if _db_student.get("learning_path_json"):
                        st.session_state["learning_path"] = _learning_path_from_dict(_json_mod.loads(_db_student["learning_path_json"]))
                    if _db_student.get("progress_snapshot_json"):
                        st.session_state["progress_snapshot"] = _progress_snapshot_from_dict(_json_mod.loads(_db_student["progress_snapshot_json"]))
                    if _db_student.get("progress_assessment_json"):
                        st.session_state["progress_assessment"] = _readiness_assessment_from_dict(_json_mod.loads(_db_student["progress_assessment_json"]))
                st.rerun()

    st.stop()

# ─── Colour palette (Microsoft Learn light theme) ─────────────────────────────
BLUE        = "#0078D4"      # Primary accent (links, actions)
BLUE_LITE   = "#EFF6FF"      # Note callout background
PURPLE      = "#5C2D91"      # Important accent
PURPLE_LITE = "#F5F0FF"      # Important callout background
CYAN        = "#0078D4"      # Mapped to primary blue
TEAL        = "#00B7C3"      # Secondary accent
PINK        = "#CA5010"      # Warning / attention (prereq gaps)
GREEN       = "#107C10"      # Success / tip
GREEN_LITE  = "#F0FFF4"      # Success background
ORANGE      = "#CA5010"      # Warning
ORANGE_LITE = "#FFF8F0"      # Warning background
RED         = "#D13438"      # Critical / caution
RED_LITE    = "#FFF0F0"      # Caution background
GOLD        = "#8A6D00"      # Moderate status
GOLD_LITE   = "#FFF8E0"      # Gold background
BG_DARK     = "#F5F5F5"      # Page content background
BG_CARD     = "#FFFFFF"      # Card / panel background
BG_SIDEBAR  = "#FAFAFA"      # Sidebar background
TEXT_PRIMARY = "#1B1B1B"     # Primary text
TEXT_MUTED   = "#616161"     # Muted text
BORDER       = "#E1DFDD"     # Borders

LEVEL_COLOUR = {
    "unknown":  "#d13438",
    "weak":     "#ca5010",
    "moderate": "#0078d4",
    "strong":   "#107c10",
}
LEVEL_ICON = {
    "unknown":  "✗",
    "weak":     "⚠",
    "moderate": "◑",
    "strong":   "✓",
}

EXAM_DOMAIN_NAMES = {d["id"]: d["name"] for d in EXAM_DOMAINS}

# ─── Azure / Microsoft certification catalogue ────────────────────────────────
AZURE_CERTS = [
    # AI & Data
    "AI-102 – Azure AI Engineer Associate",
    "AI-900 – Azure AI Fundamentals",
    "DP-100 – Azure Data Scientist Associate",
    "DP-203 – Azure Data Engineer Associate",
    "DP-300 – Azure Database Administrator Associate",
    "DP-420 – Azure Cosmos DB Developer Specialty",
    "DP-600 – Fabric Analytics Engineer Associate",
    # Azure Developer / Architect
    "AZ-204 – Azure Developer Associate",
    "AZ-305 – Azure Solutions Architect Expert",
    "AZ-400 – Azure DevOps Engineer Expert",
    # Azure Administrator / Security
    "AZ-104 – Azure Administrator Associate",
    "AZ-500 – Azure Security Engineer Associate",
    "AZ-700 – Azure Network Engineer Associate",
    "AZ-800 – Windows Server Hybrid Admin Associate",
    "AZ-900 – Azure Fundamentals",
    # Modern Work & Security
    "MS-900 – Microsoft 365 Fundamentals",
    "MS-102 – Microsoft 365 Administrator Expert",
    "SC-900 – Security, Compliance & Identity Fundamentals",
    "SC-100 – Cybersecurity Architect Expert",
    "SC-200 – Security Operations Analyst Associate",
    "SC-300 – Identity & Access Admin Associate",
    # Power Platform
    "PL-900 – Power Platform Fundamentals",
    "PL-100 – Power Platform App Maker Associate",
    "PL-200 – Power Platform Functional Consultant",
    "PL-400 – Power Platform Developer Associate",
    "PL-600 – Power Platform Solution Architect Expert",
]

DEFAULT_CERT = "AI-102 – Azure AI Engineer Associate"

# ─── Custom CSS (Microsoft Learn light theme) ──────────────────────────────
st.markdown(f"""
<style>
  /* ─ Microsoft Learn Light Theme ─ */
  [data-testid="stAppViewContainer"] {{
    background: {BG_DARK};
    font-family: 'Segoe UI', -apple-system, system-ui, sans-serif;
  }}
  [data-testid="stHeader"] {{
    background: #fff !important;
    border-bottom: 1px solid {BORDER};
  }}

  /* Hide Streamlit default page-nav labels */
  [data-testid="stSidebarNav"] {{ display: none; }}

  /* Hide deploy button */
  [data-testid="stDeployButton"],
  .stDeployButton {{ display: none !important; }}

  /* Hide sidebar completely post-login */
  [data-testid="stSidebar"],
  [data-testid="stSidebarCollapseButton"],
  [data-testid="collapsedControl"] {{ display: none !important; }}

  /* Scenario picker cards (post-login top strip) */
  .scenario-strip {{
    display: flex;
    gap: 12px;
    margin-bottom: 4px;
  }}
  .scenario-card {{
    flex: 1;
    background: #EFF6FF;
    border: 1px solid #BFD4EF;
    border-radius: 6px;
    padding: 10px 14px;
    text-align: center;
    transition: all 0.2s;
    cursor: pointer;
  }}
  .scenario-card:hover {{
    background: #DCEAFE;
    border-color: {BLUE};
  }}
  .scenario-card .sc-icon {{ font-size: 1.3rem; margin-bottom: 2px; }}
  .scenario-card .sc-name {{ color: #1B1B1B; font-size: 0.8rem; font-weight: 600; }}
  .scenario-card .sc-desc {{ color: #616161; font-size: 0.65rem; }}

  /* Azure Portal top navigation bar */
  .az-topbar {{
    background: {BLUE};
    display: flex;
    align-items: center;
    padding: 0 16px;
    height: 40px;
    margin: -1rem -1rem 0 -1rem;
    font-family: 'Segoe UI', sans-serif;
    color: #fff;
    box-shadow: 0 1px 3px rgba(0,0,0,0.15);
    position: relative;
    z-index: 999;
  }}
  .az-topbar-left {{
    display: flex;
    align-items: center;
    gap: 16px;
    white-space: nowrap;
  }}
  .az-waffle {{
    display: inline-grid;
    grid-template-columns: repeat(3, 3.5px);
    gap: 2.5px;
    padding: 8px;
    cursor: pointer;
  }}
  .az-waffle .wdot {{
    width: 3.5px; height: 3.5px;
    background: rgba(255,255,255,0.85);
    border-radius: 50%;
  }}
  .az-hamburger {{
    font-size: 18px;
    cursor: pointer;
    opacity: 0.9;
    line-height: 1;
    padding: 0 4px;
  }}
  .az-brand {{
    font-size: 15px;
    font-weight: 600;
    letter-spacing: -0.3px;
    color: #fff;
  }}
  .az-topbar-center {{
    flex: 1;
    max-width: 560px;
    margin: 0 24px;
  }}
  .az-search {{
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.25);
    border-radius: 4px;
    padding: 5px 14px;
    display: flex;
    align-items: center;
    gap: 8px;
    color: rgba(255,255,255,0.65);
    font-size: 13px;
  }}
  .az-topbar-right {{
    display: flex;
    align-items: center;
    gap: 4px;
    margin-left: auto;
  }}
  .az-copilot-pill {{
    background: #107C10;
    color: #fff;
    border-radius: 14px;
    padding: 3px 14px 3px 10px;
    font-size: 12px;
    font-weight: 600;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    margin-right: 6px;
    border: 1px solid rgba(255,255,255,0.2);
  }}
  .az-topbar-icon {{
    width: 32px; height: 32px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 2px;
    cursor: pointer;
    opacity: 0.8;
    color: #fff;
    transition: background 0.15s;
  }}
  .az-topbar-icon:hover {{
    background: rgba(255,255,255,0.1);
    opacity: 1;
  }}
  .az-topbar-icon svg {{
    width: 16px; height: 16px;
    fill: currentColor;
  }}
  .az-topbar-user {{
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    padding-left: 12px;
    margin-left: 4px;
    border-left: 1px solid rgba(255,255,255,0.2);
    cursor: default;
    max-width: 180px;
  }}
  .az-user-name {{
    font-size: 12px;
    font-weight: 400;
    color: #fff;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 160px;
  }}
  .az-user-dir {{
    font-size: 10px;
    color: rgba(255,255,255,0.65);
    text-transform: uppercase;
    letter-spacing: 0.3px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 160px;
  }}

  /* Sub-header breadcrumb bar */
  .az-subheader {{
    background: #fff;
    border-bottom: 1px solid {BORDER};
    padding: 8px 24px;
    margin: 0 -1rem;
    font-size: 0.82rem;
    color: {TEXT_MUTED};
    font-family: 'Segoe UI', sans-serif;
    display: flex;
    align-items: center;
    gap: 6px;
  }}
  .az-subheader a {{ color: {BLUE}; text-decoration: none; }}
  .az-subheader a:hover {{ text-decoration: underline; }}
  .az-subheader .sep {{ color: #C8C6C4; }}

  /* Section cards – MS Learn white */
  .card {{
    background: {BG_CARD};
    border-radius: 4px;
    padding: 1.2rem 1.5rem;
    border: 1px solid {BORDER};
    margin-bottom: 1rem;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
    color: {TEXT_PRIMARY};
  }}
  .card-purple {{ border-left: 4px solid {PURPLE}; }}
  .card-green  {{ border-left: 4px solid {GREEN}; }}
  .card-gold   {{ border-left: 4px solid {GOLD}; }}
  .card-pink   {{ border-left: 4px solid {ORANGE}; }}
  .card-blue   {{ border-left: 4px solid {BLUE}; }}

  /* MS Learn callout styles */
  .callout-note {{
    background: #EFF6FF; border-left: 4px solid #0078D4;
    border-radius: 4px; padding: 12px 16px; margin-bottom: 12px; color: #1B1B1B;
  }}
  .callout-tip {{
    background: #F0FFF4; border-left: 4px solid #107C10;
    border-radius: 4px; padding: 12px 16px; margin-bottom: 12px; color: #1B1B1B;
  }}
  .callout-warning {{
    background: #FFF8F0; border-left: 4px solid #CA5010;
    border-radius: 4px; padding: 12px 16px; margin-bottom: 12px; color: #1B1B1B;
  }}
  .callout-important {{
    background: #F5F0FF; border-left: 4px solid #5C2D91;
    border-radius: 4px; padding: 12px 16px; margin-bottom: 12px; color: #1B1B1B;
  }}

  /* Domain badge pills */
  .badge-unknown  {{ background:{LEVEL_COLOUR["unknown"]};  color:white; padding:2px 10px; border-radius:12px; font-size:0.78rem; font-weight:600; }}
  .badge-weak     {{ background:{LEVEL_COLOUR["weak"]};     color:white; padding:2px 10px; border-radius:12px; font-size:0.78rem; font-weight:600; }}
  .badge-moderate {{ background:{LEVEL_COLOUR["moderate"]}; color:white; padding:2px 10px; border-radius:12px; font-size:0.78rem; font-weight:600; }}
  .badge-strong   {{ background:{LEVEL_COLOUR["strong"]};   color:white; padding:2px 10px; border-radius:12px; font-size:0.78rem; font-weight:600; }}

  /* Ready / not-ready */
  .decision-ready     {{ background:{GREEN_LITE}; border:2px solid {GREEN}; border-radius:4px; padding:1rem 1.5rem; color:{TEXT_PRIMARY}; }}
  .decision-not-ready {{ background:{RED_LITE};   border:2px solid {RED};   border-radius:4px; padding:1rem 1.5rem; color:{TEXT_PRIMARY}; }}

  /* Progress bar */
  div[data-testid="stProgress"] > div {{ background-color: {BLUE}; }}

  /* Tab styling – MS Learn blue */
  .stTabs [data-baseweb="tab-highlight"] {{ background-color: {BLUE} !important; }}
  .stTabs [aria-selected="true"] {{ color: {BLUE} !important; font-weight: 600 !important; }}
  .stTabs [data-baseweb="tab"] {{ color: {TEXT_MUTED} !important; }}

  /* Global text */
  h1, h2, h3, h4, h5 {{ color: {TEXT_PRIMARY} !important; font-family: 'Segoe UI', -apple-system, sans-serif; }}
  .stMarkdown p, .stMarkdown li {{ color: #323130; }}
  .stCaption {{ color: {TEXT_MUTED} !important; }}

  /* Form elements */
  .stSelectbox div[data-baseweb="select"] > div {{
    background: #fff !important;
    border: 1px solid {BORDER} !important;
    color: {TEXT_PRIMARY} !important;
    border-radius: 4px !important;
  }}
  .stTextInput input, .stTextArea textarea {{
    background: #fff !important;
    border: 1px solid {BORDER} !important;
    color: {TEXT_PRIMARY} !important;
    border-radius: 4px !important;
  }}
  .stTextInput input:focus, .stTextArea textarea:focus {{
    border-color: {BLUE} !important;
    box-shadow: 0 0 0 1px {BLUE} !important;
  }}
  .stNumberInput input {{
    background: #fff !important;
    border: 1px solid {BORDER} !important;
    color: {TEXT_PRIMARY} !important;
  }}

  /* Radio/checkbox */
  div[data-testid="stRadio"] label *,
  div[data-testid="stRadio"] label span {{
    color: {TEXT_PRIMARY} !important;
  }}
  div[data-testid="stRadio"] label:has(input:checked) * {{
    color: {BLUE} !important;
  }}

  /* Expander */
  .stExpander details {{
    background: {BG_CARD} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 4px;
  }}
  .stExpander summary {{ color: {TEXT_PRIMARY} !important; }}

  /* Metric */
  div[data-testid="stMetricValue"] {{ color: {BLUE} !important; }}
  div[data-testid="stMetricLabel"] {{ color: {TEXT_MUTED} !important; }}

  /* Table */
  div[data-testid="stTable"] {{ background: {BG_CARD}; border-radius: 4px; border: 1px solid {BORDER}; }}

  /* Buttons (post-login) */
  .stButton > button {{
    background: {BLUE} !important;
    border: none !important;
    color: #fff !important;
    border-radius: 4px !important;
    font-weight: 600 !important;
    font-family: 'Segoe UI', sans-serif !important;
  }}
  .stButton > button:hover {{
    background: #106EBE !important;
  }}
  .stFormSubmitButton button {{
    background: {BLUE} !important;
    border: none !important;
    color: #fff !important;
    border-radius: 4px !important;
    font-weight: 600 !important;
  }}
  .stFormSubmitButton button:hover {{
    background: #106EBE !important;
  }}
</style>
""", unsafe_allow_html=True)


# ─── Post-login setup ────────────────────────────────────────────────────────
_login_name = st.session_state.get("login_name", "Learner")
_utype = st.session_state.get("user_type", "learner")
is_returning = "profile" in st.session_state

# Profiling mode (default mock)
use_live = False
az_endpoint = az_key = az_deployment = ""


# ─── Pre-fill values per scenario ────────────────────────────────────────────
_PREFILL_SCENARIOS = {
    "Blank — start from scratch": {},
    "Alex Chen — new learner, AI-102": {
        "name": "Alex Chen", "background": "3 years Python developer, familiar with REST APIs, no Azure experience.",
        "certs": "", "style": "Hands-on labs and project-based learning",
        "hpw": 10.0, "weeks": 8, "concerns": "Azure OpenAI, Bot Service",
        "goal": "Career move into AI engineering",
    },
    "Priya Sharma — returning, AZ-305": {
        "name": "Priya Sharma", "background": "5 years cloud architect, certified AZ-104 & AZ-204, strong IaC.",
        "certs": "AZ-104, AZ-204", "style": "Architecture diagrams and case studies",
        "hpw": 6.0, "weeks": 4, "concerns": "Well-Architected Framework, cost optimization",
        "goal": "Solutions Architect Expert to lead enterprise engagements",
    },
}
prefill = {}


# ─── Azure Portal–style top navigation bar ──────────────────────────────────────
if is_returning:
    _rp: LearnerProfile = st.session_state["profile"]
    _hero_title = f"Welcome back, {_rp.student_name}"
    _hero_sub = f"{_rp.exam_target} Prep"
else:
    _hero_title = "Certification Coach"
    _hero_sub = "New Session"

st.markdown(f"""
<div class="az-topbar">
  <div class="az-topbar-right" style="margin-left:auto;">
    <div class="az-topbar-user" id="az-profile-trigger" style="cursor:pointer;">
      <span class="az-user-name">{_login_name}</span>
      <span class="az-user-dir">Agents League</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ─── Sign-out dropdown (anchored top-right under profile) ────────────────────
_so_col1, _so_col2 = st.columns([11, 2])
with _so_col2:
    with st.popover("👤 " + _login_name, use_container_width=True):
        st.markdown(f"""
        <div style="text-align:center;padding:8px 0 4px;">
          <div style="display:flex;align-items:center;gap:8px;justify-content:space-between;margin-bottom:12px;">
            <div style="display:flex;align-items:center;gap:6px;">
              <svg width="16" height="16" viewBox="0 0 23 23">
                <rect width="11" height="11" fill="#f25022"/>
                <rect x="12" width="11" height="11" fill="#7fba00"/>
                <rect y="12" width="11" height="11" fill="#00a4ef"/>
                <rect x="12" y="12" width="11" height="11" fill="#ffb900"/>
              </svg>
              <span style="font-weight:600;font-size:0.9rem;color:#1B1B1B;">Microsoft</span>
            </div>
          </div>
          <div style="width:64px;height:64px;border-radius:50%;background:#005A9E;
                      display:flex;align-items:center;justify-content:center;
                      margin:0 auto 10px;">
            <span style="color:#fff;font-size:1.4rem;font-weight:600;">{_login_name[0].upper()}</span>
          </div>
          <div style="font-weight:700;font-size:0.95rem;color:#1B1B1B;">{_login_name}</div>
          <div style="font-size:0.78rem;color:#616161;margin:2px 0 8px;">Agents League</div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Sign out", key="topbar_signout", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

# ─── Admin Dashboard link (for admin users) ──────────────────────────────────
if _utype == "admin":
    st.page_link("pages/1_Admin_Dashboard.py", label="🔐 Admin Dashboard", icon="📊")

# ─── Scenario picker cards (new users only) ──────────────────────────────────
if not is_returning:
    st.markdown("### 🎯 Choose a Demo Scenario")
    st.markdown("""
    <div class="scenario-strip">
      <div class="scenario-card">
        <div class="sc-icon">👩‍🎓</div>
        <div class="sc-name">Alex Chen</div>
        <div class="sc-desc">New learner · AI-102</div>
      </div>
      <div class="scenario-card">
        <div class="sc-icon">👨‍💻</div>
        <div class="sc-name">Priya Sharma</div>
        <div class="sc-desc">Returning · AZ-305</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    _sc1, _sc2 = st.columns(2)
    with _sc1:
        if st.button("▶ Alex", key="sc_alex", use_container_width=True):
            prefill.update(_PREFILL_SCENARIOS["Alex Chen — new learner, AI-102"])
    with _sc2:
        if st.button("▶ Priya", key="sc_priya", use_container_width=True):
            prefill.update(_PREFILL_SCENARIOS["Priya Sharma — returning, AZ-305"])

# ─── Intake form ─────────────────────────────────────────────────────────────
st.markdown("## 📝 Student Intake Form")
st.caption("Fill in the details below. The AI profiling agent will personalise your certification study plan.")

with st.form("intake_form", clear_on_submit=False):

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 👤 Student Details")
        student_name = st.text_input(
            "Your name",
            value=prefill.get("name", ""),
            placeholder="e.g. Priya Sharma",
        )
        exam_cert = st.selectbox(
            "Target certification exam",
            options=AZURE_CERTS,
            index=AZURE_CERTS.index(DEFAULT_CERT),
            help="Select any Azure / Microsoft certification you are preparing for.",
        )
        # Extract the short code (e.g. 'AI-102') for use in the profile
        exam_target = exam_cert.split(" – ")[0].strip()
        background_text = st.text_area(
            "Background & experience",
            value=prefill.get("background", ""),
            placeholder="e.g. 3 years as a Python developer, familiar with REST APIs, no Azure experience yet",
            height=110,
        )
        existing_certs_raw = st.text_input(
            "Existing Microsoft certifications",
            value=prefill.get("certs", ""),
            placeholder="e.g. AZ-104, AZ-305  (or leave blank)",
        )
        preferred_style = st.text_area(
            "How do you prefer to learn?",
            value=prefill.get("style", ""),
            placeholder="e.g. hands-on labs first, or structured reading, or quick reference cards",
            height=80,
        )

    with col2:
        st.markdown("#### ⏱️ Study Budget")
        col2a, col2b = st.columns(2)
        with col2a:
            hours_per_week = st.number_input(
                "Hours per week", min_value=1.0, max_value=60.0,
                value=float(prefill.get("hpw", 10.0)), step=0.5,
            )
        with col2b:
            weeks_available = st.number_input(
                "Weeks available", min_value=1, max_value=52,
                value=int(prefill.get("weeks", 8)), step=1,
            )
        total_hours = hours_per_week * weeks_available
        st.info(f"📅 Total study budget: **{total_hours:.0f} hours**")

        st.markdown("#### 🎯 Focus & Preferences")
        concern_topics_raw = st.text_input(
            "Topics that worry you most",
            value=prefill.get("concerns", ""),
            placeholder="e.g. Azure OpenAI, Bot Service, Responsible AI",
        )
        goal_text = st.text_area(
            "Why do you want this certification?",
            value=prefill.get("goal", ""),
            placeholder="e.g. career change, promotion, client project requirement",
            height=80,
        )

    st.markdown("")
    submitted = st.form_submit_button(
        "🚀 Generate Learner Profile",
        type="primary",
        width="stretch",
    )


# ─── Handle submit ────────────────────────────────────────────────────────────
if submitted:
    if not student_name.strip():
        st.error("Please enter the student's name.")
        st.stop()

    raw = RawStudentInput(
        student_name    = student_name.strip(),
        exam_target     = exam_target.strip(),
        background_text = background_text.strip(),
        existing_certs  = [c.strip() for c in existing_certs_raw.split(",") if c.strip()],
        hours_per_week  = hours_per_week,
        weeks_available = weeks_available,
        concern_topics  = [t.strip() for t in concern_topics_raw.split(",") if t.strip()],
        preferred_style = preferred_style.strip(),
        goal_text       = goal_text.strip(),
    )

    # ── Guardrail: validate raw input ────────────────────────────────────────
    _guardrails = GuardrailsPipeline()
    _input_result = _guardrails.check_input(raw)
    if _input_result.blocked:
        for v in _input_result.violations:
            if v.level == GuardrailLevel.BLOCK:
                st.error(f"🚫 Guardrail [{v.code}]: {v.message}")
        st.stop()
    for v in [v for v in _input_result.violations if v.level.value == "WARN"]:
        st.warning(f"⚠️ [{v.code}] {v.message}")

    # ── Profile generation ────────────────────────────────────────────────────
    if use_live:
        try:
            import os
            os.environ["AZURE_OPENAI_ENDPOINT"]    = az_endpoint
            os.environ["AZURE_OPENAI_API_KEY"]     = az_key
            os.environ["AZURE_OPENAI_DEPLOYMENT"]  = az_deployment

            from cert_prep.b0_intake_agent import LearnerProfilingAgent
            with st.spinner("☁️ Calling Azure OpenAI — analysing profile…"):
                profile: LearnerProfile = LearnerProfilingAgent().run(raw)
            st.success("✅ Live Azure OpenAI profile generated.")
            mode_badge = "☁️ Live Azure OpenAI"
        except Exception as e:
            st.error(f"Azure OpenAI call failed: {e}")
            st.info("Falling back to mock profiler.")
            profile = run_mock_profiling(raw)
            mode_badge = "🧪 Mock (fallback)"
    else:
        with st.spinner("🧪 Running rule-based profiler…"):
            profile, trace = run_mock_profiling_with_trace(raw)
        st.session_state["trace"] = trace
        mode_badge = "🧪 Mock mode"

    # ── Guardrail: validate profile output ───────────────────────────────────
    _profile_result = _guardrails.check_profile(profile)
    if _profile_result.blocked:
        for v in _profile_result.violations:
            if v.level == GuardrailLevel.BLOCK:
                st.error(f"🚫 Profile guardrail [{v.code}]: {v.message}")
        st.warning("Profile has critical issues; results may be unreliable.")

    st.session_state["profile"]           = profile
    st.session_state["raw"]               = raw
    st.session_state["badge"]             = mode_badge
    st.session_state["guardrail_input"]   = _input_result
    st.session_state["guardrail_profile"] = _profile_result

    # ── Generate study plan (StudyPlanAgent) ──────────────────────────────────
    with st.spinner("📅 Study Plan Agent: building Gantt schedule…"):
        plan: StudyPlan = StudyPlanAgent().run_with_raw(
            profile,
            existing_certs=[c.strip() for c in existing_certs_raw.split(",") if c.strip()],
        )
    _plan_result = _guardrails.check_study_plan(plan, profile)
    st.session_state["plan"]              = plan
    st.session_state["guardrail_plan"]    = _plan_result

    # ── Learning Path Curator Agent ───────────────────────────────────────────
    with st.spinner("📚 Learning Path Curator: mapping MS Learn modules…"):
        learning_path: LearningPath = LearningPathCuratorAgent().curate(profile)
    _path_result = _guardrails.check_learning_path(learning_path)
    st.session_state["learning_path"]     = learning_path
    st.session_state["guardrail_path"]    = _path_result

    # ── Save to SQLite ────────────────────────────────────────────────────────
    _student_name = student_name.strip()
    upsert_student(_student_name, APP_PIN, "learner")
    save_profile(
        _student_name,
        profile.model_dump_json(),
        _json_mod.dumps(_dc.asdict(raw)),
        exam_target.strip(),
        badge=mode_badge,
    )
    save_plan(_student_name, _dc_to_json(plan))
    save_learning_path(_student_name, _dc_to_json(learning_path))
    if st.session_state.get("trace"):
        _trace_obj = st.session_state["trace"]
        save_trace(_student_name, _json_mod.dumps(_trace_obj.__dict__, default=str))


# ─── Results ─────────────────────────────────────────────────────────────────
if "profile" in st.session_state:
    profile: LearnerProfile  = st.session_state["profile"]
    raw:     RawStudentInput = st.session_state["raw"]
    badge = st.session_state.get("badge", "")

    st.markdown("---")
    st.markdown(f"## 📊 Learner Profile  <small style='color:grey;font-size:0.8rem;'>({badge})</small>",
                unsafe_allow_html=True)

    # ── KPI info-bar (HTML cards — never truncates) ───────────────────────────
    risk_count = len(profile.risk_domains)
    skip_count = len(profile.modules_to_skip)
    avg_conf   = sum(dp.confidence_score for dp in profile.domain_profiles) / len(profile.domain_profiles)

    conf_color = "#27ae60" if avg_conf >= 0.65 else ("#e67e22" if avg_conf >= 0.40 else "#e74c3c")
    risk_color = "#e74c3c" if risk_count > 2 else ("#e67e22" if risk_count > 0 else "#27ae60")

    # Risk / confidence backgrounds (light pastel that complements the value colour)
    _rc_bg  = "#fff1f0" if risk_count > 2 else ("#fff8ee" if risk_count > 0 else "#f0fff4")
    _rc_bdr = risk_color
    _cf_bg  = "#f0fff4" if avg_conf >= 0.65 else ("#fff8ee" if avg_conf >= 0.40 else "#fff1f0")
    _learn_icon = {"unknown": "🌱", "weak": "📖", "moderate": "📘", "strong": "🏆"}.get(
        profile.experience_level.value.split("_")[0], "🎓"
    )

    kpi_cards = f"""
    <div style="display:flex;gap:14px;margin-bottom:18px;flex-wrap:wrap;">

      <!-- Student -->
      <div style="flex:1;min-width:150px;
                  background:linear-gradient(135deg,#f5f0ff 0%,#ede9fe 100%);
                  border-left:5px solid #7c3aed;border-radius:10px;padding:14px 18px;
                  box-shadow:0 2px 8px rgba(124,58,237,.12);">
        <div style="color:#7c3aed;font-size:0.68rem;font-weight:700;
                    text-transform:uppercase;letter-spacing:.08em;margin-bottom:5px;">🎓 Student</div>
        <div style="color:#3b0764;font-size:1.1rem;font-weight:800;
                    line-height:1.3;word-break:break-word;">{profile.student_name}</div>
        <div style="color:#8b5cf6;font-size:0.75rem;margin-top:3px;">
          🎯&nbsp;{profile.exam_target}
        </div>
      </div>

      <!-- Experience -->
      <div style="flex:1;min-width:150px;
                  background:linear-gradient(135deg,#eff6ff 0%,#dbeafe 100%);
                  border-left:5px solid #2563eb;border-radius:10px;padding:14px 18px;
                  box-shadow:0 2px 8px rgba(37,99,235,.12);">
        <div style="color:#2563eb;font-size:0.68rem;font-weight:700;
                    text-transform:uppercase;letter-spacing:.08em;margin-bottom:5px;">{_learn_icon} Experience</div>
        <div style="color:#1e3a8a;font-size:1.05rem;font-weight:800;
                    line-height:1.3;word-break:break-word;">
          {profile.experience_level.value.replace("_", " ").title()}
        </div>
        <div style="color:#3b82f6;font-size:0.75rem;margin-top:3px;">
          📚&nbsp;{profile.learning_style.value.replace("_"," ").title()} learner
        </div>
      </div>

      <!-- Study Budget -->
      <div style="flex:1;min-width:140px;
                  background:linear-gradient(135deg,#f0fdf4 0%,#bbf7d0 100%);
                  border-left:5px solid #16a34a;border-radius:10px;padding:14px 18px;
                  box-shadow:0 2px 8px rgba(22,163,74,.12);">
        <div style="color:#16a34a;font-size:0.68rem;font-weight:700;
                    text-transform:uppercase;letter-spacing:.08em;margin-bottom:5px;">⏱ Study Budget</div>
        <div style="color:#14532d;font-size:1.15rem;font-weight:800;line-height:1.3;">
          {profile.total_budget_hours:.0f}&nbsp;h
        </div>
        <div style="color:#22c55e;font-size:0.75rem;margin-top:3px;">
          {profile.hours_per_week}h/wk × {profile.weeks_available} weeks
        </div>
      </div>

      <!-- Risk Domains -->
      <div style="flex:1;min-width:140px;
                  background:linear-gradient(135deg,{_rc_bg} 0%,white 100%);
                  border-left:5px solid {_rc_bdr};border-radius:10px;padding:14px 18px;
                  box-shadow:0 2px 8px rgba(0,0,0,.07);">
        <div style="color:{_rc_bdr};font-size:0.68rem;font-weight:700;
                    text-transform:uppercase;letter-spacing:.08em;margin-bottom:5px;">⚠ Risk Domains</div>
        <div style="color:{_rc_bdr};font-size:1.25rem;font-weight:800;line-height:1.3;">
          {risk_count}
          <span style="font-size:0.8rem;font-weight:500;color:#555;margin-left:4px;">
            {"critical" if risk_count > 2 else ("flagged" if risk_count > 0 else "clear")}
          </span>
        </div>
        <div style="color:#888;font-size:0.75rem;margin-top:3px;">
          {skip_count} domains skippable
        </div>
      </div>

      <!-- Avg Confidence -->
      <div style="flex:1;min-width:140px;
                  background:linear-gradient(135deg,{_cf_bg} 0%,white 100%);
                  border-left:5px solid {conf_color};border-radius:10px;padding:14px 18px;
                  box-shadow:0 2px 8px rgba(0,0,0,.07);">
        <div style="color:{conf_color};font-size:0.68rem;font-weight:700;
                    text-transform:uppercase;letter-spacing:.08em;margin-bottom:5px;">💯 Avg Confidence</div>
        <div style="color:{conf_color};font-size:1.35rem;font-weight:800;line-height:1.3;">
          {avg_conf:.0%}
        </div>
        <div style="color:#888;font-size:0.75rem;margin-top:3px;">
          {"Great start! 🎉" if avg_conf >= 0.65 else ("Needs work 📖" if avg_conf >= 0.40 else "Remediation needed 🔧")}
        </div>
      </div>

    </div>
    """
    st.markdown(kpi_cards, unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────────────────────────────
    # All learners see all tabs (returning users have their data auto-loaded)
    tab_domains, tab_plan, tab_path, tab_recs, tab_progress, tab_quiz, tab_json = st.tabs([
        "🗺️ Domain Map",
        "📅 Study Setup",
        "📚 Learning Path",
        "💡 Recommendations",
        "📈 My Progress",
        "🧪 Knowledge Check",
        "📄 Raw JSON",
    ])

    # ── Tab 1: Domain Map ─────────────────────────────────────────────────────
    with tab_domains:
        st.markdown("### Domain Knowledge Assessment")
        st.caption("Confidence scores and knowledge levels across the exam domains.")

        # ── Pre-compute insight data ──────────────────────────────────────────
        labels    = [dp.domain_name.replace(" Solutions", "").replace("Implement ", "")
                     for dp in profile.domain_profiles]
        scores    = [dp.confidence_score for dp in profile.domain_profiles]
        threshold = [0.50] * len(labels)

        _sorted_dp   = sorted(profile.domain_profiles, key=lambda d: d.confidence_score)
        _weakest     = _sorted_dp[0]
        _strongest   = _sorted_dp[-1]
        _above_thresh = [dp for dp in profile.domain_profiles if dp.confidence_score >= 0.50]
        _below_thresh = [dp for dp in profile.domain_profiles if dp.confidence_score < 0.50]
        _score_range  = _strongest.confidence_score - _weakest.confidence_score
        _avg_score    = sum(scores) / len(scores)

        # ── Chart 1: Radar ────────────────────────────────────────────────────
        st.markdown("#### 🕸️ Chart 1 — Confidence Radar")
        st.caption(
            "The filled shape represents your current knowledge coverage. "
            "The dashed orange ring marks the 50 % pass-readiness threshold. "
            "Domains where the shape dips inside the ring need focused study."
        )

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=scores + [scores[0]],
            theta=labels + [labels[0]],
            fill="toself",
            name="Student confidence",
            line=dict(color=BLUE, width=2),
            fillcolor="rgba(0,120,212,0.15)",
        ))
        fig.add_trace(go.Scatterpolar(
            r=threshold + [threshold[0]],
            theta=labels + [labels[0]],
            name="Min threshold (50%)",
            line=dict(color="#ca5010", width=1.5, dash="dot"),
            fill="none",
        ))
        fig.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 1], tickformat=".0%",
                                gridcolor="#e0e0e0", linecolor="#e0e0e0"),
                angularaxis=dict(linecolor="#cccccc"),
                bgcolor="white",
            ),
            legend=dict(orientation="h", yanchor="bottom", y=-0.15),
            margin=dict(t=30, b=60, l=60, r=60),
            height=380,
            paper_bgcolor="white",
            plot_bgcolor="white",
        )

        col_chart, col_detail = st.columns([1, 1])
        with col_chart:
            st.plotly_chart(fig, use_container_width=True)

            # ── Radar insights ────────────────────────────────────────────────
            _shape_pct = int((_avg_score / 0.50) * 100)
            _radar_colour = GREEN if len(_below_thresh) == 0 else (GOLD if len(_below_thresh) <= 2 else "#d13438")
            _coverage_label = (
                "Full coverage above threshold" if not _below_thresh
                else f"{len(_below_thresh)} domain(s) below threshold"
            )
            st.markdown(
                f"""<div style="background:#f8f8ff;border-left:4px solid {PURPLE};
                     border-radius:8px;padding:10px 14px;margin-top:4px;font-size:0.85rem;">
                  <b style="font-size:0.9rem;">📌 Radar Insights</b><br/><br/>
                  <b>Shape coverage:</b> {_avg_score:.0%} avg confidence
                  &nbsp;<span style="color:{_radar_colour};font-weight:600;">({_coverage_label})</span><br/>
                  <b>Strongest axis:</b>
                    <span style="color:{GREEN};font-weight:600;">
                      {_strongest.domain_name.replace("Implement ","").replace(" Solutions","")}
                    </span>
                    &nbsp;at {_strongest.confidence_score:.0%}<br/>
                  <b>Weakest axis:</b>
                    <span style="color:#d13438;font-weight:600;">
                      {_weakest.domain_name.replace("Implement ","").replace(" Solutions","")}
                    </span>
                    &nbsp;at {_weakest.confidence_score:.0%}<br/>
                  <b>Score range:</b> {_score_range:.0%}
                    {"&nbsp;— wide gap, uneven preparation" if _score_range > 0.40
                     else ("&nbsp;— moderate spread" if _score_range > 0.20
                     else "&nbsp;— fairly balanced")}<br/>
                  {"<b style='color:#d13438;'>⚠ " + str(len(_below_thresh)) + " domain(s) need immediate focus:</b> " +
                    ", ".join(dp.domain_name.replace("Implement ","").replace(" Solutions","")
                              for dp in _below_thresh)
                   if _below_thresh else
                   "<b style='color:" + GREEN + ";'>✓ All domains meet the 50 % readiness threshold.</b>"}
                </div>""",
                unsafe_allow_html=True,
            )

        with col_detail:
            st.markdown("**Per-domain breakdown**")
            for dp in profile.domain_profiles:
                level  = dp.knowledge_level.value
                colour = LEVEL_COLOUR[level]
                icon   = LEVEL_ICON[level]
                pct    = int(dp.confidence_score * 100)
                skip   = "⏭ Skip candidate" if dp.skip_recommended else ""
                risk   = "⚠ Risk" if dp.domain_id in profile.risk_domains else ""
                flags  = f"&nbsp;{skip}&nbsp;{risk}" if (skip or risk) else ""

                st.markdown(
                    f"""<div style="margin-bottom:10px;">
                        <span><b>{dp.domain_name}</b></span>
                        <span class="badge-{level}" style="background:{colour};color:white;
                              padding:1px 8px;border-radius:10px;font-size:0.75rem;
                              font-weight:600;margin-left:8px;">{icon} {level.upper()}</span>
                        <span style="font-size:0.75rem;color:grey;margin-left:8px;">{flags}</span>
                        <div style="background:#e0e0e0;border-radius:4px;height:8px;margin-top:4px;">
                          <div style="background:{colour};width:{pct}%;height:8px;border-radius:4px;"></div>
                        </div>
                        <span style="font-size:0.75rem;color:#555;">{pct}% confidence — {dp.notes}</span>
                    </div>""",
                    unsafe_allow_html=True,
                )

        # ── Chart 2: Horizontal Bar ───────────────────────────────────────────
        st.markdown("---")
        st.markdown("#### 📊 Chart 2 — Domain Confidence Bar Chart")
        st.caption(
            "Bars show each domain's confidence score, colour-coded by knowledge level. "
            "The dashed line at 50 % is the risk threshold — anything left of it needs prioritised study time."
        )

        bar_fig = go.Figure(go.Bar(
            y=labels,
            x=scores,
            orientation="h",
            marker=dict(
                color=[LEVEL_COLOUR[dp.knowledge_level.value] for dp in profile.domain_profiles],
                line=dict(width=0),
            ),
            text=[f"{s:.0%}" for s in scores],
            textposition="outside",
        ))
        bar_fig.add_vline(x=0.50, line_dash="dot", line_color="#ca5010",
                          annotation_text="Risk threshold 50%", annotation_position="top right")
        bar_fig.update_layout(
            height=280,
            margin=dict(l=10, r=60, t=20, b=20),
            xaxis=dict(range=[0, 1.1], tickformat=".0%", showgrid=True, gridcolor="#eeeeee"),
            yaxis=dict(autorange="reversed"),
            paper_bgcolor="white",
            plot_bgcolor="white",
            showlegend=False,
        )
        st.plotly_chart(bar_fig, use_container_width=True)

        # ── Bar chart insights ────────────────────────────────────────────────
        _level_counts = {}
        for dp in profile.domain_profiles:
            lv = dp.knowledge_level.value
            _level_counts[lv] = _level_counts.get(lv, 0) + 1

        _skip_names  = [dp.domain_name.replace("Implement ","").replace(" Solutions","")
                        for dp in profile.domain_profiles if dp.skip_recommended]
        _risk_names  = [dp.domain_name.replace("Implement ","").replace(" Solutions","")
                        for dp in profile.domain_profiles if dp.domain_id in profile.risk_domains]

        _bar_colour  = GREEN if not _below_thresh else (GOLD if len(_below_thresh) <= 2 else "#d13438")

        # Build level pills
        _level_pills = ""
        for lv, cnt in sorted(_level_counts.items(),
                               key=lambda x: ["strong","moderate","weak","unknown"].index(x[0])
                               if x[0] in ["strong","moderate","weak","unknown"] else 9):
            _level_pills += (
                f'<span style="display:inline-block;background:{LEVEL_COLOUR[lv]};color:#fff;'
                f'padding:2px 10px;border-radius:12px;font-size:0.78rem;font-weight:600;margin-right:6px;">'
                f'{cnt} {lv.upper()}</span>'
            )

        # Build risk / skip lines
        _risk_html = ""
        if _risk_names:
            _risk_html = (
                f'<div class="callout-warning" style="margin-top:8px;">'
                f'<b>⚠ Risk domains (below 50% threshold):</b><br/>'
                + "".join(f'<span style="display:inline-block;margin:3px 6px 3px 0;padding:2px 10px;'
                          f'background:#FFF0F0;border:1px solid #D13438;border-radius:12px;'
                          f'font-size:0.82rem;color:#D13438;font-weight:600;">{n}</span>'
                          for n in _risk_names)
                + '</div>'
            )
        else:
            _risk_html = (
                f'<div class="callout-tip" style="margin-top:8px;">'
                f'<b>✓ No domains fall below the risk threshold.</b></div>'
            )

        _skip_html = ""
        if _skip_names:
            _skip_html = (
                f'<div style="margin-top:6px;font-size:0.85rem;color:{GREEN};">'
                f'<b>⏭ Fast-track candidates:</b> {", ".join(_skip_names)}</div>'
            )

        _rec_text = (
            "Concentrate initial study blocks on <b>" +
            ", ".join(dp.domain_name.replace("Implement ","").replace(" Solutions","")
                      for dp in _sorted_dp[:2]) +
            "</b> domains first to close the biggest gaps."
            if _below_thresh else
            "All domains are at or above readiness. Focus remaining time on practice exams and edge-case topics."
        )

        st.markdown(
            f"""<div class="callout-note">
              <b style="font-size:0.92rem;">📊 Assessment Summary</b>
              <div style="margin-top:8px;">
                <div style="margin-bottom:6px;">{_level_pills}</div>
                <div style="font-size:0.85rem;color:#323130;">
                  <b>Domains above 50% threshold:</b>
                  <span style="color:{_bar_colour};font-weight:700;">
                    {len(_above_thresh)} / {len(profile.domain_profiles)}
                  </span>
                </div>
                {_skip_html}
              </div>
              {_risk_html}
              <div style="margin-top:8px;padding:8px 12px;background:#FAFAFA;border-radius:4px;
                   font-size:0.85rem;color:#323130;">
                <b>💡 Recommendation:</b> {_rec_text}
              </div>
            </div>""",
            unsafe_allow_html=True,
        )

    # ── Tab 2: Study Setup ────────────────────────────────────────────────────
    with tab_plan:
        plan: StudyPlan = st.session_state.get("plan")

        # ── 1. Prerequisites / Fundamentals ──────────────────────────────────
        st.markdown("### 🎓 Prerequisite & Recommended Certifications")

        if plan and plan.prerequisites:
            has_gap = plan.prereq_gap
            prereq_held     = [p for p in plan.prerequisites if p.already_held]
            prereq_missing  = [p for p in plan.prerequisites if not p.already_held and p.relationship == "strongly_recommended"]
            prereq_helpful  = [p for p in plan.prerequisites if not p.already_held and p.relationship == "helpful"]

            if has_gap:
                st.warning(
                    f"⚠️ **Prerequisite gap detected for {profile.exam_target}.**  \n"
                    f"{plan.prereq_message}",
                    icon="⚠️",
                )
            else:
                st.success(
                    f"✅ All strongly recommended prerequisites for **{profile.exam_target}** are already held.",
                    icon="✅",
                )

            prereq_cols = st.columns(3)
            with prereq_cols[0]:
                st.markdown("**🔴 Strongly Recommended (missing)**")
                if prereq_missing:
                    for p in prereq_missing:
                        st.markdown(
                            f"""<div style='background:#FDE7F3;border-left:4px solid {PINK};
                                 padding:6px 12px;border-radius:6px;margin-bottom:6px;'>
                                 <b style='color:{PINK};'>{p.cert_code}</b>
                                 <span style='color:#444;font-size:0.85rem;'><br/>{p.cert_name}</span>
                                 <br/><span style='color:#d13438;font-size:0.78rem;'>⚠ Not yet held</span>
                            </div>""",
                            unsafe_allow_html=True,
                        )
                else:
                    st.caption("None missing ✓")

            with prereq_cols[1]:
                st.markdown("**🟢 Already Held**")
                if prereq_held:
                    for p in prereq_held:
                        st.markdown(
                            f"""<div style='background:{GREEN_LITE};border-left:4px solid {GREEN};
                                 padding:6px 12px;border-radius:6px;margin-bottom:6px;'>
                                 <b style='color:{GREEN};'>{p.cert_code}</b>
                                 <span style='color:#444;font-size:0.85rem;'><br/>{p.cert_name}</span>
                                 <br/><span style='color:{GREEN};font-size:0.78rem;'>✓ Held</span>
                            </div>""",
                            unsafe_allow_html=True,
                        )
                else:
                    st.caption("No relevant certifications held yet")

            with prereq_cols[2]:
                st.markdown("**🔵 Helpful (optional)**")
                if prereq_helpful:
                    for p in prereq_helpful:
                        st.markdown(
                            f"""<div style='background:{BLUE_LITE};border-left:4px solid {BLUE};
                                 padding:6px 12px;border-radius:6px;margin-bottom:6px;'>
                                 <b style='color:{BLUE};'>{p.cert_code}</b>
                                 <span style='color:#444;font-size:0.85rem;'><br/>{p.cert_name}</span>
                                 <br/><span style='color:{BLUE};font-size:0.78rem;'>Helpful but optional</span>
                            </div>""",
                            unsafe_allow_html=True,
                        )
                else:
                    st.caption("No additional helpful certs")
        else:
            st.info(f"No prerequisite data available for **{profile.exam_target}**. Check Microsoft Learn for the latest guidance.")

        st.markdown("---")

        # ── 2. Plan summary from agent ────────────────────────────────────────
        if plan:
            st.markdown("### 📋 Study Plan Agent Summary")
            st.markdown(
                f'<div class="card card-purple">{plan.plan_summary}</div>',
                unsafe_allow_html=True,
            )

        st.markdown("---")

        # ── 3. Gantt Chart ────────────────────────────────────────────────────
        st.markdown("### 📊 Weekly Study Plan — Gantt Chart")
        st.caption(
            "Each bar represents the study block for a domain. "
            "Domains are ordered by priority (critical → high → medium → low → self-test). "
            "The final week is reserved for practice exams & revision."
        )

        if plan and plan.tasks:
            _BASE = datetime.date(2026, 1, 5)  # Monday Week 1 (display anchor)

            gantt_rows = []
            for task in plan.tasks:
                start_dt = _BASE + datetime.timedelta(weeks=task.start_week - 1)
                end_dt   = _BASE + datetime.timedelta(weeks=task.end_week)  # exclusive end
                short_name = (task.domain_name
                              .replace("Implement ", "")
                              .replace(" Solutions", "")
                              .replace(" & Knowledge Mining", " & KM"))
                gantt_rows.append({
                    "Domain":         short_name,
                    "Start":          start_dt.isoformat(),
                    "Finish":         end_dt.isoformat(),
                    "Priority":       task.priority.title(),
                    "Level":          task.knowledge_level.title(),
                    "Hours":          f"{task.total_hours:.0f} h",
                    "Confidence":     f"{task.confidence_pct}%",
                    "_color":         PLAN_COLOUR.get(task.priority, "#888"),
                    "WeekRange":      (f"Week {task.start_week}" if task.start_week == task.end_week
                                       else f"Week {task.start_week}–{task.end_week}"),
                    "domain_id":      task.domain_id,
                })

            # Add review week bar
            review_start = _BASE + datetime.timedelta(weeks=plan.review_start_week - 1)
            review_end   = _BASE + datetime.timedelta(weeks=plan.review_start_week)
            gantt_rows.append({
                "Domain":     "🏁 Review & Practice Exam",
                "Start":      review_start.isoformat(),
                "Finish":     review_end.isoformat(),
                "Priority":   "Review",
                "Level":      "-",
                "Hours":      f"{profile.hours_per_week:.0f} h",
                "Confidence": "—",
                "_color":     PLAN_COLOUR["review"],
                "WeekRange":  f"Week {plan.review_start_week}",
                "domain_id":  "review",
            })

            import pandas as pd
            gantt_df = pd.DataFrame(gantt_rows)

            # Sort by start date so bars appear in schedule order top-to-bottom
            gantt_df = gantt_df.sort_values("Start", ascending=False)

            _COLOR_MAP = {
                row["Priority"]: row["_color"]
                for _, row in gantt_df.iterrows()
            }

            gantt_fig = px.timeline(
                gantt_df,
                x_start="Start",
                x_end="Finish",
                y="Domain",
                color="Priority",
                color_discrete_map=_COLOR_MAP,
                custom_data=["WeekRange", "Hours", "Level", "Confidence", "Priority"],
                labels={"Domain": ""},
            )

            gantt_fig.update_traces(
                hovertemplate=(
                    "<b>%{y}</b><br>"
                    "📅 %{customdata[0]}<br>"
                    "⏱ %{customdata[1]}<br>"
                    "📈 Level: %{customdata[2]}<br>"
                    "💯 Confidence: %{customdata[3]}<br>"
                    "🏷 Priority: %{customdata[4]}<extra></extra>"
                ),
            )

            # Replace date x-axis ticks with "Week N" labels
            week_ticks  = [(_BASE + datetime.timedelta(weeks=i)).isoformat()
                           for i in range(plan.total_weeks + 1)]
            week_labels = [f"Wk {i+1}" for i in range(plan.total_weeks + 1)]

            gantt_fig.update_layout(
                xaxis=dict(
                    tickvals=week_ticks,
                    ticktext=week_labels,
                    title="Study Weeks",
                    showgrid=True,
                    gridcolor="#eeeeee",
                ),
                yaxis=dict(title="", autorange=True),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.35,
                    title="Priority:",
                ),
                height=max(280, 60 + len(gantt_rows) * 42),
                margin=dict(l=10, r=20, t=20, b=10),
                paper_bgcolor="white",
                plot_bgcolor="white",
                bargap=0.25,
            )

            # Add week-boundary vertical lines
            for i in range(1, plan.total_weeks + 1):
                gantt_fig.add_vline(
                    x=(_BASE + datetime.timedelta(weeks=i - 1)).isoformat(),
                    line_width=1,
                    line_dash="dot",
                    line_color="#cccccc",
                )

            st.plotly_chart(gantt_fig, use_container_width=True)

            # Hour breakdown table
            st.markdown("#### ⏱ Hours Breakdown by Domain")
            task_table_rows = [
                {
                    "Domain":       (t.domain_name.replace("Implement ", "")
                                    .replace(" Solutions", "")
                                    .replace(" & Knowledge Mining", " & KM")),
                    "Weeks":        f"{t.start_week}–{t.end_week}" if t.start_week != t.end_week else str(t.start_week),
                    "Study Hours":  f"{t.total_hours:.0f} h",
                    "Priority":     t.priority.title(),
                    "Confidence":   f"{t.confidence_pct}%",
                    "Knowledge":    t.knowledge_level.title(),
                }
                for t in plan.tasks
            ]
            task_table_rows.append({
                "Domain":      "🏁 Review & Practice Exam",
                "Weeks":       str(plan.review_start_week),
                "Study Hours": f"{profile.hours_per_week:.0f} h",
                "Priority":    "Review",
                "Confidence":  "—",
                "Knowledge":   "—",
            })
            st.dataframe(
                pd.DataFrame(task_table_rows),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("Run the profiler to generate the study plan.")

        st.markdown("---")

        # ── 4. Existing profile cards (condensed) ─────────────────────────────
        st.markdown("### 📋 Profile Summary")
        _ps_c1, _ps_c2, _ps_c3 = st.columns(3)
        with _ps_c1:
            st.markdown(f"""
            <div class="card card-purple">
              <b>Learning Style:</b> {profile.learning_style.value.replace('_', ' ').title()}<br/>
              <b>Experience Level:</b> {profile.experience_level.value.replace('_', ' ').title()}<br/>
              <b>Total Study Hours:</b> {profile.total_budget_hours:.0f} h
              ({profile.hours_per_week:.0f} h/wk × {profile.weeks_available} wks)
            </div>
            """, unsafe_allow_html=True)

        with _ps_c2:
            if profile.modules_to_skip:
                st.markdown("**⏭ Skip / Fast-track**")
                for m in profile.modules_to_skip:
                    st.success(f"✓ {m}")
            else:
                st.info("No domains skipped — full study path required.")

        with _ps_c3:
            if profile.risk_domains:
                st.markdown("**⚠️ Priority Risk Domains**")
                for did in profile.risk_domains:
                    name = EXAM_DOMAIN_NAMES.get(did, did)
                    st.error(f"⚠ {name}")
            else:
                st.success("✅ No risk domains — all above threshold.")

        # Analogy map + Engagement notes (full width)
        _ae_c1, _ae_c2 = st.columns(2)
        with _ae_c1:
            if profile.analogy_map:
                st.markdown("#### 🔁 Skill Analogy Map")
                st.caption("Your existing skills mapped to Azure AI equivalents.")
                for skill, equiv in profile.analogy_map.items():
                    st.markdown(
                        f"""<div style="background:{BLUE_LITE};border-left:4px solid {BLUE};
                             padding:6px 12px;border-radius:6px;margin-bottom:6px;">
                             <b style='color:{BLUE};'>{skill}</b>
                             <span style='color:#555;'> → {equiv}</span></div>""",
                        unsafe_allow_html=True,
                    )

        with _ae_c2:
            st.markdown("#### 🔔 Engagement Notes")
            st.markdown(
                f'<div class="card card-gold"><i>{profile.engagement_notes}</i></div>',
                unsafe_allow_html=True,
            )

    # ── Tab 3: Learning Path ──────────────────────────────────────────────────
    with tab_path:
        st.markdown("### 📚 Curated Microsoft Learn Path")
        st.caption("Personalised MS Learn modules selected by the Learning Path Curator Agent based on your profile.")

        _lp: LearningPath = st.session_state.get("learning_path")
        if not _lp:
            st.info("Generate your learner profile first to see curated learning modules.")
        else:
            # Summary banner
            _pr_result = st.session_state.get("guardrail_path")
            st.markdown(
                f"""<div style="background:linear-gradient(135deg,#eff6ff,#dbeafe);
                     border-left:5px solid #2563eb;border-radius:10px;padding:12px 18px;
                     margin-bottom:16px;">
                  <b style="color:#1e3a8a;">📚 Learning Path Curator Agent</b><br/>
                  <span style="color:#374151;font-size:0.9rem;">{_lp.summary}</span>
                </div>""",
                unsafe_allow_html=True,
            )

            # Guardrail notices
            if _pr_result:
                for _gv in _pr_result.violations:
                    if _gv.level.value == "WARN":
                        st.warning(f"⚠️ [{_gv.code}] {_gv.message}")

            # Domain-by-domain module list
            _dom_order = sorted(
                profile.domain_profiles,
                key=lambda dp: (
                    0 if dp.domain_id in profile.risk_domains else
                    2 if dp.skip_recommended else 1
                ),
            )

            _priority_colour = {
                "core":        ("#bbf7d0", "#16a34a", "🔴 Core"),
                "supplemental":(  "#dbeafe", "#2563eb", "🟡 Supplemental"),
                "optional":    ("#f3f4f6", "#6b7280", "⚪ Optional"),
            }

            for _dp in _dom_order:
                _domain_modules = _lp.curated_paths.get(_dp.domain_id, [])
                _skip_flag = "⏩ Skipped" if _dp.domain_id in _lp.skipped_domains else ""

                with st.expander(
                    f"{'⏩ ' if _skip_flag else ''}**{_dp.domain_name}** "
                    f"— {len(_domain_modules)} module(s)"
                    + (f"  _(skipped – strong prior knowledge)_" if _skip_flag else ""),
                    expanded=(not bool(_skip_flag) and _dp.domain_id in profile.risk_domains),
                ):
                    if not _domain_modules:
                        st.info("Domain skipped based on strong prior knowledge.")
                        continue

                    for _mod in _domain_modules:
                        _bg, _bd, _plabel = _priority_colour.get(
                            _mod.priority, ("#f9f9f9", "#888", _mod.priority)
                        )
                        st.markdown(
                            f"""<div style="background:{_bg};border-left:4px solid {_bd};
                                 border-radius:8px;padding:10px 14px;margin-bottom:8px;
                                 display:flex;justify-content:space-between;align-items:center;
                                 flex-wrap:wrap;gap:6px;">
                              <div style="flex:3;min-width:200px;">
                                <a href="{_mod.url}" target="_blank"
                                   style="color:#1e40af;font-weight:600;text-decoration:none;
                                          font-size:0.92rem;">
                                  🔗 {_mod.title}
                                </a><br/>
                                <span style="color:#6b7280;font-size:0.78rem;">
                                  {_mod.module_type.title()} · {_mod.difficulty.title()} · ~{_mod.duration_min} min
                                </span>
                              </div>
                              <div style="font-size:0.78rem;color:{_bd};font-weight:700;">{_plabel}</div>
                            </div>""",
                            unsafe_allow_html=True,
                        )

            # Total hours vs budget
            _ratio = _lp.total_hours_est / max(profile.total_budget_hours, 1)
            st.markdown("---")
            _ce1, _ce2, _ce3 = st.columns(3)
            with _ce1:
                st.metric("Modules Curated", len(_lp.all_modules))
            with _ce2:
                st.metric("Estimated Hours", f"{_lp.total_hours_est:.1f} h")
            with _ce3:
                st.metric("Budget Utilisation", f"{_ratio:.0%}")

    # ── Tab 4: Recommendations ────────────────────────────────────────────────
    with tab_recs:
        st.markdown("### 💡 Personalisation Recommendation")
        st.markdown(
            f'<div class="card card-green">{profile.recommended_approach}</div>',
            unsafe_allow_html=True,
        )

        st.markdown("### 🏁 Predicted Readiness Outlook")
        ready_domains  = sum(1 for dp in profile.domain_profiles if dp.confidence_score >= 0.70)
        total_domains  = len(profile.domain_profiles)
        ready_pct      = ready_domains / total_domains

        col_a, col_b = st.columns([2, 1])
        with col_a:
            st.progress(ready_pct)
            st.caption(f"{ready_domains}/{total_domains} domains currently above 70% confidence.")
        with col_b:
            if ready_pct == 1.0:
                st.markdown(
                    '<div class="decision-ready"><b style="color:#107C10;">✓ On track for first-attempt pass</b></div>',
                    unsafe_allow_html=True,
                )
            elif ready_pct >= 0.66:
                st.markdown(
                    '<div class="decision-not-ready"><b style="color:#B4009E;">⚠ Likely 1 remediation cycle needed</b></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    '<div class="decision-not-ready"><b style="color:#d13438;">✗ Structured full prep recommended</b></div>',
                    unsafe_allow_html=True,
                )

        # ── Certification Recommendation Agent ────────────────────────────────
        st.markdown("### 🏅 Certification Recommendation Agent")
        _asmt_res = st.session_state.get("assessment_result")
        _prog_asmt = st.session_state.get("progress_assessment")
        _cert_agent = CertificationRecommendationAgent()

        if _asmt_res:
            _cert_rec: CertRecommendation = _cert_agent.recommend(profile, _asmt_res)
            st.session_state["cert_recommendation"] = _cert_rec
        elif _prog_asmt:
            _cert_rec: CertRecommendation = _cert_agent.recommend_from_readiness(profile, _prog_asmt)
            st.session_state["cert_recommendation"] = _cert_rec
        else:
            _cert_rec = None

        if _cert_rec:
            _go_c = "#16a34a" if _cert_rec.go_for_exam else "#dc2626"
            _go_bg = "#f0fdf4" if _cert_rec.go_for_exam else "#fff1f0"
            st.markdown(
                f"""<div style="background:{_go_bg};border:2px solid {_go_c};border-radius:10px;
                     padding:14px 18px;margin-bottom:14px;">
                  <div style="font-size:1.2rem;font-weight:800;color:{_go_c};">
                    {"✅ Ready to Book the Exam!" if _cert_rec.go_for_exam else "📖 More Preparation Needed"}
                  </div>
                  <div style="color:#374151;margin-top:4px;font-size:0.9rem;">{_cert_rec.summary}</div>
                </div>""",
                unsafe_allow_html=True,
            )

            if _cert_rec.exam_info:
                ei = _cert_rec.exam_info
                _ec1, _ec2, _ec3, _ec4 = st.columns(4)
                with _ec1: st.metric("Exam Code", ei.exam_code)
                with _ec2: st.metric("Passing Score", f"{ei.passing_score}/1000")
                with _ec3: st.metric("Duration", f"{ei.duration_minutes} min")
                with _ec4: st.metric("Cost", f"USD {ei.cost_usd}")
                st.markdown(
                    f"""<div class="card card-blue" style="margin-top:8px;">
                      <b>Exam:</b> {ei.exam_name}<br/>
                      <b>Format:</b> {ei.exam_format}<br/>
                      <b>Online Proctored:</b> {"✅ Yes" if ei.online_proctored else "No"}<br/>
                      <b>Schedule:</b> <a href="{ei.scheduling_url}" target="_blank">Pearson VUE</a> &nbsp;|&nbsp;
                      <b>Free Practice:</b> <a href="{ei.free_practice_url}" target="_blank">Official Practice Assessment</a>
                    </div>""",
                    unsafe_allow_html=True,
                )

            if _cert_rec.booking_checklist:
                st.markdown("#### ✅ Pre-Exam Booking Checklist")
                for _item in _cert_rec.booking_checklist:
                    st.checkbox(_item, key=f"chk_{hash(_item)[:8] if hasattr(hash(_item), '__getitem__') else abs(hash(_item))}")

            if _cert_rec.remediation_plan:
                st.markdown(
                    f'<div class="card card-pink">'
                    f'<b>📋 Remediation Plan</b><br/>{_cert_rec.remediation_plan}</div>',
                    unsafe_allow_html=True,
                )

            if _cert_rec.next_cert_suggestions:
                st.markdown("#### 🚀 Next Certification Recommendations")
                for _nc in _cert_rec.next_cert_suggestions:
                    _diff_c = {"foundational":"#16a34a","intermediate":"#2563eb","advanced":"#7c3aed","expert":"#dc2626"}.get(_nc.difficulty, "#888")
                    st.markdown(
                        f"""<div style="background:white;border:1px solid #e5e7eb;border-left:4px solid {_diff_c};
                             border-radius:8px;padding:12px 16px;margin-bottom:8px;">
                          <div style="font-weight:700;color:#111;font-size:0.96rem;">
                            <a href="{_nc.learn_url}" target="_blank" style="color:{_diff_c};text-decoration:none;">
                              {_nc.exam_code}
                            </a> — {_nc.exam_name}
                            <span style="margin-left:8px;font-size:0.75rem;color:{_diff_c};text-transform:uppercase;">
                              {_nc.difficulty}
                            </span>
                          </div>
                          <div style="color:#555;font-size:0.85rem;margin-top:4px;">{_nc.rationale}</div>
                          {f'<div style="color:#888;font-size:0.78rem;margin-top:3px;">⏱ Est. {_nc.timeline_est}</div>' if _nc.timeline_est else ""}
                        </div>""",
                        unsafe_allow_html=True,
                    )
        else:
            st.info(
                "Complete the **Knowledge Check** quiz or the **My Progress** check-in "
                "to unlock personalised certification booking recommendations.",
                icon="💡",
            )

        st.markdown("### 🔄 Agent Pipeline Status")
        _pipe_stages = [
            ("🎤 Learner Intake Agent",       "Intake",     "Collects raw student input",           True),
            ("🧠 Learner Profiling Agent",     "Profiling",  "Infers experience & domain knowledge", True),
            ("📚 Learning Path Curator",       "Curation",   "Maps MS Learn modules to domains",     "learning_path" in st.session_state),
            ("📅 Study Plan Agent",            "Planning",   "Gantt schedule + prerequisites",       "plan" in st.session_state),
            ("📈 Progress Agent",              "Progress",   "Mid-journey readiness scoring",        "progress_assessment" in st.session_state),
            ("🧪 Assessment Agent",            "Assessment", "Domain knowledge quiz",                "assessment_result" in st.session_state),
            ("🏅 Cert Recommendation Agent",   "Decision",   "Go/No-Go exam decision",               _cert_rec is not None),
        ]
        for _label, _block, _desc, _done in _pipe_stages:
            _bg  = "#f0fdf4" if _done else "#f9fafb"
            _bc  = "#16a34a" if _done else "#d1d5db"
            _ico = "✅" if _done else "⏳"
            st.markdown(
                f"""<div style="background:{_bg};border:1px solid {_bc};border-radius:8px;
                     padding:8px 14px;margin-bottom:6px;display:flex;align-items:center;gap:10px;">
                  <span style="font-size:1.1rem;">{_ico}</span>
                  <div>
                    <b style="color:#111;">{_label}</b>
                    <span style="color:#888;font-size:0.78rem;margin-left:6px;">[{_block}]</span><br/>
                    <span style="color:#555;font-size:0.82rem;">{_desc}</span>
                  </div>
                </div>""",
                unsafe_allow_html=True,
            )

    # ── Tab 4: My Progress ────────────────────────────────────────────────────
    with tab_progress:
        st.markdown("### 📈 My Progress Check-In")

        _has_plan = "plan" in st.session_state

        if not _has_plan:
            st.info(
                "Complete the intake form above and generate your learner profile first, "
                "then return here to log your progress and get a readiness assessment.",
                icon="ℹ️",
            )
        else:
            _plan: StudyPlan = st.session_state["plan"]
            _prior_snap = st.session_state.get("progress_snapshot")
            _prior_asmt = st.session_state.get("progress_assessment")

            # Welcome back callout for returning users
            if _prior_asmt:
                _pa: ReadinessAssessment = _prior_asmt
                _c = _pa.verdict_colour
                st.markdown(
                    f"""<div style="background:#f0f0f8;border-left:5px solid {_c};
                         border-radius:8px;padding:10px 16px;margin-bottom:12px;">
                      <b>Last check-in result:</b>
                      <span style="color:{_c};font-size:1.1rem;font-weight:700;margin-left:8px;">
                        {_pa.readiness_pct:.0f}% — {_pa.verdict_label}
                      </span>
                      &nbsp;|&nbsp;
                      <span style="color:{_pa.go_nogo_colour};font-weight:700;">
                        {_pa.exam_go_nogo}
                      </span>
                      <span style="color:#555;font-size:0.85rem;margin-left:8px;">
                        {_pa.hours_remaining:.0f} h remaining · {_pa.weeks_remaining} wk(s) left
                      </span>
                    </div>""",
                    unsafe_allow_html=True,
                )

            # ── Progress Check-In Form ────────────────────────────────────────
            st.markdown("#### ✏️ Log Your Study Session")
            with st.form("progress_form", clear_on_submit=False):
                _pcol1, _pcol2 = st.columns(2)
                with _pcol1:
                    _hours_spent = st.number_input(
                        "Total hours studied so far",
                        min_value=0.0,
                        max_value=float(profile.total_budget_hours * 2),
                        value=float(
                            _prior_snap.total_hours_spent if _prior_snap else 0.0
                        ),
                        step=0.5,
                        help=f"Your full budget is {profile.total_budget_hours:.0f} h",
                    )
                    _weeks_elapsed = st.number_input(
                        "Weeks elapsed since you started",
                        min_value=0,
                        max_value=profile.weeks_available + 4,
                        value=int(
                            _prior_snap.weeks_elapsed if _prior_snap else 0
                        ),
                        step=1,
                    )
                with _pcol2:
                    _prac_opt = st.selectbox(
                        "Have you taken a practice exam?",
                        options=["no", "some", "yes"],
                        index=(
                            ["no","some","yes"].index(_prior_snap.done_practice_exam)
                            if _prior_snap else 0
                        ),
                    )
                    _prac_score = st.number_input(
                        "Practice exam score (%)",
                        min_value=0,
                        max_value=100,
                        value=int(_prior_snap.practice_score_pct or 0)
                              if _prior_snap else 0,
                        step=1,
                        disabled=(_prac_opt == "no"),
                        help="Enter 0 if you haven't done a scored test yet",
                    )

                st.markdown("##### 🎯 Domain Self-Rating")
                st.caption(
                    "Rate your current confidence in each domain: "
                    "1 = barely started, 3 = working knowledge, 5 = very confident."
                )

                _domain_ratings: dict[str, int] = {}
                _prev_ratings = {
                    dp.domain_id: dp.self_rating
                    for dp in _prior_snap.domain_progress
                } if _prior_snap else {}

                _dr_cols = st.columns(2)
                for _di, dp in enumerate(profile.domain_profiles):
                    _short = (dp.domain_name
                              .replace("Implement ", "")
                              .replace(" Solutions", "")
                              .replace(" & Knowledge Mining", " & KM"))
                    with _dr_cols[_di % 2]:
                        _domain_ratings[dp.domain_id] = st.slider(
                            _short,
                            min_value=1,
                            max_value=5,
                            value=_prev_ratings.get(dp.domain_id, max(1, int(dp.confidence_score * 4) + 1)),
                            help=dp.domain_name,
                            key=f"dr_{dp.domain_id}",
                        )

                _notes = st.text_area(
                    "Optional notes / blockers",
                    value=_prior_snap.notes if _prior_snap else "",
                    placeholder="e.g. Struggling with Azure OpenAI RAG patterns, skipped conversational AI docs",
                    height=70,
                )

                _assess_btn = st.form_submit_button(
                    "🔍 Assess My Readiness",
                    type="primary",
                    use_container_width=True,
                )

            # ── Run assessment on submit ──────────────────────────────────────
            if _assess_btn:
                _snap = ProgressSnapshot(
                    total_hours_spent  = _hours_spent,
                    weeks_elapsed      = _weeks_elapsed,
                    domain_progress    = [
                        DomainProgress(
                            domain_id   = dp.domain_id,
                            domain_name = dp.domain_name,
                            self_rating = _domain_ratings[dp.domain_id],
                            hours_spent = 0.0,
                        )
                        for dp in profile.domain_profiles
                    ],
                    done_practice_exam  = _prac_opt,
                    practice_score_pct  = _prac_score if _prac_opt != "no" else None,
                    email               = st.session_state.get("user_email", ""),
                    notes               = _notes,
                )
                with st.spinner("🤖 Progress Agent: computing readiness…"):
                    _asmt = ProgressAgent().assess(profile, _snap)
                st.session_state["progress_snapshot"] = _snap
                st.session_state["progress_assessment"] = _asmt
                # Save progress to DB
                _login_nm = st.session_state.get("login_name", "")
                if _login_nm and _login_nm != "Admin":
                    save_progress(_login_nm, _dc_to_json(_snap), _dc_to_json(_asmt))
                st.rerun()

            # ── Show assessment results ───────────────────────────────────────
            if _prior_asmt:
                _asmt: ReadinessAssessment = _prior_asmt
                _snap: ProgressSnapshot   = st.session_state["progress_snapshot"]
                st.markdown("---")
                st.markdown("### 🎯 Readiness Assessment")

                # ── GO / NO-GO + gauge side by side ──────────────────────────
                _gc1, _gc2 = st.columns([1, 1])

                with _gc1:
                    # Plotly gauge
                    _gauge = go.Figure(go.Indicator(
                        mode  = "gauge+number+delta",
                        value = _asmt.readiness_pct,
                        delta = {"reference": 75, "valueformat": ".0f",
                                 "increasing": {"color": GREEN},
                                 "decreasing": {"color": "#d13438"}},
                        gauge = {
                            "axis":      {"range": [0, 100], "tickformat": ".0f",
                                          "ticksuffix": "%"},
                            "bar":       {"color": _asmt.verdict_colour, "thickness": 0.25},
                            "steps":     [
                                {"range": [0,  45], "color": "#fde7f3"},
                                {"range": [45, 60], "color": "#fff4ce"},
                                {"range": [60, 75], "color": "#eef6ff"},
                                {"range": [75,100], "color": "#e9f7ee"},
                            ],
                            "threshold": {"line": {"color": "#5c2d91", "width": 3},
                                          "thickness": 0.8, "value": 75},
                        },
                        title = {"text": f"Readiness Score<br><span style='font-size:0.85rem;color:#888;'>"
                                         f"(target ≥ 75%)</span>"},
                        number = {"suffix": "%", "font": {"color": _asmt.verdict_colour, "size": 44}},
                    ))
                    _gauge.update_layout(
                        height=260,
                        margin=dict(t=40, b=10, l=20, r=20),
                        paper_bgcolor="white",
                    )
                    st.plotly_chart(_gauge, use_container_width=True)

                with _gc2:
                    # GO / NO-GO card
                    _gnc = _asmt.go_nogo_colour
                    st.markdown(
                        f"""<div style="border:3px solid {_gnc};border-radius:12px;
                             padding:20px 24px;text-align:center;background:white;
                             box-shadow:0 4px 12px rgba(0,0,0,0.08);margin-top:12px;">
                          <div style="font-size:0.9rem;color:#888;font-weight:600;
                               text-transform:uppercase;letter-spacing:.08em;">Exam Decision</div>
                          <div style="font-size:2.4rem;font-weight:800;color:{_gnc};
                               margin:6px 0;">{_asmt.exam_go_nogo}</div>
                          <div style="font-size:0.88rem;color:#444;line-height:1.5;">
                            {_asmt.go_nogo_reason}
                          </div>
                        </div>""",
                        unsafe_allow_html=True,
                    )

                    # Hours + Weeks KPIs
                    st.markdown("<div style='margin-top:12px;'></div>", unsafe_allow_html=True)
                    _kc1, _kc2 = st.columns(2)
                    with _kc1:
                        st.metric("Hours Spent",
                                  f"{_snap.total_hours_spent:.0f} h",
                                  f"{_asmt.hours_progress_pct:.0f}% of budget")
                    with _kc2:
                        _wrem_delta = f"{_asmt.weeks_remaining} wk(s) left"
                        st.metric("Weeks Elapsed",
                                  f"{_snap.weeks_elapsed} / {profile.weeks_available}",
                                  _wrem_delta)

                # ── Nudge alerts ──────────────────────────────────────────────
                st.markdown("### 🔔 Smart Nudges & Alerts")
                _nudge_style = {
                    NudgeLevel.DANGER:  ("🚨", "#fde7f3", "#d13438"),
                    NudgeLevel.WARNING: ("⚠️", "#fff4ce", "#ca5010"),
                    NudgeLevel.INFO:    ("💡", "#eef6ff", "#0078d4"),
                    NudgeLevel.SUCCESS: ("✅", "#e9f7ee", "#107c10"),
                }
                for _n in _asmt.nudges:
                    _icon, _bg, _border = _nudge_style.get(
                        _n.level, ("ℹ️", "#f5f5f5", "#888")
                    )
                    _msg = (_n.message
                            .replace("**", "<b>", 1).replace("**", "</b>", 1)
                            .replace("**", "<b>", 1).replace("**", "</b>", 1))
                    st.markdown(
                        f"""<div style="background:{_bg};border-left:5px solid {_border};
                             border-radius:8px;padding:12px 16px;margin-bottom:10px;">
                          <b style="color:{_border};">{_icon} {_n.title}</b><br/>
                          <span style="font-size:0.87rem;color:#333;">{_msg}</span>
                        </div>""",
                        unsafe_allow_html=True,
                    )

                # ── Domain status table ───────────────────────────────────────
                st.markdown("### 📊 Domain Progress vs Plan")
                st.caption(
                    "Compares your self-rating today against where you should be "
                    "at this point in your study plan."
                )
                _status_meta = {
                    "ahead":    ("✓ Ahead",    GREEN,    "🟢"),
                    "on_track": ("◑ On Track", BLUE,     "🔵"),
                    "behind":   ("⚠ Behind",   GOLD,     "🟡"),
                    "critical": ("🚨 Critical", "#d13438","🔴"),
                }
                for _ds in _asmt.domain_status:
                    _sl, _sc, _si = _status_meta.get(
                        _ds.status, ("?", "#888", "⚪")
                    )
                    _stars_filled  = "★" * _ds.actual_rating
                    _stars_empty   = "☆" * (5 - _ds.actual_rating)
                    _exp_stars     = "★" * int(round(_ds.expected_rating))
                    _exp_empty     = "☆" * (5 - int(round(_ds.expected_rating)))
                    _short_name    = (_ds.domain_name
                                      .replace("Implement ", "")
                                      .replace(" Solutions", "")
                                      .replace(" & Knowledge Mining", " & KM"))
                    st.markdown(
                        f"""<div style="display:flex;align-items:center;gap:12px;
                             padding:8px 12px;border-radius:8px;margin-bottom:6px;
                             background:white;border:1px solid #eeeeee;
                             border-left:4px solid {_sc};">
                          <span style="font-size:1.1rem;">{_si}</span>
                          <span style="flex:2;font-weight:600;color:#222;">{_short_name}</span>
                          <span style="flex:1;text-align:center;font-size:1rem;color:#f4a523;">
                            {_stars_filled}<span style="color:#ccc;">{_stars_empty}</span>
                            <span style="font-size:0.75rem;color:#888;margin-left:4px;">
                              (you: {_ds.actual_rating})
                            </span>
                          </span>
                          <span style="flex:1;text-align:center;font-size:0.82rem;color:#888;">
                            expected: {_exp_stars}<span style="color:#ccc;">{_exp_empty}</span>
                            ({_ds.expected_rating:.1f})
                          </span>
                          <span style="color:{_sc};font-weight:600;font-size:0.85rem;">{_sl}</span>
                        </div>""",
                        unsafe_allow_html=True,
                    )

                # ── Recommended focus ─────────────────────────────────────────
                if _asmt.recommended_focus:
                    _focus_names = [
                        EXAM_DOMAIN_NAMES.get(did, did)
                        for did in _asmt.recommended_focus
                    ]
                    st.markdown(
                        f"""<div style="background:{PURPLE_LITE};border-left:5px solid {PURPLE};
                             border-radius:8px;padding:10px 16px;margin-top:8px;">
                          <b>🎯 Recommended focus for your next study sessions:</b><br/>
                          {"".join(f"<span style='margin-right:8px;'>&nbsp;• {n}</span>" for n in _focus_names)}
                        </div>""",
                        unsafe_allow_html=True,
                    )

                st.markdown("---")

                # ── Email Weekly Summary ──────────────────────────────────────
                st.markdown("### 📧 Weekly Summary Email")
                _email_addr = st.session_state.get("user_email", "")

                _ec1, _ec2 = st.columns([2, 1])
                with _ec1:
                    _send_to = st.text_input(
                        "Send report to",
                        value=_email_addr,
                        placeholder="you@example.com",
                        key="send_email_input",
                        help="Enter your email to receive a weekly HTML summary report.",
                    )
                with _ec2:
                    st.markdown("<div style='margin-top:28px;'></div>",
                                unsafe_allow_html=True)
                    _do_send = st.button(
                        "📤 Send Weekly Report",
                        type="primary",
                        use_container_width=True,
                    )

                if _do_send:
                    if not _send_to:
                        st.error("Please enter an email address.")
                    else:
                        _html_body = generate_weekly_summary(profile, _snap, _asmt)
                        _subject   = (
                            f"{profile.exam_target} Weekly Study Report — "
                            f"{profile.student_name} — "
                            f"Readiness {_asmt.readiness_pct:.0f}%"
                        )
                        with st.spinner("Sending email…"):
                            _ok, _msg = attempt_send_email(_send_to, _subject, _html_body)
                        if _ok:
                            st.success(f"✅ {_msg}")
                        else:
                            st.warning(
                                f"⚠️ {_msg}\n\n"
                                "**Email preview** is shown below — copy-paste or "
                                "screenshot it to share manually."
                            )
                            # Always show preview when send fails
                            with st.expander("📄 Preview weekly report email", expanded=True):
                                _html_body = generate_weekly_summary(profile, _snap, _asmt)
                                st.markdown(_html_body, unsafe_allow_html=True)

                # Preview button (always available)
                with st.expander("👁️ Preview weekly report (no email needed)"):
                    _html_prev = generate_weekly_summary(profile, _snap, _asmt)
                    st.markdown(_html_prev, unsafe_allow_html=True)
                    st.download_button(
                        label="⬇️ Download report as HTML",
                        data=_html_prev.encode("utf-8"),
                        file_name=f"weekly_report_{profile.student_name.replace(' ','_')}.html",
                        mime="text/html",
                        use_container_width=True,
                    )

    # ── Tab 6: Knowledge Check (Assessment Agent) ────────────────────────────
    with tab_quiz:
        st.markdown("### 🧪 Knowledge Check — Readiness Quiz")
        st.caption(
            "A domain-weighted mini-exam generated by the Assessment Agent. "
            "Passing score ≥ 60%. Your result feeds the Certification Recommendation Agent."
        )

        _q_count = st.slider(
            "Number of questions",
            min_value=5, max_value=30,
            value=st.session_state.get("_quiz_q_count", 10),
            key="_quiz_q_count",
        )

        if st.button("🎲 Generate New Quiz", type="primary"):
            _agent = AssessmentAgent()
            _new_assess = _agent.generate(profile, n_questions=_q_count)
            _gr = GuardrailsPipeline().check_assessment(_new_assess)
            if _gr.blocked:
                for _v in _gr.violations:
                    st.error(f"🚫 Assessment guardrail [{_v.code}]: {_v.message}")
            else:
                st.session_state["assessment"] = _new_assess
                st.session_state.pop("assessment_result", None)  # clear prior result
                st.session_state.pop("assessment_answers", None)
                st.rerun()

        _active_assess: Assessment = st.session_state.get("assessment")

        if not _active_assess:
            st.info("Press **Generate New Quiz** to start your knowledge check.", icon="🎲")
        else:
            # If result already exists, show it
            _prior_result: AssessmentResult = st.session_state.get("assessment_result")

            if _prior_result:
                _score  = _prior_result.score_pct
                _passed = _prior_result.passed
                _psc    = "#16a34a" if _passed else "#dc2626"
                st.markdown(
                    f"""<div style="background:{'#f0fdf4' if _passed else '#fff1f0'};border:2px solid {_psc};
                         border-radius:10px;padding:16px 20px;margin-bottom:16px;">
                      <div style="font-size:1.4rem;font-weight:800;color:{_psc};">
                        {'✅ PASSED' if _passed else '❌ NOT PASSED'} — {_score:.0f}%
                        <span style="font-size:0.85rem;color:#888;margin-left:8px;">
                          ({_prior_result.correct_count}/{_prior_result.total_count} correct)
                        </span>
                      </div>
                      <div style="color:#374151;margin-top:6px;font-size:0.9rem;">
                        {_prior_result.verdict}<br/>
                        <b>Next step:</b> {_prior_result.recommendation}
                      </div>
                    </div>""",
                    unsafe_allow_html=True,
                )

                # Domain scores
                st.markdown("#### 📊 Domain Breakdown")
                for _did, _ds in sorted(_prior_result.domain_scores.items(), key=lambda x: x[1]):
                    _dc = "#16a34a" if _ds >= 70 else ("#f59e0b" if _ds >= 50 else "#dc2626")
                    _dn = EXAM_DOMAIN_NAMES.get(_did, _did).replace("Implement ", "").replace(" Solutions","")
                    st.markdown(
                        f"""<div style="display:flex;align-items:center;gap:10px;
                             margin-bottom:6px;padding:6px 12px;border-radius:6px;
                             background:white;border:1px solid #e5e7eb;border-left:4px solid {_dc};">
                          <span style="flex:2;font-weight:600;color:#111;">{_dn}</span>
                          <span style="flex:1;font-weight:700;color:{_dc};">{_ds:.0f}%</span>
                          <span style="color:#888;font-size:0.8rem;">
                            {'✓ Pass' if _ds >= 60 else '✗ Review'}
                          </span>
                        </div>""",
                        unsafe_allow_html=True,
                    )

                # Per-question feedback
                with st.expander("📝 View detailed question feedback"):
                    for _i, (_q, _fb) in enumerate(zip(
                        _active_assess.questions, _prior_result.feedback
                    )):
                        _qc = "#16a34a" if _fb.correct else "#dc2626"
                        _icon = "✅" if _fb.correct else "❌"
                        st.markdown(
                            f"""<div style="border:1px solid {'#bbf7d0' if _fb.correct else '#fca5a5'};
                                 border-radius:8px;padding:12px 16px;margin-bottom:10px;
                                 background:{'#f0fdf4' if _fb.correct else '#fff1f0'};">
                              <b style="color:#111;">{_icon} Q{_i+1}. {_q.question}</b><br/>
                              <span style="color:{_qc};font-size:0.88rem;">
                                You chose: <b>{_q.options[_fb.learner_index]}</b>
                              </span>
                              {'<br/><span style="color:#dc2626;font-size:0.88rem;">Correct: <b>' + _q.options[_q.correct_index] + '</b></span>' if not _fb.correct else ""}
                              <br/><span style="color:#555;font-size:0.83rem;font-style:italic;">
                                {_fb.explanation}
                              </span>
                            </div>""",
                            unsafe_allow_html=True,
                        )

                if st.button("🔄 Retake Quiz", use_container_width=True):
                    st.session_state.pop("assessment_result", None)
                    st.session_state.pop("assessment_answers", None)
                    st.rerun()

            else:
                # Show quiz form
                st.markdown(f"#### 📋 Answer the {len(_active_assess.questions)} Questions Below")
                st.markdown(
                    f"""<div class="card card-blue">
                      <b>Exam:</b> {_active_assess.exam_target} &nbsp;|&nbsp;
                      <b>Questions:</b> {_active_assess.total_marks} &nbsp;|&nbsp;
                      <b>Pass mark:</b> {_active_assess.pass_mark_pct:.0f}%
                    </div>""",
                    unsafe_allow_html=True,
                )

                _answers: list[int] = []
                with st.form("quiz_form"):
                    for _qi, _q in enumerate(_active_assess.questions):
                        _opt_letters = ["A", "B", "C", "D"]
                        _domain_short = _q.domain_name.replace("Implement ", "").replace(" Solutions","").replace(" & Knowledge Mining"," & KM")
                        st.markdown(
                            f"""<div style="background:white;border:1px solid #e5e7eb;border-radius:8px;
                                 padding:12px 16px;margin-bottom:4px;">
                              <span style="font-size:0.72rem;color:#6b7280;font-weight:700;text-transform:uppercase;">
                                Q{_qi+1} · {_domain_short} · {_q.difficulty.title()}
                              </span><br/>
                              <b style="color:#111;">{_q.question}</b>
                            </div>""",
                            unsafe_allow_html=True,
                        )
                        _chosen = st.radio(
                            label=f"q{_qi+1}",
                            options=list(range(len(_q.options))),
                            format_func=lambda i, opts=_q.options: opts[i],
                            label_visibility="collapsed",
                            horizontal=False,
                            key=f"q_{_qi}",
                        )
                        _answers.append(_chosen)

                    _submit_quiz = st.form_submit_button(
                        "📤 Submit Answers & Get Score",
                        type="primary",
                        use_container_width=True,
                    )

                if _submit_quiz:
                    _agent2 = AssessmentAgent()
                    _result = _agent2.evaluate(_active_assess, _answers)
                    st.session_state["assessment_result"] = _result
                    st.session_state["assessment_answers"] = _answers
                    # Save to DB
                    _login_nm = st.session_state.get("login_name", "")
                    if _login_nm and _login_nm != "Admin":
                        save_assessment(
                            _login_nm,
                            _dc_to_json(_active_assess),
                            _dc_to_json(_result),
                        )
                    # Clear cert rec so it regenerates
                    st.session_state.pop("cert_recommendation", None)
                    st.rerun()

    # ── Tab 7: Raw JSON ───────────────────────────────────────────────────────
    with tab_json:
        col_j1, col_j2 = st.columns(2)
        with col_j1:
            st.markdown("#### Raw Student Input")
            st.json(_dc.asdict(raw))
        with col_j2:
            st.markdown("#### Generated Learner Profile")
            st.json(profile.model_dump())

        st.download_button(
            label="⬇️ Download profile as JSON",
            data=profile.model_dump_json(indent=2),
            file_name=f"learner_profile_{raw.student_name.replace(' ', '_')}.json",
            mime="application/json",
            width="stretch",
        )
