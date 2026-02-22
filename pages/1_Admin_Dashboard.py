"""
pages/1_Admin_Dashboard.py – Admin-only agent interaction inspector.

Shows how each agent in the pipeline contributed to the final
LearnerProfile output. Protected by a session-scoped mock login gate.

Credentials  →  username: admin  |  password: agents2026
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

# ─── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Admin Dashboard – AI-102 Agents",
    page_icon="🔐",
    layout="wide",
)

# ─── Theme constants (match main app palette) ─────────────────────────────────
BG        = "#0e1117"
CARD_BG   = "#1e2a3a"
BLUE      = "#4a9eff"
PURPLE    = "#a78bfa"
GREEN     = "#34d399"
ORANGE    = "#fb923c"
RED       = "#f87171"
YELLOW    = "#fbbf24"
GREY      = "#8899aa"

AGENT_COLORS = {
    "safety":     RED,
    "intake":     BLUE,
    "profiling":  PURPLE,
    "scorer":     GREEN,
    "gate":       ORANGE,
    "analogy":    YELLOW,
    "engagement": "#06b6d4",
}

# ─── Minimal page CSS ─────────────────────────────────────────────────────────
st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background: #0e1117; }
  [data-testid="stSidebar"]          { background: #141c27; }
  h1, h2, h3, h4                     { color: #e8edf3 !important; }
  .stExpander details                 { background: #1e2a3a; border-radius: 8px; border: 1px solid #2a3a50 !important; }
  .stExpander summary                 { color: #e8edf3 !important; }
  div[data-testid="stTable"]          { background: #1e2a3a; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _card(label: str, value: str, color: str = BLUE, wide: bool = False) -> str:
    w = "100%" if wide else "auto"
    return f"""
    <div style="background:{CARD_BG};border-left:4px solid {color};border-radius:8px;
                padding:10px 16px;display:inline-block;min-width:160px;width:{w};
                margin-bottom:8px;box-sizing:border-box;">
      <div style="color:{GREY};font-size:0.7rem;font-weight:600;text-transform:uppercase;
                  letter-spacing:.06em;margin-bottom:3px;">{label}</div>
      <div style="color:#e8edf3;font-size:1rem;font-weight:700;">{value}</div>
    </div>"""


def _section_header(title: str, icon: str = "") -> None:
    st.markdown(
        f"""<h3 style="color:#e8edf3;border-bottom:1px solid #2a3a50;
                        padding-bottom:6px;margin-top:28px;">{icon} {title}</h3>""",
        unsafe_allow_html=True,
    )


def _badge(text: str, color: str) -> str:
    return (
        f'<span style="background:{color}22;color:{color};border:1px solid {color}55;'
        f'border-radius:12px;padding:1px 10px;font-size:0.78rem;font-weight:600;">{text}</span>'
    )


def _hex_rgba(hex_color: str, alpha: float = 1.0) -> str:
    """Convert a #RRGGBB hex color to rgba() string Plotly can use."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# ─── Login gate ───────────────────────────────────────────────────────────────

MOCK_USER = "admin"
MOCK_PASS = "agents2026"

if "admin_logged_in" not in st.session_state:
    st.session_state["admin_logged_in"] = False


def _show_login() -> None:
    st.markdown("""
    <div style="max-width:400px;margin:80px auto 0;">
      <div style="text-align:center;margin-bottom:32px;">
        <span style="font-size:3rem;">🔐</span>
        <h2 style="color:#e8edf3;margin-top:8px;">Admin Access</h2>
        <p style="color:#8899aa;font-size:0.9rem;">
          This dashboard is restricted to administrators.<br/>
          Enter your credentials to continue.
        </p>
      </div>
    </div>
    """, unsafe_allow_html=True)

    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        with st.form("admin_login_form", clear_on_submit=False):
            username = st.text_input("Username", placeholder="admin")
            password = st.text_input("Password", type="password", placeholder="••••••••••")
            submitted = st.form_submit_button("🔓  Sign in", use_container_width=True)

        if submitted:
            if username == MOCK_USER and password == MOCK_PASS:
                st.session_state["admin_logged_in"] = True
                st.rerun()
            else:
                st.error("Invalid credentials. Please try again.")

        st.markdown(
            "<p style='text-align:center;color:#8899aa;font-size:0.78rem;"
            "margin-top:16px;'>Hint: username&nbsp;=&nbsp;<code>admin</code> &nbsp;|&nbsp; "
            "password&nbsp;=&nbsp;<code>agents2026</code></p>",
            unsafe_allow_html=True,
        )


if not st.session_state["admin_logged_in"]:
    _show_login()
    st.stop()


# ─── Authenticated: sidebar logout ────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔐 Admin Panel")
    st.markdown(f"Signed in as **{MOCK_USER}**")
    if st.button("🚪 Sign out", use_container_width=True):
        st.session_state["admin_logged_in"] = False
        st.rerun()
    st.markdown("---")
    st.caption("Only admins can see this page.\nStudents see the main Profiler UI.")


# ─── Page header ──────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">
  <span style="font-size:2rem;">🤖</span>
  <div>
    <h1 style="color:#e8edf3;margin:0;font-size:1.9rem;">Agent Interaction Dashboard</h1>
    <p style="color:#8899aa;margin:0;font-size:0.9rem;">
      Real-time audit of how each AI agent contributed to the learner profile output.
    </p>
  </div>
</div>
""", unsafe_allow_html=True)
st.markdown("---")


# ─── Check for trace data ─────────────────────────────────────────────────────
from cert_prep.agent_trace import RunTrace, AgentStep, build_mock_trace

trace: RunTrace | None = st.session_state.get("trace", None)
profile                = st.session_state.get("profile", None)
raw                    = st.session_state.get("raw", None)

if trace is None:
    st.info(
        "🔍 **No profiling run detected yet.**\n\n"
        "Go to the main **AI-102 Cert Prep** page, fill in the intake form, "
        "and click **Generate Profile**. Then return here to inspect the "
        "full agent interaction log.",
        icon="ℹ️",
    )

    # Show a preview with synthetic demo data
    st.markdown("---")
    st.markdown("### 👇 Preview – Demo Run (synthetic data)")
    st.caption("This is what the dashboard looks like after a real profiling run.")

    # Build a small demo raw + profile for preview
    from cert_prep.models import RawStudentInput
    _demo_raw = RawStudentInput(
        student_name    = "Demo Student",
        exam_target     = "AI-102 – Azure AI Engineer Associate",
        background_text = "Data scientist with 3 years of Python and scikit-learn",
        existing_certs  = ["DP-100"],
        hours_per_week  = 10,
        weeks_available = 8,
        concern_topics  = ["generative AI", "responsible AI"],
        preferred_style = "hands-on labs",
        goal_text       = "Pass AI-102 exam",
    )
    from cert_prep.mock_profiler import run_mock_profiling
    _demo_profile = run_mock_profiling(_demo_raw)
    trace = build_mock_trace(_demo_raw, _demo_profile)
    profile = _demo_profile
    raw = _demo_raw
    _demo_mode = True
else:
    _demo_mode = False


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 1 – Run Summary Cards
# ═════════════════════════════════════════════════════════════════════════════
_section_header("Run Summary", "📋")

run_cols = st.columns(6)
summary_items = [
    ("Run ID",      trace.run_id,                                  BLUE),
    ("Student",     trace.student_name,                            PURPLE),
    ("Exam Target", trace.exam_target.split("–")[0].strip(),       GREEN),
    ("Timestamp",   trace.timestamp,                               GREY),
    ("Mode",        trace.mode,                                    ORANGE),
    ("Total Time",  f"{trace.total_ms:.0f} ms",                    YELLOW),
]
for col, (lbl, val, clr) in zip(run_cols, summary_items):
    with col:
        st.markdown(_card(lbl, val, clr, wide=True), unsafe_allow_html=True)

if _demo_mode:
    st.warning("⚠️ Showing **demo/synthetic data** — generate a real profile to see live run details.", icon="⚠️")


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 2 – Architecture-style Pipeline Diagram
# ═════════════════════════════════════════════════════════════════════════════
_section_header("Agent Pipeline Flow", "🔀")

st.caption(
    "Architecture-diagram view inspired by the **r4 design**. "
    "Solid-filled blocks = **active in this run** (with ✓ timing). "
    "Outlined blocks = exist in full system, not invoked this run. "
    "🟡 badges = execution step order."
)


def _build_pipeline_fig(trace_obj):
    """
    Draws an architecture block diagram that mirrors the r4 drawio layout.
    Color palette matches the official diagram exactly.
    Active agents are solid-filled; inactive blocks are outline-only.
    """
    sid = {s.agent_id: s for s in trace_obj.steps}

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[0, 100], y=[-2, 70], mode="markers",
        marker=dict(opacity=0, size=1), showlegend=False, hoverinfo="skip",
    ))

    shapes, anns = [], []

    # ── Helpers ────────────────────────────────────────────────────────────
    def _r(x0, y0, x1, y1, fill, border, bw=1.5, op=1.0, above=False):
        shapes.append(dict(
            type="rect", x0=x0, y0=y0, x1=x1, y1=y1,
            fillcolor=fill, opacity=op,
            line=dict(color=border, width=bw),
            layer="above" if above else "below",
        ))

    def _a(x, y, txt, color="#ffffff", sz=10, bold=False,
           xa="center", ya="middle", bg=None, bdc=None):
        d = dict(x=x, y=y, text=f"<b>{txt}</b>" if bold else txt,
                 showarrow=False, font=dict(color=color, size=sz, family="Segoe UI, Arial"),
                 xanchor=xa, yanchor=ya, xref="x", yref="y")
        if bg:
            d["bgcolor"] = bg
            d["bordercolor"] = bdc or bg
            d["borderwidth"] = 1
            d["borderpad"] = 3
        anns.append(d)

    def _arr(x0, y0, x1, y1, clr="#aaaaaa", head=2, w=1.5, txt="", tsz=8):
        d = dict(x=x1, y=y1, ax=x0, ay=y0, xref="x", yref="y", axref="x", ayref="y",
                 showarrow=True, arrowhead=head, arrowsize=1.2,
                 arrowwidth=w, arrowcolor=clr)
        if txt:
            d["text"] = txt
            d["font"] = dict(color="#e8edf3", size=tsz)
        anns.append(d)

    def _block(aid, x0, y0, x1, y1, title, sub="",
               bf="#EEF6FF", bb="#0F6CBD", bt="#0F3D7A"):
        step   = sid.get(aid)
        active = step is not None
        fill   = bb    if active else bf
        bw     = 2.5   if active else 1.5
        tc     = "#ffffff" if active else bt
        sc     = "#ddeeff" if active else "#888888"

        shapes.append(dict(
            type="rect", x0=x0, y0=y0, x1=x1, y1=y1,
            fillcolor=fill, line=dict(color=bb, width=bw), layer="above",
        ))
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if sub:
            _a(cx, cy + 2.0, title, tc, sz=10, bold=True)
            _a(cx, cy - 0.5, sub,   sc, sz=8)
        else:
            _a(cx, cy, title, tc, sz=10, bold=True)

        if step:
            _a(x1 - 0.4, y0 + 1.0, f"✓ {step.duration_ms:.0f} ms",
               "#fbbf24", sz=8, xa="right", ya="bottom")

    # ── SAFETY BAR (top, cross-cutting) ────────────────────────────────────
    ss  = sid.get("safety")
    _r(0, 64, 100, 69, "#B4009E" if ss else "#FDE7F3", "#B4009E", bw=2)
    _a(50, 66.5,
       "🛡️  Policy & Safety Guardrails  ·  cross-cutting  ·  PII filter  ·  anti-cheating  ·  human escalation",
       "#ffffff" if ss else "#7a0068", sz=10, bold=True)
    if ss:
        _a(97, 66.5, f"✓ {ss.duration_ms:.0f} ms", "#fbbf24", sz=9, xa="right")

    # ── SECTION 1: INTAKE & PREPARATION (light-yellow container) ───────────
    _r(0, 9, 100, 63, "#FFFDE7", "#8A6D00", bw=1.5, op=0.45)
    _a(2, 62.3, "1.  Intake & Preparation", "#5a4200", sz=11, bold=True, xa="left")

    # Orchestrator sub-container (gold)
    _r(37, 11, 99, 61, "#FFF4CE", "#8A6D00", bw=1, op=0.35)
    _a(68, 60.3, "Preparation Orchestrator  (Central Brain)", "#5a4200", sz=10, bold=True)

    # Reasoning trace log strip (inside orchestrator, bottom)
    _r(42, 9.5, 96, 11.5, "#FFF9C4", "#8A6D00", bw=1, op=0.7)
    _a(69, 10.5, "Reasoning Trace Log  (explainability)", "#7a5d00", sz=9)

    # Student Input  ── always shown as "origin" (solid blue)
    _r(1, 29, 16, 57, "#0F6CBD", "#0F6CBD", bw=2.5, above=True)
    _a(8.5, 46,   "Student Input", "#ffffff",  sz=10, bold=True)
    _a(8.5, 41,   "Topics · Exam", "#d0e8ff",  sz=8)
    _a(8.5, 37.5, "Time · Prefs",  "#d0e8ff",  sz=8)

    # Learner Intake & Profiling
    _block("intake", 19, 29, 36, 57,
           "Learner Intake", "& Profiling",
           "#F5F0FF", "#5C2D91", "#3d1077")
    if sid.get("profiling"):
        p = sid["profiling"]
        _a(27.5, 32.5, f"⚙ LLM  {p.duration_ms:.0f} ms", "#c4a8ff", sz=8)

    # 1.1 – Learning Path Planner  (analogy mapper maps here)
    _block("analogy", 39, 29, 65, 57,
           "1.1  Learning Path Planner",
           "Syllabus mapper · resource curator",
           "#F5F0FF", "#5C2D91", "#3d1077")

    # 1.2 – Study Plan & Engagement Generator
    _block("engagement", 67, 29, 97, 57,
           "1.2  Study Plan &",
           "Engagement Generator",
           "#F5F0FF", "#5C2D91", "#3d1077")

    # Domain Confidence Scorer  (inside orchestrator, below main row)
    sc2  = sid.get("scorer")
    sf   = "#27ae60" if sc2 else "#d5f5e3"
    stc  = "#ffffff" if sc2 else "#0a5c0a"
    _r(39, 13, 65, 27, sf, "#107C10", bw=1.5, op=0.95, above=True)
    _a(52, 21, "Domain Confidence Scorer", stc, sz=9, bold=True)
    _a(52, 17, "Confidence thresholds per domain", stc if sc2 else "#4a8a4a", sz=8)
    if sc2:
        _a(52, 13.5, f"✓ {sc2.duration_ms:.0f} ms", "#fbbf24", sz=8)

    # Preparation Output Artifact  (bottom-left of Section 1)
    _r(1, 10, 35, 27, "#EEF6FF", "#0F6CBD", bw=1.8, op=0.95, above=True)
    _a(18, 21,   "Preparation Output Artifact", "#0F3D7A", sz=9, bold=True)
    _a(18, 16,   "Study Plan + Resources", "#3366aa", sz=8)
    _a(18, 12.5, "+ Milestones",            "#3366aa", sz=8)

    # Readiness Gate diamond  (sits right of scorer, bridging vertical gap)
    gs   = sid.get("gate")
    gf   = "#107C10" if gs else "#E9F7EE"
    gtc  = "#ffffff" if gs else "#0a4d0a"
    gx, gy, gr = 68, 18.5, 6.2
    shapes.append(dict(
        type="path",
        path=f"M {gx} {gy+gr} L {gx+gr*1.55} {gy} L {gx} {gy-gr} L {gx-gr*1.55} {gy} Z",
        fillcolor=gf, line=dict(color="#107C10", width=2.2 if gs else 1.5),
        layer="above",
    ))
    _a(gx, gy + 1.5, "Ready for",       gtc, sz=9, bold=True)
    _a(gx, gy - 1.5, "Assessment?",     gtc, sz=9, bold=True)
    if gs:
        _a(gx, gy - 5, f"✓ {gs.duration_ms:.0f} ms", "#fbbf24", sz=8)

    # ── SECTION 2: ASSESSMENT + VERIFICATION ───────────────────────────────
    _r(26, 0.3, 100, 8, "#F3F0FF", "#5C2D91", bw=1.5, op=0.5)
    _a(63, 7.5, "2.  Assessment + Verification", "#3d1a6e", sz=10, bold=True)

    _r(27.5, 0.8, 47, 6.5, "#F5F0FF", "#5C2D91", bw=1.5, op=0.95, above=True)
    _a(37.25, 4.0, "2.1  Assessment Builder", "#3d1077", sz=9, bold=True)
    _a(37.25, 2.0, "(exam-style questions)",   "#888888", sz=8)

    _r(49, 0.8, 69, 6.5, "#FDE7F3", "#B4009E", bw=1.5, op=0.95, above=True)
    _a(59, 4.0, "2.2  Tiered Verifier",  "#7a0068", sz=9, bold=True)
    _a(59, 2.0, "+ Repair Loop",         "#7a0068", sz=8)

    _r(71, 0.8, 90, 6.5, "#E9F7EE", "#107C10", bw=1.5, op=0.95, above=True)
    _a(80.5, 4.0, "2.3  Scoring Engine", "#0a4d0a", sz=9, bold=True)
    _a(80.5, 2.0, "(deterministic)",     "#888888", sz=8)

    # ── SECTION 3: DECISION + ADAPTATION ───────────────────────────────────
    _r(0, 0.3, 24.5, 8, "#E9F7EE", "#107C10", bw=1.5, op=0.5)
    _a(12.25, 7.5, "3.  Decision + Adaptation", "#0a4d0a", sz=10, bold=True)

    _r(0.5, 0.8, 11.5, 6.5, "#EEF6FF", "#0F6CBD", bw=1.5, op=0.95, above=True)
    _a(6.0, 4.0, "3.2  Cert &",    "#0F3D7A", sz=9, bold=True)
    _a(6.0, 2.0, "Exam Planner",  "#0F3D7A", sz=8)

    _r(13, 0.8, 24, 6.5, "#E9F7EE", "#107C10", bw=1.5, op=0.95, above=True)
    _a(18.5, 4.0, "3.1  Gap Analyzer",   "#0a4d0a", sz=9, bold=True)
    _a(18.5, 2.0, "& Decision Policy",   "#0a4d0a", sz=8)

    # ── OBSERVABILITY BAR (bottom) ─────────────────────────────────────────
    _r(0, -1.4, 100, 0.2, "#EEF6FF", "#0F6CBD", bw=1, op=0.7)
    _a(50, -0.65,
       "📊  Evaluation Harness & Observability  ·  KPIs  ·  latency  ·"
       "  verifier catch-rate  ·  gap delta  ·  readiness accuracy",
       "#0F6CBD", sz=8)

    # ── ARROWS ─────────────────────────────────────────────────────────────
    _arr(16, 43,  19, 43, "#aaaaaa")            # Student Input → Intake
    _arr(36, 43,  39, 43, "#5C2D91")            # Intake → Orchestrator
    _arr(65, 43,  67, 43, "#5C2D91")            # 1.1 → 1.2
    _arr(27.5, 29, 20, 27, "#0F6CBD")           # Intake → Output Artifact
    _arr(35, 18.5, 57.7, 18.5, "#107C10")       # Output → Gate
    _arr(62, 12.5, 37.25, 8, "#107C10",         # Gate Yes → Section 2
         txt="Yes →", tsz=8)
    _arr(74, 18.5, 98, 18.5, "#e67e22",         # Gate No → right edge
         txt="No → Remedi-\nate & Replan", tsz=8)
    _arr(18, 10, 18.5, 8, "#0F6CBD")            # Output → Section 3

    # ── STEP ORDER BADGES (gold circle numbers) ────────────────────────────
    badge_pos = {
        "safety":     (50,   66.5),
        "intake":     (27.5, 57.8),
        "profiling":  (34.5, 34.0),
        "scorer":     (63.5, 27.5),
        "gate":       (77.5, 24.5),
        "analogy":    (52.0, 57.8),
        "engagement": (82.0, 57.8),
    }
    for i, step in enumerate(trace_obj.steps):
        if step.agent_id in badge_pos:
            bx, by = badge_pos[step.agent_id]
            _a(bx, by, str(i + 1), "#0e1117", sz=9, bold=True,
               bg="#fbbf24", bdc="#f59e0b")

    fig.update_layout(
        shapes=shapes, annotations=anns,
        paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
        height=540,
        margin=dict(l=4, r=4, t=8, b=4),
        xaxis=dict(range=[0, 100], visible=False, fixedrange=True),
        yaxis=dict(range=[-2, 70],  visible=False, fixedrange=True),
        dragmode=False,
    )
    return fig


st.plotly_chart(_build_pipeline_fig(trace), use_container_width=True)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 3 – Agent Execution Timeline (Gantt)
# ═════════════════════════════════════════════════════════════════════════════
_section_header("Agent Execution Timeline", "⏱️")
st.caption("Horizontal bars show each agent\'s processing window (relative ms from run start).")

import pandas as pd

gantt_rows = []
for step in trace.steps:
    gantt_rows.append({
        "Agent":    f"{step.icon} {step.agent_name.split('(')[0].strip()}",
        "Start":    step.start_ms,
        "Finish":   step.start_ms + step.duration_ms,
        "Duration": step.duration_ms,
        "Status":   step.status,
        "Color":    AGENT_COLORS.get(step.agent_id, BLUE),
    })

gantt_df = pd.DataFrame(gantt_rows)

gantt_fig = go.Figure()
for _, row in gantt_df.iterrows():
    gantt_fig.add_trace(go.Bar(
        name        = row["Agent"],
        x           = [row["Duration"]],
        y           = [row["Agent"]],
        base        = row["Start"],
        orientation = "h",
        marker_color= row["Color"],
        text        = f'{row["Duration"]:.0f} ms',
        textposition= "auto",
        showlegend  = False,
        hovertemplate = (
            f"<b>{row['Agent']}</b><br>"
            f"Start: {row['Start']:.0f} ms<br>"
            f"Duration: {row['Duration']:.0f} ms<br>"
            f"Status: {row['Status']}<extra></extra>"
        ),
    ))

gantt_fig.update_layout(
    barmode      = "stack",
    paper_bgcolor= CARD_BG,
    plot_bgcolor = CARD_BG,
    font         = dict(color="#e8edf3", size=11),
    height       = max(220, len(trace.steps) * 52),
    margin       = dict(l=10, r=20, t=10, b=40),
    xaxis = dict(
        title      = "Time (ms from run start)",
        color      = GREY,
        gridcolor  = "#2a3a50",
        zeroline   = False,
    ),
    yaxis = dict(
        color      = "#e8edf3",
        gridcolor  = "#2a3a50",
        autorange  = "reversed",
    ),
)
st.plotly_chart(gantt_fig, use_container_width=True)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 4 – Per-Agent I/O Cards
# ═════════════════════════════════════════════════════════════════════════════
_section_header("Per-Agent Interaction Log", "🗂️")
st.caption("Expand each card to inspect inputs, outputs, decisions, and any warnings.")

for step in trace.steps:
    clr = AGENT_COLORS.get(step.agent_id, BLUE)
    status_badge = _badge(step.status, GREEN if step.status == "success" else ORANGE)
    dur_badge    = _badge(f"{step.duration_ms:.0f} ms", GREY)

    expander_label = (
        f"{step.icon}  {step.agent_name}  —  {step.duration_ms:.0f} ms"
    )
    with st.expander(expander_label, expanded=False):

        st.markdown(
            f"""<div style="display:flex;gap:8px;align-items:center;margin-bottom:12px;">
              {status_badge} {dur_badge}
              <span style="color:{GREY};font-size:0.78rem;">agent_id: <code>{step.agent_id}</code></span>
            </div>""",
            unsafe_allow_html=True,
        )

        io_col, dec_col = st.columns([3, 2])

        with io_col:
            st.markdown(
                f"""
                <div style="background:#0e1117;border-left:3px solid {clr};
                            border-radius:6px;padding:12px 14px;margin-bottom:10px;">
                  <div style="color:{GREY};font-size:0.72rem;font-weight:600;
                              text-transform:uppercase;letter-spacing:.06em;
                              margin-bottom:4px;">📨 Input</div>
                  <div style="color:#c9d5e0;font-size:0.87rem;
                              line-height:1.5;">{step.input_summary}</div>
                </div>
                <div style="background:#0e1117;border-left:3px solid {GREEN};
                            border-radius:6px;padding:12px 14px;">
                  <div style="color:{GREY};font-size:0.72rem;font-weight:600;
                              text-transform:uppercase;letter-spacing:.06em;
                              margin-bottom:4px;">📤 Output</div>
                  <div style="color:#c9d5e0;font-size:0.87rem;
                              line-height:1.5;">{step.output_summary}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with dec_col:
            if step.decisions:
                st.markdown(
                    f'<div style="color:{GREY};font-size:0.72rem;font-weight:600;'
                    f'text-transform:uppercase;letter-spacing:.06em;'
                    f'margin-bottom:6px;">⚙️ Decisions / Rules Applied</div>',
                    unsafe_allow_html=True,
                )
                for d in step.decisions:
                    st.markdown(
                        f'<div style="color:#c9d5e0;font-size:0.83rem;'
                        f'padding:2px 0 2px 10px;border-left:2px solid {clr}22;">'
                        f'• {d}</div>',
                        unsafe_allow_html=True,
                    )

            if step.warnings:
                st.markdown("<br/>", unsafe_allow_html=True)
                for w in step.warnings:
                    st.warning(w, icon="⚠️")

        # Detail JSON (collapsed sub-expander)
        if step.detail:
            import json as _json
            with st.expander("🔍 Raw detail payload (JSON)", expanded=False):
                st.code(_json.dumps(step.detail, indent=2, default=str), language="json")


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 5 – Domain Decision Audit Trail
# ═════════════════════════════════════════════════════════════════════════════
_section_header("Domain Decision Audit Trail", "📋")
st.caption(
    "Final per-domain outcome: confidence score, knowledge level, "
    "skip recommendation, and risk flag."
)

if profile is not None:
    audit_rows = []
    for dp in profile.domain_profiles:
        audit_rows.append({
            "Domain":        dp.domain_name,
            "Knowledge Level": dp.knowledge_level.value.replace("_", " ").title(),
            "Confidence":    f"{dp.confidence_score:.0%}",
            "Conf (raw)":    dp.confidence_score,
            "Skip?":         "✅ Yes" if dp.skip_recommended else "—",
            "Risk?":         "⚠️ Yes" if dp.domain_id in profile.risk_domains else "—",
            "Notes":         dp.notes[:90] + "…" if len(dp.notes) > 90 else dp.notes,
        })

    audit_df = pd.DataFrame(audit_rows)

    # Colour-code confidence bars via plotly table
    col_table, col_bar = st.columns([3, 2])

    with col_table:
        header_vals = ["Domain", "Level", "Confidence", "Skip?", "Risk?"]
        cell_vals   = [
            audit_df["Domain"].tolist(),
            audit_df["Knowledge Level"].tolist(),
            audit_df["Confidence"].tolist(),
            audit_df["Skip?"].tolist(),
            audit_df["Risk?"].tolist(),
        ]
        conf_colors = [
            GREEN if r >= 0.65 else (ORANGE if r >= 0.40 else RED)
            for r in audit_df["Conf (raw)"].tolist()
        ]
        table_fig = go.Figure(go.Table(
            columnwidth = [180, 130, 100, 60, 60],
            header = dict(
                values     = [f"<b>{h}</b>" for h in header_vals],
                fill_color = "#2a3a50",
                align      = "left",
                font       = dict(color="#e8edf3", size=12),
                height     = 32,
            ),
            cells = dict(
                values     = cell_vals,
                fill_color = [
                    [CARD_BG] * len(audit_df),
                    [CARD_BG] * len(audit_df),
                    conf_colors,
                    [CARD_BG] * len(audit_df),
                    [CARD_BG] * len(audit_df),
                ],
                align      = ["left", "left", "center", "center", "center"],
                font       = dict(color="#e8edf3", size=11),
                height     = 30,
            ),
        ))
        table_fig.update_layout(
            paper_bgcolor = CARD_BG,
            margin        = dict(l=0, r=0, t=0, b=0),
            height        = 280,
        )
        st.plotly_chart(table_fig, use_container_width=True)

    with col_bar:
        bar_fig = go.Figure(go.Bar(
            y    = [dp.domain_name.replace("Implement ", "").replace(" Solutions", "")
                    for dp in profile.domain_profiles],
            x    = [dp.confidence_score for dp in profile.domain_profiles],
            orientation = "h",
            marker_color = conf_colors,
            text  = [f"{dp.confidence_score:.0%}" for dp in profile.domain_profiles],
            textposition = "outside",
        ))
        bar_fig.update_layout(
            paper_bgcolor = CARD_BG,
            plot_bgcolor  = CARD_BG,
            font          = dict(color="#e8edf3", size=11),
            height        = 280,
            margin        = dict(l=0, r=50, t=10, b=20),
            xaxis = dict(
                range      = [0, 1.05],
                gridcolor  = "#2a3a50",
                color      = GREY,
                tickformat = ".0%",
            ),
            yaxis = dict(color="#e8edf3", gridcolor="#2a3a50"),
        )
        bar_fig.add_vline(x=0.50, line_dash="dash", line_color="rgba(255,255,255,0.27)",
                          annotation_text="50% threshold",
                          annotation_font_color=GREY,
                          annotation_position="top right")
        st.plotly_chart(bar_fig, use_container_width=True)


# ═════════════════════════════════════════════════════════════════════════════
# SECTION 6 – Session Student Table (all profiles this session)
# ═════════════════════════════════════════════════════════════════════════════
_section_header("Session History", "📂")
st.caption("All learner profiles generated in this browser session.")

# Append current profile to a running history list
if profile is not None and not _demo_mode:
    history: list = st.session_state.get("admin_history", [])
    # Avoid duplicates by run_id
    existing_ids = {h.get("run_id") for h in history}
    if trace.run_id not in existing_ids:
        history.append({
            "run_id":      trace.run_id,
            "student":     trace.student_name,
            "exam":        trace.exam_target.split("–")[0].strip(),
            "mode":        trace.mode,
            "time":        trace.timestamp,
            "total_ms":    f"{trace.total_ms:.0f} ms",
            "level":       profile.experience_level.value.replace("_", " ").title(),
            "avg_conf":    f"{sum(dp.confidence_score for dp in profile.domain_profiles)/len(profile.domain_profiles):.0%}",
            "risk_count":  len(profile.risk_domains),
        })
        st.session_state["admin_history"] = history
    history_df = pd.DataFrame(history)
else:
    # Demo mode fallback
    history_df = pd.DataFrame([{
        "run_id": trace.run_id, "student": trace.student_name,
        "exam": "AI-102", "mode": trace.mode, "time": trace.timestamp,
        "total_ms": f"{trace.total_ms:.0f} ms",
        "level": profile.experience_level.value.replace("_", " ").title() if profile else "—",
        "avg_conf": "—", "risk_count": "—",
    }])

if len(history_df) > 0:
    st.dataframe(
        history_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "run_id":     st.column_config.TextColumn("Run ID",     width="small"),
            "student":    st.column_config.TextColumn("Student",    width="medium"),
            "exam":       st.column_config.TextColumn("Exam",       width="medium"),
            "mode":       st.column_config.TextColumn("Mode",       width="small"),
            "time":       st.column_config.TextColumn("Timestamp",  width="medium"),
            "total_ms":   st.column_config.TextColumn("Total Time", width="small"),
            "level":      st.column_config.TextColumn("Level",      width="medium"),
            "avg_conf":   st.column_config.TextColumn("Avg Conf",   width="small"),
            "risk_count": st.column_config.NumberColumn("Risk Domains", width="small"),
        },
    )
else:
    st.info("No sessions recorded yet — generate a profile from the main page first.")


# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<p style='text-align:center;color:#4a5568;font-size:0.78rem;'>"
    "🔐 Admin Dashboard · AI-102 Agents League · For authorised users only"
    "</p>",
    unsafe_allow_html=True,
)
