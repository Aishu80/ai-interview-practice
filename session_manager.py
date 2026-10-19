"""
SQLite-based session persistence manager for the AI Interview Practice platform.

Stores interview histories, metadata, and JSON evaluation reports.
All queries use parameterized SQL to guarantee safe data manipulation.
"""

import os
import json
import sqlite3
import logging
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

from utils.config import AppConfig, get_config
from models.schemas import InterviewSession, FeedbackReport


logger = logging.getLogger(__name__)


class SessionManager:
    """Manages SQLite persistence for interview sessions and feedback records."""

    def __init__(self, db_path: str = "interview_history.db", enabled: bool = True) -> None:
        """Initializes the session manager and sets up database tables if enabled.

        Args:
            db_path: Path to the SQLite database file.
            enabled: Whether persistence is enabled. If False, operations safely no-op.
        """
        self.db_path = db_path
        self.enabled = enabled

        if self.enabled:
            self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Creates and returns a connection to the SQLite database."""
        return sqlite3.connect(self.db_path, timeout=10.0)

    def _init_db(self) -> None:
        """Creates the required tables and indexes if they do not exist."""
        try:
            # Ensure the directory exists if a directory path is included
            if self.db_path != ":memory:":
                db_dir = os.path.dirname(self.db_path)
                if db_dir:
                    os.makedirs(db_dir, exist_ok=True)

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS sessions (
                        id TEXT PRIMARY KEY,
                        created_at TEXT NOT NULL,
                        target_role TEXT,
                        interview_type TEXT,
                        mcq_score REAL,
                        written_score REAL,
                        combined_score REAL,
                        summary TEXT
                    )
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_sessions_created_at
                    ON sessions (created_at DESC)
                """)
                conn.commit()
        except Exception as exc:
            logger.error("Failed to initialize session database at %s: %s", self.db_path, exc)

    def save_session(self, session_id: str, data: dict) -> bool:
        """Saves or updates a session summary record in the database.

        Args:
            session_id: Unique session identifier string.
            data: Session summary dictionary containing session attributes.

        Returns:
            bool: True if the record was successfully saved, False otherwise.
        """
        if not self.enabled:
            return False

        if not session_id or not isinstance(session_id, str):
            logger.error("Cannot save session with invalid session_id: %s", session_id)
            return False

        if not isinstance(data, dict):
            logger.error("Session data must be a dictionary.")
            return False

        try:
            created_at = data.get("created_at") or datetime.now().isoformat()

            # Extract target_role (supports direct key or nested interview_config)
            target_role = data.get("target_role")
            if target_role is None and isinstance(data.get("interview_config"), dict):
                target_role = data["interview_config"].get("target_role")
            target_role = str(target_role) if target_role is not None else ""

            # Extract interview_type (supports direct key or nested interview_config)
            interview_type = data.get("interview_type")
            if interview_type is None and isinstance(data.get("interview_config"), dict):
                interview_type = data["interview_config"].get("interview_type")
            interview_type = str(interview_type) if interview_type is not None else ""

            # Extract scores (supports direct keys or nested result objects)
            mcq_score = data.get("mcq_score")
            if mcq_score is None and isinstance(data.get("mcq_results"), dict):
                mcq_score = data["mcq_results"].get("accuracy")
            mcq_score = float(mcq_score) if mcq_score is not None else None

            written_score = data.get("written_score")
            if written_score is None and isinstance(data.get("written_assessment"), dict):
                written_score = data["written_assessment"].get("overall_score")
            written_score = float(written_score) if written_score is not None else None

            combined_score = data.get("combined_score")
            combined_score = float(combined_score) if combined_score is not None else None

            # Serialize summary payload
            summary_content = data.get("summary", data)
            if isinstance(summary_content, (dict, list)):
                summary_json = json.dumps(summary_content, default=str)
            else:
                summary_json = str(summary_content or "{}")

            sql = """
                INSERT OR REPLACE INTO sessions (
                    id, created_at, target_role, interview_type,
                    mcq_score, written_score, combined_score, summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            params = (
                str(session_id),
                str(created_at),
                target_role,
                interview_type,
                mcq_score,
                written_score,
                combined_score,
                summary_json,
            )

            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                conn.commit()

            return True

        except Exception as exc:
            logger.error("Error saving session %s: %s", session_id, exc)
            return False

    def get_session(self, session_id: str) -> dict | None:
        """Retrieves a single session record by its ID.

        Args:
            session_id: Session identifier string.

        Returns:
            dict | None: The session dictionary, or None if not found or disabled.
        """
        if not self.enabled or not session_id:
            return None

        try:
            sql = """
                SELECT id, created_at, target_role, interview_type,
                       mcq_score, written_score, combined_score, summary
                FROM sessions
                WHERE id = ?
            """
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (str(session_id),))
                row = cursor.fetchone()

            if not row:
                return None

            summary_data = None
            if row[7]:
                try:
                    summary_data = json.loads(row[7])
                except Exception:
                    summary_data = row[7]

            return {
                "id": row[0],
                "created_at": row[1],
                "target_role": row[2],
                "interview_type": row[3],
                "mcq_score": row[4],
                "written_score": row[5],
                "combined_score": row[6],
                "summary": summary_data,
            }

        except Exception as exc:
            logger.error("Error retrieving session %s: %s", session_id, exc)
            return None

    def get_all_sessions(self) -> list[dict]:
        """Retrieves all stored interview sessions ordered by created_at descending.

        Returns:
            list[dict]: List of session dictionaries, or empty list if disabled/error.
        """
        if not self.enabled:
            return []

        try:
            sql = """
                SELECT id, created_at, target_role, interview_type,
                       mcq_score, written_score, combined_score, summary
                FROM sessions
                ORDER BY created_at DESC
            """
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql)
                rows = cursor.fetchall()

            sessions: list[dict] = []
            for row in rows:
                summary_data = None
                if row[7]:
                    try:
                        summary_data = json.loads(row[7])
                    except Exception:
                        summary_data = row[7]

                sessions.append({
                    "id": row[0],
                    "created_at": row[1],
                    "target_role": row[2],
                    "interview_type": row[3],
                    "mcq_score": row[4],
                    "written_score": row[5],
                    "combined_score": row[6],
                    "summary": summary_data,
                })

            return sessions

        except Exception as exc:
            logger.error("Error retrieving all sessions: %s", exc)
            return []

    def delete_session(self, session_id: str) -> bool:
        """Deletes a specific session by its ID.

        Args:
            session_id: Session identifier string.

        Returns:
            bool: True if deletion succeeded, False otherwise.
        """
        if not self.enabled or not session_id:
            return False

        try:
            sql = "DELETE FROM sessions WHERE id = ?"
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (str(session_id),))
                conn.commit()
                deleted = cursor.rowcount > 0

            return deleted

        except Exception as exc:
            logger.error("Error deleting session %s: %s", session_id, exc)
            return False

    def delete_all_sessions(self) -> bool:
        """Deletes all session records from the database.

        Returns:
            bool: True if all records were cleared, False otherwise.
        """
        if not self.enabled:
            return False

        try:
            sql = "DELETE FROM sessions"
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql)
                conn.commit()

            return True

        except Exception as exc:
            logger.error("Error clearing all sessions: %s", exc)
            return False


def get_session_manager(config: Optional[AppConfig] = None) -> SessionManager:
    """Convenience helper to retrieve a SessionManager configured from AppConfig.

    Args:
        config: Optional AppConfig instance. If omitted, loaded from environment.

    Returns:
        SessionManager: Configured instance.
    """
    if config is None:
        config = get_config()
    return SessionManager(db_path=config.db_path, enabled=config.enable_history)
