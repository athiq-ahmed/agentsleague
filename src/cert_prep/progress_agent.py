"""
progress_agent.py – Mid-Journey Progress Tracker & Readiness Assessor
======================================================================
Handles the "returning learner" flow:

  ProgressAgent
    • Accepts a mid-journey ProgressSnapshot (hours spent, per-domain
      self-ratings, practice-exam status) alongside the student's original
      LearnerProfile.
    • Computes an overall ReadinessAssessment (readiness %, verdict, nudges).
    • Identifies which Gantt blocks are ahead / on-track / behind schedule.

  generate_weekly_summary(profile, snapshot, assessment) → str (HTML)
    Produces a formatted HTML e-mail body for the weekly progress report.

  attempt_send_email(to_address, subject, html_body, config) → bool
    Tries to send via SMTP if env vars are set; returns True on success.
"""

from __future__ import annotations

import os
import smtplib
import textwrap
from dataclasses import dataclass, field
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from typing import Optional

from cert_prep.models import EXAM_DOMAINS, LearnerProfile


# ─── Domain weights lookup ────────────────────────────────────────────────────
_DOMAIN_WEIGHT: dict[str, float] = {d["id"]: d["weight"] for d in EXAM_DOMAINS}
_DOMAIN_NAME:   dict[str, str]   = {d["id"]: d["name"]   for d in EXAM_DOMAINS}


# ─── Enumerations ────────────────────────────────────────────────────────────

class ReadinessVerdict(str, Enum):
    NOT_READY    = "not_ready"      # < 45 %
    NEEDS_WORK   = "needs_work"     # 45–60 %
    NEARLY_READY = "nearly_ready"   # 60–75 %
    EXAM_READY   = "exam_ready"     # ≥ 75 %


class NudgeLevel(str, Enum):
    DANGER  = "danger"   # red
    WARNING = "warning"  # orange/amber
    INFO    = "info"     # blue
    SUCCESS = "success"  # green


# ─── Input / Output models ────────────────────────────────────────────────────

@dataclass
class DomainProgress:
    """Student's self-assessed progress on one exam domain (1–5 scale)."""
    domain_id:    str
    domain_name:  str
    self_rating:  int     # 1 = barely started … 5 = confident / ready
    hours_spent:  float   # hours invested in this domain so far


@dataclass
class ProgressSnapshot:
    """
    Mid-journey state reported by a returning learner.
    Captured via the Streamlit check-in form.
    """
    total_hours_spent:   float
    weeks_elapsed:       int              # weeks since starting the plan
    domain_progress:     list[DomainProgress]
    done_practice_exam:  str              # "yes" | "some" | "no"
    practice_score_pct:  Optional[int]   # 0-100 if done, else None
    email:               Optional[str]   # for weekly summary
    notes:               str             # free-text from student


@dataclass
class Nudge:
    """A single actionable alert/notification for the student."""
    level:   NudgeLevel
    title:   str
    message: str


@dataclass
class DomainStatusLine:
    """Actual vs expected progress for one domain."""
    domain_id:        str
    domain_name:      str
    expected_rating:  float   # 1–5 scale inferred from plan
    actual_rating:    int     # student self-rating
    gap:              float   # actual – expected  (negative = behind)
    status:           str     # "ahead" | "on_track" | "behind" | "critical"


@dataclass
class ReadinessAssessment:
    """
    Output of ProgressAgent.assess().
    All fields consumed by the Streamlit My Progress tab.
    """
    readiness_pct:       float          # 0–100
    verdict:             ReadinessVerdict
    verdict_label:       str            # human-readable
    verdict_colour:      str            # hex
    domain_status:       list[DomainStatusLine]
    nudges:              list[Nudge]
    hours_progress_pct:  float          # hours_spent / total_budget %
    hours_remaining:     float
    weeks_remaining:     int
    recommended_focus:   list[str]      # domain_ids to focus on next
    exam_go_nogo:        str            # "GO" | "CONDITIONAL GO" | "NOT YET"
    go_nogo_colour:      str            # hex
    go_nogo_reason:      str


# ─── Progress Agent ───────────────────────────────────────────────────────────

class ProgressAgent:
    """
    Analyses a mid-journey ProgressSnapshot against the original LearnerProfile
    to produce a ReadinessAssessment with smart nudges.
    """

    _VERDICT_META: dict[ReadinessVerdict, tuple[str, str]] = {
        ReadinessVerdict.NOT_READY:    ("Not Ready",      "#d13438"),
        ReadinessVerdict.NEEDS_WORK:   ("Needs Work",     "#ca5010"),
        ReadinessVerdict.NEARLY_READY: ("Nearly Ready",   "#8a6d00"),
        ReadinessVerdict.EXAM_READY:   ("Exam Ready! 🎉", "#107c10"),
    }

    def assess(
        self,
        profile: LearnerProfile,
        snap: ProgressSnapshot,
    ) -> ReadinessAssessment:

        # ── 1. Weighted domain readiness ──────────────────────────────────────
        # Domain score = self_rating / 5, weighted by exam weight
        weighted_score = 0.0
        for dp in snap.domain_progress:
            w = _DOMAIN_WEIGHT.get(dp.domain_id, 1 / len(EXAM_DOMAINS))
            weighted_score += (dp.self_rating / 5.0) * w

        # ── 2. Hours progress ratio ───────────────────────────────────────────
        total_budget = profile.total_budget_hours or 1.0
        hours_progress = min(snap.total_hours_spent / total_budget, 1.0)

        # ── 3. Practice exam bonus ────────────────────────────────────────────
        if snap.done_practice_exam == "yes" and snap.practice_score_pct is not None:
            practice_factor = min(snap.practice_score_pct / 100.0, 1.0)
        elif snap.done_practice_exam == "some":
            practice_factor = 0.50
        else:
            practice_factor = 0.0

        # ── 4. Composite readiness ────────────────────────────────────────────
        # Weights: domain self-assessment 55%, hours 25%, practice 20%
        readiness_raw = (
            weighted_score   * 0.55 +
            hours_progress   * 0.25 +
            practice_factor  * 0.20
        )
        readiness_pct = round(readiness_raw * 100, 1)

        # ── 5. Verdict ────────────────────────────────────────────────────────
        if readiness_pct >= 75:
            verdict = ReadinessVerdict.EXAM_READY
        elif readiness_pct >= 60:
            verdict = ReadinessVerdict.NEARLY_READY
        elif readiness_pct >= 45:
            verdict = ReadinessVerdict.NEEDS_WORK
        else:
            verdict = ReadinessVerdict.NOT_READY

        verdict_label, verdict_colour = self._VERDICT_META[verdict]

        # ── 6. Domain status (actual vs expected) ────────────────────────────
        weeks_elapsed  = max(snap.weeks_elapsed, 1)
        plan_progress  = min(weeks_elapsed / max(profile.weeks_available, 1), 1.0)
        expected_avg   = 1 + (4 * plan_progress)   # expected rating grows 1→5 over the plan

        domain_status: list[DomainStatusLine] = []
        for dp in snap.domain_progress:
            expected = max(1.0, min(5.0, expected_avg))
            gap      = dp.self_rating - expected
            if gap >= 0.5:
                status = "ahead"
            elif gap >= -0.5:
                status = "on_track"
            elif gap >= -1.5:
                status = "behind"
            else:
                status = "critical"
            domain_status.append(DomainStatusLine(
                domain_id       = dp.domain_id,
                domain_name     = dp.domain_name,
                expected_rating = round(expected, 1),
                actual_rating   = dp.self_rating,
                gap             = round(gap, 1),
                status          = status,
            ))

        # ── 7. Nudges ─────────────────────────────────────────────────────────
        nudges = self._build_nudges(profile, snap, readiness_pct, domain_status, hours_progress)

        # ── 8. Recommended focus domains ─────────────────────────────────────
        focus = [
            ds.domain_id for ds in
            sorted(domain_status, key=lambda d: (d.actual_rating, d.gap))
            if ds.status in ("behind", "critical")
        ][:3]
        if not focus:
            # suggest the risk domains from the original profile
            focus = profile.risk_domains[:2]

        # ── 9. Hours remaining ────────────────────────────────────────────────
        hours_remaining = max(0.0, total_budget - snap.total_hours_spent)
        weeks_remaining = max(0, profile.weeks_available - snap.weeks_elapsed)

        # ── 10. GO / NO-GO ────────────────────────────────────────────────────
        go_nogo, go_colour, go_reason = self._go_nogo(
            readiness_pct, snap, weeks_remaining, domain_status,
        )

        return ReadinessAssessment(
            readiness_pct       = readiness_pct,
            verdict             = verdict,
            verdict_label       = verdict_label,
            verdict_colour      = verdict_colour,
            domain_status       = domain_status,
            nudges              = nudges,
            hours_progress_pct  = round(hours_progress * 100, 1),
            hours_remaining     = round(hours_remaining, 1),
            weeks_remaining     = weeks_remaining,
            recommended_focus   = focus,
            exam_go_nogo        = go_nogo,
            go_nogo_colour      = go_colour,
            go_nogo_reason      = go_reason,
        )

    # ── Nudge builder ─────────────────────────────────────────────────────────

    def _build_nudges(
        self,
        profile: LearnerProfile,
        snap: ProgressSnapshot,
        readiness_pct: float,
        domain_status: list[DomainStatusLine],
        hours_progress: float,
    ) -> list[Nudge]:
        nudges: list[Nudge] = []

        # Overall readiness nudge
        if readiness_pct >= 75:
            nudges.append(Nudge(
                level=NudgeLevel.SUCCESS,
                title="You're exam ready! 🎉",
                message=(
                    f"Your readiness score is **{readiness_pct:.0f}%**. "
                    "Book your exam slot now — every extra day is money saved! "
                    "Focus remaining time on practice tests and edge-case topics."
                ),
            ))
        elif readiness_pct >= 60:
            nudges.append(Nudge(
                level=NudgeLevel.WARNING,
                title="Nearly there — final push needed",
                message=(
                    f"You're at **{readiness_pct:.0f}%** readiness. "
                    "You need one more focused study sprint before scheduling your exam. "
                    "Close the gaps in your weakest domains and complete at least one full practice exam."
                ),
            ))
        elif readiness_pct >= 45:
            nudges.append(Nudge(
                level=NudgeLevel.WARNING,
                title="Progress detected — more structured study required",
                message=(
                    f"Readiness is **{readiness_pct:.0f}%**. You're making progress but "
                    "aren't yet ready to sit the exam confidently. "
                    "Increase weekly hours and focus on the flagged critical domains below."
                ),
            ))
        else:
            nudges.append(Nudge(
                level=NudgeLevel.DANGER,
                title="Not yet ready — serious study time needed",
                message=(
                    f"Readiness is **{readiness_pct:.0f}%**. Do not schedule your exam yet. "
                    "Revisit your study plan, consider requesting more time from your employer/schedule, "
                    "and prioritise the weakest domains urgently."
                ),
            ))

        # Hours pacing nudge
        if hours_progress < 0.30 and snap.weeks_elapsed > 1:
            nudges.append(Nudge(
                level=NudgeLevel.DANGER,
                title="⏰ You're behind on study hours",
                message=(
                    f"You've completed only **{snap.total_hours_spent:.0f} h** "
                    f"({hours_progress:.0%} of your {profile.total_budget_hours:.0f} h budget), "
                    "but have already used "
                    f"{snap.weeks_elapsed}/{profile.weeks_available} weeks. "
                    "Consider increasing your daily study blocks to catch up."
                ),
            ))
        elif hours_progress < 0.55 and snap.weeks_elapsed >= profile.weeks_available // 2:
            nudges.append(Nudge(
                level=NudgeLevel.WARNING,
                title="⏰ Halfway through your weeks — check your pacing",
                message=(
                    f"You're {snap.weeks_elapsed}/{profile.weeks_available} weeks in "
                    f"but have only used {hours_progress:.0%} of your study budget. "
                    "Try to add an extra study session each week."
                ),
            ))

        # Critical domain nudges
        critical = [ds for ds in domain_status if ds.status == "critical"]
        if critical:
            names = ", ".join(
                ds.domain_name.replace("Implement ", "").replace(" Solutions", "")
                for ds in critical
            )
            nudges.append(Nudge(
                level=NudgeLevel.DANGER,
                title=f"🚨 {len(critical)} domain(s) critically behind",
                message=(
                    f"**{names}** — your self-rating is significantly below where it should be "
                    "at this point in your plan. Dedicate your next 2–3 study sessions exclusively "
                    "to these topics."
                ),
            ))

        # No practice exam nudge
        if snap.done_practice_exam == "no" and snap.weeks_elapsed >= 2:
            nudges.append(Nudge(
                level=NudgeLevel.INFO,
                title="📝 No practice exam taken yet",
                message=(
                    "Practice exams are one of the strongest predictors of actual exam success. "
                    "Take a timed practice test on Microsoft Learn or MeasureUp this week — "
                    "even a partial one — to benchmark your readiness objectively."
                ),
            ))

        # Practice exam low score
        if (snap.done_practice_exam == "yes"
                and snap.practice_score_pct is not None
                and snap.practice_score_pct < 65):
            nudges.append(Nudge(
                level=NudgeLevel.WARNING,
                title=f"📝 Practice score {snap.practice_score_pct}% — below pass threshold",
                message=(
                    "Microsoft certification exams typically require ~70% to pass. Your practice score suggests "
                    "targeted revision is still needed. Focus on the domains where you lost "
                    "marks in the practice exam, not broad re-reading."
                ),
            ))

        return nudges

    # ── GO / NO-GO logic ──────────────────────────────────────────────────────

    def _go_nogo(
        self,
        readiness_pct: float,
        snap: ProgressSnapshot,
        weeks_remaining: int,
        domain_status: list[DomainStatusLine],
    ) -> tuple[str, str, str]:
        critical_count = sum(1 for ds in domain_status if ds.status == "critical")

        if readiness_pct >= 75 and critical_count == 0:
            return (
                "GO",
                "#107c10",
                "Your readiness score and domain coverage both clear the threshold. "
                "You are ready to book your exam.",
            )
        elif readiness_pct >= 65 and critical_count <= 1 and weeks_remaining >= 1:
            return (
                "CONDITIONAL GO",
                "#8a6d00",
                f"You're close — one more targeted study week should get you over the line. "
                f"{'Close the gap on 1 critical domain first. ' if critical_count else ''}"
                "Book a date ~2 weeks out to maintain urgency.",
            )
        else:
            reasons = []
            if readiness_pct < 65:
                reasons.append(f"readiness is {readiness_pct:.0f}% (target ≥75%)")
            if critical_count > 1:
                reasons.append(f"{critical_count} domains critically behind schedule")
            if weeks_remaining == 0 and readiness_pct < 65:
                reasons.append("no study weeks remaining but score not sufficient")
            return (
                "NOT YET",
                "#d13438",
                "Do not book the exam yet. " + "; ".join(reasons).capitalize() + ".",
            )


# ─── Weekly summary e-mail ────────────────────────────────────────────────────

def generate_weekly_summary(
    profile: LearnerProfile,
    snap: ProgressSnapshot,
    assessment: ReadinessAssessment,
) -> str:
    """
    Returns a self-contained HTML string suitable for sending as an e-mail body.
    Also usable as an in-app preview.
    """
    today = date.today().strftime("%B %d, %Y")
    domain_rows = ""
    for ds in assessment.domain_status:
        gap_html = ""
        if ds.status == "critical":
            gap_html = "<span style='color:#d13438;font-weight:700;'>🚨 Critical</span>"
        elif ds.status == "behind":
            gap_html = "<span style='color:#ca5010;'>⚠ Behind</span>"
        elif ds.status == "on_track":
            gap_html = "<span style='color:#0078d4;'>◑ On track</span>"
        else:
            gap_html = "<span style='color:#107c10;'>✓ Ahead</span>"

        domain_rows += f"""
        <tr>
          <td style="padding:6px 10px;border-bottom:1px solid #eeeeee;">{ds.domain_name}</td>
          <td style="padding:6px 10px;border-bottom:1px solid #eeeeee;text-align:center;">
            {"⭐" * ds.actual_rating}{"☆" * (5 - ds.actual_rating)} ({ds.actual_rating}/5)
          </td>
          <td style="padding:6px 10px;border-bottom:1px solid #eeeeee;text-align:center;">{gap_html}</td>
        </tr>"""

    nudge_html = ""
    level_bg = {
        NudgeLevel.DANGER:  "#fde7f3",
        NudgeLevel.WARNING: "#fff4ce",
        NudgeLevel.INFO:    "#eef6ff",
        NudgeLevel.SUCCESS: "#e9f7ee",
    }
    level_border = {
        NudgeLevel.DANGER:  "#d13438",
        NudgeLevel.WARNING: "#ca5010",
        NudgeLevel.INFO:    "#0078d4",
        NudgeLevel.SUCCESS: "#107c10",
    }
    for n in assessment.nudges[:4]:
        bg  = level_bg.get(n.level, "#f5f5f5")
        bdr = level_border.get(n.level, "#888")
        nudge_html += f"""
        <div style="margin:8px 0;padding:10px 14px;background:{bg};
                    border-left:4px solid {bdr};border-radius:6px;">
          <b>{n.title}</b><br/>
          <span style="font-size:0.9em;">{n.message.replace("**","<b>",1).replace("**","</b>",1)}</span>
        </div>"""

    verdict_colour = assessment.verdict_colour
    go_colour      = assessment.go_nogo_colour

    html = textwrap.dedent(f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family:Segoe UI,Arial,sans-serif;max-width:640px;margin:auto;
                 background:#f9f9f9;padding:20px;">
      <div style="background:linear-gradient(135deg,#5C2D91,#B4009E);color:white;
                  padding:20px 24px;border-radius:12px;margin-bottom:20px;">
        <h2 style="margin:0;">📊 Weekly Study Progress Report</h2>
        <p style="margin:4px 0 0;opacity:0.85;">{profile.student_name} · {profile.exam_target} · {today}</p>
      </div>

      <div style="display:flex;gap:12px;margin-bottom:16px;">
        <div style="flex:1;background:white;border-left:4px solid {verdict_colour};
                    border-radius:8px;padding:12px 16px;box-shadow:0 2px 6px rgba(0,0,0,0.06);">
          <div style="font-size:0.75rem;color:#888;font-weight:600;text-transform:uppercase;">
            Readiness Score
          </div>
          <div style="font-size:1.6rem;font-weight:700;color:{verdict_colour};">
            {assessment.readiness_pct:.0f}%
          </div>
          <div style="font-size:0.85rem;color:{verdict_colour};font-weight:600;">
            {assessment.verdict_label}
          </div>
        </div>
        <div style="flex:1;background:white;border-left:4px solid {go_colour};
                    border-radius:8px;padding:12px 16px;box-shadow:0 2px 6px rgba(0,0,0,0.06);">
          <div style="font-size:0.75rem;color:#888;font-weight:600;text-transform:uppercase;">
            Exam Decision
          </div>
          <div style="font-size:1.6rem;font-weight:700;color:{go_colour};">
            {assessment.exam_go_nogo}
          </div>
          <div style="font-size:0.85rem;color:#555;">{assessment.go_nogo_reason[:80]}…</div>
        </div>
        <div style="flex:1;background:white;border-left:4px solid #0078d4;
                    border-radius:8px;padding:12px 16px;box-shadow:0 2px 6px rgba(0,0,0,0.06);">
          <div style="font-size:0.75rem;color:#888;font-weight:600;text-transform:uppercase;">
            Hours Studied
          </div>
          <div style="font-size:1.6rem;font-weight:700;color:#0078d4;">
            {snap.total_hours_spent:.0f} h
          </div>
          <div style="font-size:0.85rem;color:#555;">
            of {profile.total_budget_hours:.0f} h ({assessment.hours_progress_pct:.0f}%)
          </div>
        </div>
      </div>

      <h3 style="color:#5C2D91;margin:16px 0 8px;">🔔 This Week's Nudges</h3>
      {nudge_html}

      <h3 style="color:#5C2D91;margin:16px 0 8px;">📚 Domain Progress</h3>
      <table style="width:100%;border-collapse:collapse;background:white;
                    border-radius:8px;overflow:hidden;box-shadow:0 2px 6px rgba(0,0,0,0.06);">
        <thead>
          <tr style="background:#5C2D91;color:white;">
            <th style="padding:8px 10px;text-align:left;">Domain</th>
            <th style="padding:8px 10px;text-align:center;">Self-Rating</th>
            <th style="padding:8px 10px;text-align:center;">Status</th>
          </tr>
        </thead>
        <tbody>
          {domain_rows}
        </tbody>
      </table>

      <p style="margin-top:24px;font-size:0.8rem;color:#888;text-align:center;">
        Generated by <b>Cert Prep Agent</b> · Microsoft Agents League ·
        <a href="http://localhost:8501" style="color:#5C2D91;">Open app</a>
      </p>
    </body>
    </html>
    """).strip()
    return html


# ─── Email dispatch ───────────────────────────────────────────────────────────

def attempt_send_email(
    to_address: str,
    subject: str,
    html_body: str,
) -> tuple[bool, str]:
    """
    Attempts to send `html_body` to `to_address` via SMTP.

    Reads SMTP config from environment variables:
        SMTP_HOST  (default: smtp.gmail.com)
        SMTP_PORT  (default: 587)
        SMTP_USER  – sender address / login
        SMTP_PASS  – app password
        SMTP_FROM  – display From address (defaults to SMTP_USER)

    Returns:
        (True, "Sent successfully")  on success
        (False, "<error message>")   on failure / missing config
    """
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")
    smtp_from = os.getenv("SMTP_FROM", smtp_user)

    if not smtp_user or not smtp_pass:
        return False, (
            "SMTP credentials not configured. "
            "Set SMTP_USER and SMTP_PASS environment variables to enable email sending."
        )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = smtp_from
    msg["To"]      = to_address
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_from, [to_address], msg.as_string())
        return True, "Email sent successfully! Check your inbox."
    except Exception as exc:
        return False, f"Failed to send email: {exc}"
