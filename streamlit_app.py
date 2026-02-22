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
from cert_prep.mock_profiler import run_mock_profiling, run_mock_profiling_with_trace
from cert_prep.study_plan_agent import StudyPlanAgent, StudyPlan, PRIORITY_COLOUR as PLAN_COLOUR
from cert_prep.progress_agent import (
    ProgressAgent, ProgressSnapshot, DomainProgress,
    ReadinessAssessment, generate_weekly_summary, attempt_send_email,
    NudgeLevel,
)
from cert_prep.learning_path_curator import LearningPathCuratorAgent, LearningPath, LearningModule
from cert_prep.assessment_agent import AssessmentAgent, Assessment, AssessmentResult
from cert_prep.cert_recommendation_agent import (
    CertificationRecommendationAgent, CertRecommendation,
)
from cert_prep.guardrails import (
    GuardrailsPipeline, GuardrailResult, GuardrailLevel,
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
    # ── Microsoft Fluent-inspired login CSS ──────────────────────────────────
    st.markdown("""
    <style>
      /* Hide sidebar & header, collapse top padding */
      [data-testid="stSidebar"] { display: none; }
      [data-testid="stHeader"] { display: none; }
      .block-container { padding-top: 1rem !important; padding-bottom: 0.5rem !important; }
      /* MS-style dark mesh gradient background */
      [data-testid="stAppViewContainer"] {
        background:
          radial-gradient(ellipse at 20% 50%, rgba(0,120,212,0.15) 0%, transparent 50%),
          radial-gradient(ellipse at 80% 20%, rgba(80,230,255,0.08) 0%, transparent 40%),
          radial-gradient(ellipse at 60% 80%, rgba(0,183,195,0.10) 0%, transparent 45%),
          linear-gradient(145deg, #0a0a1a 0%, #0f1b2d 35%, #0d1117 70%, #050914 100%);
      }
      /* ── Left hero ────────────────────────────────── */
      .ms-badge {
        display: inline-flex; align-items: center; gap: 8px;
        background: rgba(0,120,212,0.12);
        border: 1px solid rgba(0,120,212,0.25);
        color: #50E6FF; font-size: 0.72rem; font-weight: 600;
        padding: 5px 16px; border-radius: 20px;
        letter-spacing: 0.06em; text-transform: uppercase;
        margin-bottom: 10px;
      }
      .ms-heading {
        color: #ffffff; font-size: 2.4rem; font-weight: 700;
        line-height: 1.15; letter-spacing: -0.02em;
        margin: 0 0 10px;
        font-family: 'Segoe UI', -apple-system, sans-serif;
      }
      .ms-heading .grad {
        background: linear-gradient(90deg, #50E6FF 0%, #0078D4 50%, #005A9E 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        background-clip: text;
      }
      .ms-sub {
        color: rgba(255,255,255,0.55); font-size: 0.92rem;
        line-height: 1.6; margin-bottom: 20px;
        font-family: 'Segoe UI', sans-serif;
      }
      /* Benefit 2×2 grid */
      .ben-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 16px; }
      .ben-card {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.07);
        border-radius: 12px; padding: 14px;
        transition: border-color 0.2s;
      }
      .ben-card:hover { border-color: rgba(0,120,212,0.3); }
      .ben-card .ic {
        width: 34px; height: 34px; border-radius: 8px;
        display: flex; align-items: center; justify-content: center;
        font-size: 1.1rem; margin-bottom: 6px;
      }
      .ben-card h4 {
        color: #E8EDF3; font-size: 0.82rem; font-weight: 600;
        margin: 0 0 2px; font-family: 'Segoe UI', sans-serif;
      }
      .ben-card p {
        color: rgba(255,255,255,0.38); font-size: 0.72rem;
        margin: 0; line-height: 1.35;
      }
      .ic-blue { background: rgba(0,120,212,0.15); border: 1px solid rgba(0,120,212,0.25); }
      .ic-teal { background: rgba(0,183,195,0.15); border: 1px solid rgba(0,183,195,0.25); }
      .ic-cyan { background: rgba(80,230,255,0.12); border: 1px solid rgba(80,230,255,0.2); }
      .ic-green { background: rgba(16,124,16,0.15); border: 1px solid rgba(16,124,16,0.25); }
      /* Stats bar */
      .ms-stats {
        display: flex; gap: 0; border-radius: 10px; overflow: hidden;
        border: 1px solid rgba(255,255,255,0.06);
      }
      .ms-stat {
        flex: 1; text-align: center; padding: 12px 6px;
        background: rgba(255,255,255,0.02);
        border-right: 1px solid rgba(255,255,255,0.06);
      }
      .ms-stat:last-child { border-right: none; }
      .ms-stat-n { color: #50E6FF; font-size: 1.3rem; font-weight: 800; }
      .ms-stat-l {
        color: rgba(255,255,255,0.38); font-size: 0.62rem;
        text-transform: uppercase; letter-spacing: 0.06em; margin-top: 2px;
      }
      /* ── Right sign-in panel ────────────────────── */
      .signin-title {
        text-align: center; color: #fff; font-size: 1.2rem;
        font-weight: 700; margin-bottom: 2px;
        font-family: 'Segoe UI', sans-serif;
      }
      .signin-sub {
        text-align: center; color: rgba(255,255,255,0.38);
        font-size: 0.76rem; margin-bottom: 10px;
      }
      /* Quick-login demo user cards (visual only) */
      .demo-grid { display: flex; gap: 8px; margin-bottom: 4px; }
      .demo-card {
        flex: 1; background: rgba(0,120,212,0.07);
        border: 1px solid rgba(0,120,212,0.16);
        border-radius: 10px; padding: 10px 6px;
        text-align: center; transition: all 0.2s;
      }
      .demo-card:hover { background: rgba(0,120,212,0.14); border-color: #0078D4; }
      .demo-card .dm-ic { font-size: 1.2rem; margin-bottom: 2px; }
      .demo-card .dm-nm { color: #E8EDF3; font-size: 0.72rem; font-weight: 600; }
      .demo-card .dm-rl { color: rgba(255,255,255,0.32); font-size: 0.62rem; }
      /* Quick-login Streamlit buttons */
      .stButton > button {
        background: rgba(0,120,212,0.12) !important;
        border: 1px solid rgba(0,120,212,0.25) !important;
        border-radius: 8px !important;
        color: #50E6FF !important;
        font-size: 0.78rem !important;
        font-weight: 600 !important;
        padding: 6px 8px !important;
        font-family: 'Segoe UI', sans-serif !important;
        transition: all 0.15s;
      }
      .stButton > button:hover {
        background: rgba(0,120,212,0.25) !important;
        border-color: #0078D4 !important;
      }
      /* Divider */
      .or-sep {
        display: flex; align-items: center; gap: 10px;
        margin: 8px 0 8px; color: rgba(255,255,255,0.2);
        font-size: 0.7rem;
      }
      .or-sep::before, .or-sep::after {
        content: ''; flex: 1; height: 1px;
        background: rgba(255,255,255,0.08);
      }
      /* Radio role selector */
      div[data-testid="stRadio"] label,
      div[data-testid="stRadio"] [role="radiogroup"] label {
        background: rgba(255,255,255,0.04) !important;
        border: 1px solid rgba(255,255,255,0.10) !important;
        border-radius: 8px !important;
        padding: 9px 14px !important;
        transition: all 0.2s ease; cursor: pointer;
        margin-bottom: 2px !important;
      }
      div[data-testid="stRadio"] label:hover {
        background: rgba(0,120,212,0.10) !important;
        border-color: rgba(0,120,212,0.30) !important;
      }
      /* Force ALL radio label text visible */
      div[data-testid="stRadio"] label *,
      div[data-testid="stRadio"] label span,
      div[data-testid="stRadio"] label p,
      div[data-testid="stRadio"] label div,
      div[data-testid="stRadio"] [role="radiogroup"] label *,
      div[data-testid="stHorizontalRadio"] label *,
      div[data-testid="stHorizontalRadio"] label {
        color: #CBD5E1 !important;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        font-family: 'Segoe UI', sans-serif !important;
      }
      /* Selected radio */
      div[data-testid="stRadio"] label:has(input:checked) {
        background: rgba(0,120,212,0.18) !important;
        border-color: #0078D4 !important;
      }
      div[data-testid="stRadio"] label:has(input:checked) *,
      div[data-testid="stRadio"] label:has(input:checked) span,
      div[data-testid="stRadio"] label:has(input:checked) p {
        color: #50E6FF !important;
      }
      div[data-testid="stHorizontalRadio"] label:has(input:checked) {
        background: rgba(0,120,212,0.18) !important;
        border-color: #0078D4 !important;
      }
      div[data-testid="stHorizontalRadio"] label:has(input:checked) * {
        color: #50E6FF !important;
      }
      /* Text inputs */
      .stTextInput input {
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.10) !important;
        border-radius: 8px !important;
        color: #fff !important; padding: 10px 14px !important;
        font-family: 'Segoe UI', sans-serif !important;
      }
      .stTextInput input:focus {
        border-color: #0078D4 !important;
        box-shadow: 0 0 0 2px rgba(0,120,212,0.2) !important;
      }
      .stTextInput input::placeholder { color: rgba(255,255,255,0.28) !important; }
      /* Submit button — Microsoft blue */
      .stFormSubmitButton button {
        background: #0078D4 !important;
        border: none !important; border-radius: 8px !important;
        padding: 11px !important; font-size: 0.95rem !important;
        font-weight: 600 !important; color: #fff !important;
        font-family: 'Segoe UI', sans-serif !important;
        transition: background 0.15s ease, box-shadow 0.15s ease;
      }
      .stFormSubmitButton button:hover {
        background: #106EBE !important;
        box-shadow: 0 4px 14px rgba(0,120,212,0.35) !important;
      }
      .role-desc {
        text-align: center; color: rgba(255,255,255,0.38);
        font-size: 0.74rem; margin: 4px 0 8px;
        min-height: 24px;
      }
    </style>
    """, unsafe_allow_html=True)

    # ── Two-panel layout ─────────────────────────────────────────────────────
    _left, _spacer, _right = st.columns([1.2, 0.08, 0.72])

    # ── LEFT: Hero + benefits ──────────────────────────────────────────────
    with _left:
        st.markdown("""
        <span class="ms-badge">
          <svg width="16" height="16" viewBox="0 0 23 23"><rect width="11" height="11" fill="#f25022"/><rect x="12" width="11" height="11" fill="#7fba00"/><rect y="12" width="11" height="11" fill="#00a4ef"/><rect x="12" y="12" width="11" height="11" fill="#ffb900"/></svg>
          Agents League · Battle #2
        </span>
        <h1 class="ms-heading">
          Your AI-Powered<br/>
          <span class="grad">Certification Coach</span>
        </h1>
        <p class="ms-sub">
          Six specialised AI agents profile your skills, build a personalised
          study plan, quiz you on weak areas, and tell you exactly when
          you're ready to book your exam.
        </p>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="ben-grid">
          <div class="ben-card">
            <div class="ic ic-blue">🧠</div>
            <h4>Intelligent Profiling</h4>
            <p>AI maps your strengths &amp; gaps across every exam domain automatically.</p>
          </div>
          <div class="ben-card">
            <div class="ic ic-teal">🗺️</div>
            <h4>Personalised Study Plans</h4>
            <p>Week-by-week schedule weighted by exam blueprint with MS Learn links.</p>
          </div>
          <div class="ben-card">
            <div class="ic ic-cyan">🧪</div>
            <h4>Adaptive Quizzes</h4>
            <p>Domain-weighted, exam-style questions focusing on your weakest areas.</p>
          </div>
          <div class="ben-card">
            <div class="ic ic-green">📊</div>
            <h4>Readiness Verdict</h4>
            <p>GO / NO-GO recommendation based on scores, study hours &amp; practice exams.</p>
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="ms-stats">
          <div class="ms-stat"><div class="ms-stat-n">6</div><div class="ms-stat-l">AI Agents</div></div>
          <div class="ms-stat"><div class="ms-stat-n">30+</div><div class="ms-stat-l">Certifications</div></div>
          <div class="ms-stat"><div class="ms-stat-n">100%</div><div class="ms-stat-l">Personalised</div></div>
          <div class="ms-stat"><div class="ms-stat-n">∞</div><div class="ms-stat-l">Practice Qs</div></div>
        </div>
        """, unsafe_allow_html=True)

    # ── RIGHT: Sign-in form ────────────────────────────────────────────────
    with _right:
        st.markdown("""
        <div style="text-align:center;margin-bottom:4px;">
          <div style="font-size:1.8rem;">🎓</div>
        </div>
        """, unsafe_allow_html=True)
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
                st.session_state["authenticated"] = True
                st.session_state["login_name"] = "Alex Chen"
                st.session_state["user_type"] = "new"
                st.rerun()
        with _d2:
            if st.button("▶ Priya", key="demo_existing", use_container_width=True):
                st.session_state["authenticated"] = True
                st.session_state["login_name"] = "Priya Sharma"
                st.session_state["user_type"] = "existing"
                st.rerun()
        with _d3:
            if st.button("▶ Admin", key="demo_admin", use_container_width=True):
                st.session_state["authenticated"] = True
                st.session_state["login_name"] = "Admin"
                st.session_state["user_type"] = "admin"
                st.session_state["admin_logged_in"] = True
                st.rerun()

        st.markdown('<div class="or-sep">or sign in manually</div>', unsafe_allow_html=True)

        # Role selector
        user_type = st.radio(
            "I am a …",
            options=["🆕 New Learner", "🔄 Returning Learner", "🔐 Admin"],
            horizontal=True,
            key="login_role",
            label_visibility="collapsed",
        )
        _is_admin_login = user_type.startswith("🔐")

        # Role description
        if _is_admin_login:
            _role_desc = "Administrator — inspect agent traces and audit student runs."
        elif user_type.startswith("🔄"):
            _role_desc = "Welcome back! Track progress and pick up where you left off."
        else:
            _role_desc = "First time? We'll profile your skills and build a custom study plan."
        st.markdown(f'<div class="role-desc">{_role_desc}</div>', unsafe_allow_html=True)

        # Manual login form
        with st.form("login_form"):
            if _is_admin_login:
                user_name = st.text_input("Username", placeholder="admin", label_visibility="collapsed")
                credential = st.text_input("Password", type="password", placeholder="Enter password", label_visibility="collapsed")
            else:
                user_name = st.text_input("Your name", placeholder="👤  Enter your name", label_visibility="collapsed")
                credential = st.text_input("PIN", type="password", placeholder="🔑  PIN: 1234", label_visibility="collapsed")

            login_btn = st.form_submit_button("Sign In →", type="primary", use_container_width=True)

        if _is_admin_login:
            st.markdown(
                "<p style='text-align:center;color:rgba(255,255,255,0.28);font-size:0.68rem;'>"
                "Credentials: <code style='color:#50E6FF'>admin</code> / "
                "<code style='color:#50E6FF'>agents2026</code></p>",
                unsafe_allow_html=True,
            )

        st.markdown(
            "<p style='text-align:center;color:rgba(255,255,255,0.16);font-size:0.62rem;margin-top:12px;'>"
            "Built with Azure AI Foundry · Streamlit · Azure OpenAI</p>",
            unsafe_allow_html=True,
        )

        if login_btn:
            if not user_name.strip():
                st.error("Please enter your name." if not _is_admin_login else "Please enter the username.")
            elif _is_admin_login:
                if user_name.strip() == ADMIN_USER and credential == ADMIN_PASS:
                    st.session_state["authenticated"] = True
                    st.session_state["login_name"] = "Admin"
                    st.session_state["user_type"] = "admin"
                    st.session_state["admin_logged_in"] = True
                    st.rerun()
                else:
                    st.error("Invalid admin credentials.")
            elif credential != APP_PIN:
                st.error("Incorrect PIN. Please try again.")
            else:
                st.session_state["authenticated"] = True
                st.session_state["login_name"] = user_name.strip()
                st.session_state["user_type"] = "existing" if user_type.startswith("🔄") else "new"
                st.rerun()

    st.stop()

# ─── Colour palette (matches architecture diagram) ───────────────────────────
PURPLE      = "#5C2D91"
PURPLE_LITE = "#F5F0FF"
PINK        = "#B4009E"
PINK_LITE   = "#FDE7F3"
GREEN       = "#107C10"
GREEN_LITE  = "#E9F7EE"
GOLD        = "#8A6D00"
GOLD_LITE   = "#FFF4CE"
BLUE        = "#0F6CBD"
BLUE_LITE   = "#EEF6FF"

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

# ─── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
  /* Header bar */
  .hero {{
    background: linear-gradient(135deg, {PURPLE} 0%, {PINK} 100%);
    color: white;
    padding: 1.4rem 2rem;
    border-radius: 12px;
    margin-bottom: 1.5rem;
  }}
  .hero h1 {{ margin: 0; font-size: 1.9rem; }}
  .hero p  {{ margin: 0.3rem 0 0; opacity: 0.85; font-size: 1rem; }}

  /* Section cards */
  .card {{
    background: white;
    border-radius: 10px;
    padding: 1.2rem 1.5rem;
    border: 1px solid #e0e0e0;
    margin-bottom: 1rem;
    box-shadow: 0 2px 6px rgba(0,0,0,0.06);
  }}
  .card-purple {{ border-left: 5px solid {PURPLE}; }}
  .card-green  {{ border-left: 5px solid {GREEN};  }}
  .card-gold   {{ border-left: 5px solid {GOLD};   }}
  .card-pink   {{ border-left: 5px solid {PINK};   }}
  .card-blue   {{ border-left: 5px solid {BLUE};   }}

  /* Domain badge pills */
  .badge-unknown  {{ background:{LEVEL_COLOUR["unknown"]};  color:white; padding:2px 10px; border-radius:12px; font-size:0.78rem; font-weight:600; }}
  .badge-weak     {{ background:{LEVEL_COLOUR["weak"]};     color:white; padding:2px 10px; border-radius:12px; font-size:0.78rem; font-weight:600; }}
  .badge-moderate {{ background:{LEVEL_COLOUR["moderate"]}; color:white; padding:2px 10px; border-radius:12px; font-size:0.78rem; font-weight:600; }}
  .badge-strong   {{ background:{LEVEL_COLOUR["strong"]};   color:white; padding:2px 10px; border-radius:12px; font-size:0.78rem; font-weight:600; }}

  /* Ready / not-ready decision box */
  .decision-ready     {{ background:{GREEN_LITE};  border:2px solid {GREEN};  border-radius:10px; padding:1rem 1.5rem; }}
  .decision-not-ready {{ background:{PINK_LITE};   border:2px solid {PINK};   border-radius:10px; padding:1rem 1.5rem; }}

  /* Progress bar override */
  div[data-testid="stProgress"] > div {{ background-color: {PURPLE}; }}

  /* Sidebar */
  section[data-testid="stSidebar"] {{ background: {PURPLE_LITE}; }}

  /* Tab underline */
  .stTabs [data-baseweb="tab-highlight"] {{ background-color: {PURPLE} !important; }}
  .stTabs [aria-selected="true"] {{ color: {PURPLE} !important; font-weight: 700 !important; }}
</style>
""", unsafe_allow_html=True)


# ─── Sidebar – mode + optional credentials ───────────────────────────────────
with st.sidebar:
    st.image("https://img-prod-cms-rt-microsoft-com.akamaized.net/cms/api/am/imageFileData/RE1Mu3b?ver=5c31", width=140)

    # Greeting & sign-out
    _login_name = st.session_state.get("login_name", "Learner")
    _user_type_label = "Returning" if st.session_state.get("user_type") == "existing" else "New"
    st.markdown(f"👋 **{_login_name}** ({_user_type_label})")
    if st.button("🚪 Sign Out", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()
    st.markdown("---")

    st.markdown("### ⚙️ Configuration")

    mode = st.radio(
        "Profiling mode",
        options=["🧪 Mock (no credentials)", "☁️ Live Azure OpenAI"],
        index=0,
        help="Mock mode uses rule-based inference. Live mode calls Azure OpenAI.",
    )
    use_live = mode.startswith("☁️")

    if use_live:
        st.markdown("---")
        az_endpoint   = os.getenv("AZURE_OPENAI_ENDPOINT",   "")
        az_key        = os.getenv("AZURE_OPENAI_API_KEY",    "")
        az_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
        if az_endpoint and az_key:
            st.success("✅ Azure OpenAI credentials loaded from environment.")
            st.caption(f"Deployment: **{az_deployment}**")
        else:
            st.warning(
                "⚠️ No Azure credentials found.\n\n"
                "Add `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY` "
                "to your `.env` file and restart the app."
            )
            use_live = False
    else:
        az_endpoint = az_key = az_deployment = ""

    st.markdown("---")
    st.markdown("### � Your Journey")
    journey_mode = st.radio(
        "Where are you in your prep?",
        options=["🆕 First Visit — create my plan", "🔄 Returning — update my progress"],
        index=0 if "profile" not in st.session_state else 1,
        help="Returning learners can log study hours, self-rate domains, and get a readiness assessment.",
    )
    is_returning = journey_mode.startswith("🔄")

    st.markdown("---")
    st.markdown("### 📧 Weekly Report Email")
    sidebar_email = st.text_input(
        "Your email address",
        value=st.session_state.get("user_email", ""),
        placeholder="you@example.com",
        help="We'll use this to send your weekly study progress summary.",
    )
    if sidebar_email:
        st.session_state["user_email"] = sidebar_email
        st.caption("✅ Email saved — use the 📈 My Progress tab to send a report.")

    st.markdown("---")
    st.markdown("### �📋 Pre-fill scenario")
    scenario = st.selectbox(
        "Load a sample student",
        ["— custom (blank form) —", "Priya – Fresh Graduate", "Marcus – Azure Architect", "Sarah – Data Scientist"],
    )

    st.markdown("---")
    st.markdown(
        "<small>Part of the **Agents League** competition submission.<br/>"
        "Block 1: Learner Intake & Profiling</small>",
        unsafe_allow_html=True,
    )


# ─── Pre-fill values per scenario ────────────────────────────────────────────
SCENARIOS = {
    "Priya – Fresh Graduate": {
        "name":       "Priya Sharma",
        "background": "BSc Computer Science graduate (2025). Strong Python basics but no prior Azure or AI services experience.",
        "certs":      "",
        "hpw":        10.0,
        "weeks":      10,
        "concerns":   "Azure OpenAI, Bot Service, Responsible AI",
        "style":      "Structured, linear learning with hands-on labs. I need motivational reminders to stay on track.",
        "goal":       "Pass AI-102 to strengthen job applications for AI Engineer roles.",
    },
    "Marcus – Azure Architect": {
        "name":       "Marcus Chen",
        "background": "5 years as Cloud Solutions Architect. Deep Azure infrastructure expertise. Holds AZ-104 and AZ-305. No AI/ML certifications yet.",
        "certs":      "AZ-104, AZ-305",
        "hpw":        15.0,
        "weeks":      3,
        "concerns":   "Azure OpenAI, Generative AI patterns, Responsible AI governance",
        "style":      "Skip things I already know. Give me quick reference cards and deep-dive labs for AI-specific topics.",
        "goal":       "Add AI-102 before Q1 performance review. Fast-track focused prep.",
    },
    "Sarah – Data Scientist": {
        "name":       "Sarah Al-Rashid",
        "background": "Senior Data Scientist with 7 years of scikit-learn, PyTorch, and Jupyter experience. Uses Azure ML workspace but has never touched Cognitive Services.",
        "certs":      "DP-100",
        "hpw":        8.0,
        "weeks":      5,
        "concerns":   "Bot Service, Document Intelligence, Responsible AI",
        "style":      "Hands-on API-first. Show me SDK code before portal screenshots. Map new Azure concepts to things I know from ML.",
        "goal":       "Formalise and certify Azure AI knowledge to lead company's certification compliance programme.",
    },
}

prefill = SCENARIOS.get(scenario, {})


# ─── Hero banner ─────────────────────────────────────────────────────────────
if is_returning and "profile" in st.session_state:
    _rp: LearnerProfile = st.session_state["profile"]
    st.markdown(f"""
    <div class="hero">
      <h1>👋 Welcome Back, {_rp.student_name}!</h1>
      <p>Returning Learner &nbsp;|&nbsp; {_rp.exam_target} Prep
         &nbsp;|&nbsp; Head to the <b>📈 My Progress</b> tab to log today's study session.</p>
    </div>
    """, unsafe_allow_html=True)
elif is_returning and "profile" not in st.session_state:
    st.markdown("""
    <div class="hero">
      <h1>🔄 Returning Learner</h1>
      <p>No saved profile found. Please complete the intake form below first to create your plan.</p>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="hero">
      <h1>🎓 Microsoft Certification Prep — Learner Profiler</h1>
      <p>Block 1: Learner Intake &amp; Profiling &nbsp;|&nbsp; Microsoft Agents League Multi-Agent System</p>
    </div>
    """, unsafe_allow_html=True)


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
        preferred_style = st.text_area(
            "How do you prefer to learn?",
            value=prefill.get("style", ""),
            placeholder="e.g. hands-on labs first, or structured reading, or quick reference cards",
            height=80,
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

            from cert_prep.intake_agent import LearnerProfilingAgent
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
    _is_existing = st.session_state.get("user_type") == "existing"

    if _is_existing:
        tab_domains, tab_plan, tab_path, tab_recs, tab_progress, tab_quiz, tab_json = st.tabs([
            "🗺️ Domain Map",
            "📅 Study Setup",
            "📚 Learning Path",
            "💡 Recommendations",
            "📈 My Progress",
            "🧪 Knowledge Check",
            "📄 Raw JSON",
        ])
    else:
        tab_domains, tab_plan, tab_path = st.tabs([
            "🗺️ Domain Map",
            "📅 Study Setup",
            "📚 Learning Path",
        ])
        tab_recs = tab_progress = tab_quiz = tab_json = None

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
            line=dict(color=PURPLE, width=2),
            fillcolor="rgba(92,45,145,0.18)",
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

        _level_summary = " · ".join(
            f"<span style='color:{LEVEL_COLOUR[lv]};font-weight:600;'>"
            f"{cnt} {lv.upper()}</span>"
            for lv, cnt in sorted(_level_counts.items(),
                                   key=lambda x: ["strong","moderate","weak","unknown"].index(x[0])
                                   if x[0] in ["strong","moderate","weak","unknown"] else 9)
        )

        _skip_names  = [dp.domain_name.replace("Implement ","").replace(" Solutions","")
                        for dp in profile.domain_profiles if dp.skip_recommended]
        _risk_names  = [dp.domain_name.replace("Implement ","").replace(" Solutions","")
                        for dp in profile.domain_profiles if dp.domain_id in profile.risk_domains]

        _bar_colour  = GREEN if not _below_thresh else (GOLD if len(_below_thresh) <= 2 else "#d13438")

        st.markdown(
            f"""<div style="background:#f8f8ff;border-left:4px solid {BLUE};
                 border-radius:8px;padding:10px 14px;margin-top:4px;font-size:0.85rem;">
              <b style="font-size:0.9rem;">📌 Bar Chart Insights</b><br/><br/>
              <b>Knowledge level mix:</b> {_level_summary}<br/>
              <b>Domains above 50 % threshold:</b>
                <span style="color:{_bar_colour};font-weight:600;">
                  {len(_above_thresh)} / {len(profile.domain_profiles)}
                </span><br/>
              {"<b>Fast-track / skip candidates:</b> <span style='color:" + GREEN + ";'>" +
                ", ".join(_skip_names) + "</span><br/>"
               if _skip_names else ""}
              {"<b style='color:#d13438;'>⚠ Risk domains (below threshold):</b> " +
                ", ".join(_risk_names) + "<br/>"
               if _risk_names else
               "<b style='color:" + GREEN + ";'>✓ No domains fall below the risk threshold.</b><br/>"}
              <b>Recommendation:</b>
              {"Concentrate initial study blocks on the <b>" +
                ", ".join(dp.domain_name.replace("Implement ","").replace(" Solutions","")
                          for dp in _sorted_dp[:2]) +
                "</b> domains first to close the biggest gaps."
               if _below_thresh else
               "All domains are at or above readiness. Focus remaining time on practice exams and edge-case topics."}
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
        col_l, col_r = st.columns(2)

        with col_l:
            st.markdown("### 📋 Profile Summary")
            st.markdown(f"""
            <div class="card card-purple">
              <b>Learning Style:</b> {profile.learning_style.value.replace('_', ' ').title()}<br/>
              <b>Experience Level:</b> {profile.experience_level.value.replace('_', ' ').title()}<br/>
              <b>Total Study Hours:</b> {profile.total_budget_hours:.0f} h
              ({profile.hours_per_week:.0f} h/wk × {profile.weeks_available} wks)
            </div>
            """, unsafe_allow_html=True)

            if profile.modules_to_skip:
                st.markdown("#### ⏭ Domains safe to skip or fast-track")
                for m in profile.modules_to_skip:
                    st.success(f"✓ {m}")
            else:
                st.info("No domains skipped — full study path required.")

            if profile.risk_domains:
                st.markdown("#### ⚠️ Priority risk domains")
                for did in profile.risk_domains:
                    name = EXAM_DOMAIN_NAMES.get(did, did)
                    st.error(f"⚠ {name}")

        with col_r:
            if profile.analogy_map:
                st.markdown("### 🔁 Skill Analogy Map")
                st.caption("Your existing skills mapped to Azure AI equivalents.")
                for skill, equiv in profile.analogy_map.items():
                    st.markdown(
                        f"""<div style="background:{BLUE_LITE};border-left:4px solid {BLUE};
                             padding:6px 12px;border-radius:6px;margin-bottom:6px;">
                             <b style='color:{BLUE};'>{skill}</b>
                             <span style='color:#555;'> → {equiv}</span></div>""",
                        unsafe_allow_html=True,
                    )

            st.markdown("### 🔔 Engagement Notes")
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
    if tab_recs is not None:
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
            ("🎤 Learner Intake Agent",       "Block 1",   "Collects raw student input",           True),
            ("🧠 Learner Profiling Agent",     "Block 1",   "Infers experience & domain knowledge", True),
            ("📚 Learning Path Curator",       "Block 1.1", "Maps MS Learn modules to domains",     "learning_path" in st.session_state),
            ("📅 Study Plan Agent",            "Block 1.1", "Gantt schedule + prerequisites",       "plan" in st.session_state),
            ("📈 Progress Agent",              "Block 1.2", "Mid-journey readiness scoring",        "progress_assessment" in st.session_state),
            ("🧪 Assessment Agent",            "Block 2",   "Domain knowledge quiz",                "assessment_result" in st.session_state),
            ("🏅 Cert Recommendation Agent",   "Block 3",   "Go/No-Go exam decision",               _cert_rec is not None),
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
    if tab_progress is not None:
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
    if tab_quiz is not None:
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
                    # Clear cert rec so it regenerates
                    st.session_state.pop("cert_recommendation", None)
                    st.rerun()

    # ── Tab 7: Raw JSON ───────────────────────────────────────────────────────
    if tab_json is not None:
      with tab_json:
        col_j1, col_j2 = st.columns(2)
        with col_j1:
            st.markdown("#### Raw Student Input")
            import dataclasses
            st.json(dataclasses.asdict(raw))
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
