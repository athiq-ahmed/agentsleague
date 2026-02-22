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
    page_title="Admin Dashboard – Cert Prep Agents",
    page_icon="🔐",
    layout="wide",
)

# ─── Theme constants (Microsoft Learn light theme) ────────────────────────────
BG        = "#F5F5F5"
CARD_BG   = "#FFFFFF"
BLUE      = "#0078D4"
PURPLE    = "#5C2D91"
GREEN     = "#107C10"
ORANGE    = "#CA5010"
RED       = "#D13438"
YELLOW    = "#8A6D00"
GREY      = "#616161"

AGENT_COLORS = {
    "safety":     RED,
    "intake":     BLUE,
    "profiling":  PURPLE,
    "scorer":     GREEN,
    "gate":       ORANGE,
    "analogy":    "#00B7C3",
    "engagement": "#0078D4",
}

# ─── Minimal page CSS (MS Learn light) ────────────────────────────────────────
st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background: #F5F5F5; }
  [data-testid="stSidebar"]          { background: #FAFAFA; border-right: 1px solid #E1DFDD; }
  [data-testid="stHeader"]           { background: #fff !important; border-bottom: 1px solid #E1DFDD; }
  [data-testid="stSidebarNav"]       { display: none; }
  h1, h2, h3, h4                     { color: #1B1B1B !important; font-family: 'Segoe UI', sans-serif; }
  .stMarkdown p, .stMarkdown li      { color: #323130; }
  .stExpander details                 { background: #FFFFFF; border-radius: 4px; border: 1px solid #E1DFDD !important; }
  .stExpander summary                 { color: #1B1B1B !important; }
  div[data-testid="stTable"]          { background: #FFFFFF; border-radius: 4px; border: 1px solid #E1DFDD; }
  .stButton > button {
    background: #0078D4 !important; border: none !important; color: #fff !important;
    border-radius: 4px !important; font-weight: 600 !important;
  }
  .stButton > button:hover { background: #106EBE !important; }
  .stCaption { color: #616161 !important; }
</style>
""", unsafe_allow_html=True)

# ─── Helpers ──────────────────────────────────────────────────────────────────

def _card(label: str, value: str, color: str = BLUE, wide: bool = False) -> str:
    w = "100%" if wide else "auto"
    return f"""
    <div style="background:{CARD_BG};border-left:4px solid {color};border-radius:4px;
                padding:10px 16px;display:inline-block;min-width:160px;width:{w};
                margin-bottom:8px;box-sizing:border-box;border:1px solid #E1DFDD;
                box-shadow:0 1px 2px rgba(0,0,0,0.04);">
      <div style="color:{GREY};font-size:0.7rem;font-weight:600;text-transform:uppercase;
                  letter-spacing:.06em;margin-bottom:3px;">{label}</div>
      <div style="color:#1B1B1B;font-size:1rem;font-weight:700;">{value}</div>
    </div>"""


def _section_header(title: str, icon: str = "") -> None:
    st.markdown(
        f"""<h3 style="color:#1B1B1B;border-bottom:1px solid #E1DFDD;
                        padding-bottom:6px;margin-top:28px;">{icon} {title}</h3>""",
        unsafe_allow_html=True,
    )


def _badge(text: str, color: str) -> str:
    return (
        f'<span style="background:{color}15;color:{color};border:1px solid {color}40;'
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

# Auto-login if already authenticated as admin from the main sign-in page
if st.session_state.get("user_type") == "admin":
    st.session_state["admin_logged_in"] = True

if "admin_logged_in" not in st.session_state:
    st.session_state["admin_logged_in"] = False


def _show_login() -> None:
    st.markdown("""
    <div style="max-width:400px;margin:80px auto 0;">
      <div style="text-align:center;margin-bottom:32px;">
        <span style="font-size:3rem;">🔐</span>
        <h2 style="color:#1B1B1B;margin-top:8px;">Admin Access</h2>
        <p style="color:#616161;font-size:0.9rem;">
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
            "<p style='text-align:center;color:#a0a0a0;font-size:0.78rem;"
            "margin-top:16px;'>Hint: username&nbsp;=&nbsp;<code>admin</code> &nbsp;|&nbsp; "
            "password&nbsp;=&nbsp;<code>agents2026</code></p>",
            unsafe_allow_html=True,
        )


if not st.session_state["admin_logged_in"]:
    _show_login()
    st.stop()


# ─── Authenticated: sidebar logout ────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;padding:4px 0 12px;">
      <svg width="20" height="20" viewBox="0 0 23 23">
        <rect width="11" height="11" fill="#f25022"/>
        <rect x="12" width="11" height="11" fill="#7fba00"/>
        <rect y="12" width="11" height="11" fill="#00a4ef"/>
        <rect x="12" y="12" width="11" height="11" fill="#ffb900"/>
      </svg>
      <span style="color:#1B1B1B;font-size:0.95rem;font-weight:600;
                   font-family:'Segoe UI',sans-serif;">Microsoft Learn</span>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("### 🔐 Admin Panel")
    st.markdown(f"Signed in as **{MOCK_USER}**")
    if st.button("Sign Out", use_container_width=True):
        st.session_state["admin_logged_in"] = False
        st.rerun()
    st.markdown("---")
    st.caption("Only admins can see this page.\nStudents see the main Profiler UI.")


# ─── Page header ──────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">
  <span style="font-size:2rem;">🤖</span>
  <div>
    <h1 style="color:#1B1B1B;margin:0;font-size:1.9rem;">Agent Interaction Dashboard</h1>
    <p style="color:#616161;margin:0;font-size:0.9rem;">
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
        "Go to the main **Cert Prep** page, fill in the intake form, "
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
# SECTION 2 – Learner Journey Flow
# ═════════════════════════════════════════════════════════════════════════════
_section_header("Learner Journey Flow", "🗺️")

st.caption(
    "End-to-end view of the learner's path through the multi-agent system. "
    "Each stage shows the responsible agent, its contribution, and timing."
)

# ── 2a: Journey funnel ───────────────────────────────────────────────────────
_j_col1, _j_col2 = st.columns([3, 2])

with _j_col1:
    _stages = [
        "Student Input",
        "Intake & Profiling",
        "Learning Path Planning",
        "Study Plan Generation",
        "Domain Confidence Scoring",
        "Readiness Assessment",
    ]
    _stage_values  = [100, 92, 85, 78, 70, 65]
    _stage_colors  = [BLUE, PURPLE, "#a78bfa", "#06b6d4", GREEN, ORANGE]

    funnel_fig = go.Figure(go.Funnel(
        y=_stages,
        x=_stage_values,
        textinfo="value+percent initial",
        marker=dict(color=_stage_colors),
        connector=dict(line=dict(color="#E1DFDD", width=1)),
    ))
    funnel_fig.update_layout(
        paper_bgcolor=CARD_BG,
        plot_bgcolor=CARD_BG,
        font=dict(color="#1B1B1B", size=11),
        height=340,
        margin=dict(l=10, r=10, t=10, b=10),
    )
    st.plotly_chart(funnel_fig, use_container_width=True)

with _j_col2:
    # Agent contribution pie chart
    _agent_labels = [s.agent_name.split("(")[0].strip() for s in trace.steps]
    _agent_times  = [s.duration_ms for s in trace.steps]
    _agent_clrs   = [AGENT_COLORS.get(s.agent_id, BLUE) for s in trace.steps]

    pie_fig = go.Figure(go.Pie(
        labels=_agent_labels,
        values=_agent_times,
        hole=0.45,
        marker=dict(colors=_agent_clrs, line=dict(color=CARD_BG, width=2)),
        textinfo="label+percent",
        textfont=dict(size=10),
        hovertemplate="<b>%{label}</b><br>%{value:.0f} ms (%{percent})<extra></extra>",
    ))
    pie_fig.update_layout(
        paper_bgcolor=CARD_BG,
        plot_bgcolor=CARD_BG,
        font=dict(color="#1B1B1B", size=11),
        height=340,
        margin=dict(l=10, r=10, t=10, b=10),
        showlegend=False,
        annotations=[dict(
            text=f"<b>{trace.total_ms:.0f}<br>ms</b>",
            x=0.5, y=0.5, font=dict(size=16, color="#1B1B1B"),
            showarrow=False,
        )],
    )
    st.plotly_chart(pie_fig, use_container_width=True)

# ── 2b: Journey stage cards ──────────────────────────────────────────────────
_journey_stages = [
    {
        "icon": "📥", "title": "Intake",
        "agent": "safety + intake", "color": BLUE,
        "desc": "Collect learner background, goals, constraints. Apply safety guardrails.",
    },
    {
        "icon": "🧠", "title": "Profiling",
        "agent": "profiling + scorer", "color": PURPLE,
        "desc": "Infer experience level, learning style, per-domain knowledge & confidence.",
    },
    {
        "icon": "🗺️", "title": "Learning Path",
        "agent": "analogy mapper", "color": "#06b6d4",
        "desc": "Map existing skills to exam domains. Curate MS Learn modules & resources.",
    },
    {
        "icon": "📅", "title": "Study Plan",
        "agent": "engagement gen", "color": GREEN,
        "desc": "Generate week-by-week Gantt plan. Allocate hours by domain weight & risk.",
    },
    {
        "icon": "✅", "title": "Readiness Gate",
        "agent": "gate checker", "color": ORANGE,
        "desc": "Evaluate if learner is ready for assessment or needs remediation loop.",
    },
    {
        "icon": "📊", "title": "Assessment",
        "agent": "assessment + verifier", "color": RED,
        "desc": "Build exam-style quiz, verify quality, score results, decide GO/NO-GO.",
    },
]

_jcols = st.columns(len(_journey_stages))
for _jc, _js in zip(_jcols, _journey_stages):
    with _jc:
        st.markdown(
            f"""<div style="background:{CARD_BG};border-top:3px solid {_js['color']};
                 border-radius:4px;padding:14px 12px;text-align:center;min-height:180px;
                 border:1px solid #E1DFDD;box-shadow:0 1px 2px rgba(0,0,0,0.04);">
              <div style="font-size:1.8rem;">{_js['icon']}</div>
              <div style="color:#1B1B1B;font-weight:700;font-size:0.95rem;margin:6px 0 4px;">
                {_js['title']}</div>
              <div style="color:{GREY};font-size:0.72rem;text-transform:uppercase;
                   letter-spacing:.04em;margin-bottom:6px;">{_js['agent']}</div>
              <div style="color:#616161;font-size:0.78rem;line-height:1.4;">{_js['desc']}</div>
            </div>""",
            unsafe_allow_html=True,
        )


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
    font         = dict(color="#1B1B1B", size=11),
    height       = max(220, len(trace.steps) * 52),
    margin       = dict(l=10, r=20, t=10, b=40),
    xaxis = dict(
        title      = "Time (ms from run start)",
        color      = GREY,
        gridcolor  = "#E1DFDD",
        zeroline   = False,
    ),
    yaxis = dict(
        color      = "#1B1B1B",
        gridcolor  = "#E1DFDD",
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
                <div style="background:#F5F5F5;border-left:3px solid {clr};
                            border-radius:4px;padding:12px 14px;margin-bottom:10px;">
                  <div style="color:{GREY};font-size:0.72rem;font-weight:600;
                              text-transform:uppercase;letter-spacing:.06em;
                              margin-bottom:4px;">📨 Input</div>
                  <div style="color:#323130;font-size:0.87rem;
                              line-height:1.5;">{step.input_summary}</div>
                </div>
                <div style="background:#F5F5F5;border-left:3px solid {GREEN};
                            border-radius:4px;padding:12px 14px;">
                  <div style="color:{GREY};font-size:0.72rem;font-weight:600;
                              text-transform:uppercase;letter-spacing:.06em;
                              margin-bottom:4px;">📤 Output</div>
                  <div style="color:#323130;font-size:0.87rem;
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
                        f'<div style="color:#323130;font-size:0.83rem;'
                        f'padding:2px 0 2px 10px;border-left:2px solid {clr}40;">'
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
                fill_color = "#EFF6FF",
                align      = "left",
                font       = dict(color="#1B1B1B", size=12),
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
                font       = dict(color="#1B1B1B", size=11),
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
            font          = dict(color="#1B1B1B", size=11),
            height        = 280,
            margin        = dict(l=0, r=50, t=10, b=20),
            xaxis = dict(
                range      = [0, 1.05],
                gridcolor  = "#E1DFDD",
                color      = GREY,
                tickformat = ".0%",
            ),
            yaxis = dict(color="#1B1B1B", gridcolor="#E1DFDD"),
        )
        bar_fig.add_vline(x=0.50, line_dash="dash", line_color="rgba(0,0,0,0.15)",
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
        "exam": trace.exam_target.split("–")[0].strip(), "mode": trace.mode, "time": trace.timestamp,
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
    "<p style='text-align:center;color:#a0a0a0;font-size:0.78rem;'>"
    "🔐 Admin Dashboard · Microsoft Agents League · For authorised users only"
    "</p>",
    unsafe_allow_html=True,
)
