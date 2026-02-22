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


# ─── Initialize on import ────────────────────────────────────────────────────
init_db()
