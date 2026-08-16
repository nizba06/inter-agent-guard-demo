"""SQLite persistence for analysis runs."""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

from intelbrief.schemas import AgentMessage, RunStatus, RunSummary, SecurityMode


class RunRepository:
    """CRUD for pipeline runs stored in SQLite."""

    def __init__(self, database_url: str) -> None:
        self._path = _sqlite_path(database_url)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    @contextmanager
    def _session(self) -> Iterator[sqlite3.Connection]:
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._session() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    security_mode TEXT NOT NULL,
                    task TEXT NOT NULL,
                    poisoned_source INTEGER NOT NULL,
                    writer_action TEXT,
                    attack_succeeded INTEGER NOT NULL,
                    blocked_reason TEXT,
                    blocked_hop TEXT,
                    messages_json TEXT NOT NULL,
                    audit_log_path TEXT,
                    llm_backend TEXT NOT NULL,
                    llm_model TEXT NOT NULL,
                    agentguard_mode TEXT,
                    error TEXT,
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                )
                """
            )
            self._ensure_column(conn, "attack_scenario", "TEXT NOT NULL DEFAULT 'injection'")
            self._ensure_column(conn, "blocked_layer", "TEXT")

    def _ensure_column(self, conn: sqlite3.Connection, column: str, ddl: str) -> None:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(runs)")}
        if column not in columns:
            conn.execute(f"ALTER TABLE runs ADD COLUMN {column} {ddl}")

    def insert_pending(
        self,
        run_id: uuid.UUID,
        *,
        task: str,
        poisoned_source: bool,
        secured: bool,
        llm_backend: str,
        llm_model: str,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        with self._session() as conn:
            conn.execute(
                """
                INSERT INTO runs (
                    id, status, security_mode, task, poisoned_source,
                    attack_succeeded, messages_json, llm_backend, llm_model, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(run_id),
                    RunStatus.PENDING.value,
                    SecurityMode.SECURED.value if secured else SecurityMode.UNSECURED.value,
                    task,
                    int(poisoned_source),
                    0,
                    "[]",
                    llm_backend,
                    llm_model,
                    now,
                ),
            )

    def finalize(
        self,
        run_id: uuid.UUID,
        *,
        status: RunStatus,
        writer_action: str | None,
        attack_succeeded: bool,
        blocked_reason: str | None,
        blocked_hop: str | None,
        blocked_layer: str | None,
        attack_scenario: str,
        messages: list[AgentMessage],
        audit_log_path: str | None,
        agentguard_mode: str | None,
        error: str | None,
    ) -> None:
        now = datetime.now(UTC).isoformat()
        with self._session() as conn:
            conn.execute(
                """
                UPDATE runs SET
                    status = ?,
                    writer_action = ?,
                    attack_succeeded = ?,
                    blocked_reason = ?,
                    blocked_hop = ?,
                    blocked_layer = ?,
                    attack_scenario = ?,
                    messages_json = ?,
                    audit_log_path = ?,
                    agentguard_mode = ?,
                    error = ?,
                    completed_at = ?
                WHERE id = ?
                """,
                (
                    status.value,
                    writer_action,
                    int(attack_succeeded),
                    blocked_reason,
                    blocked_hop,
                    blocked_layer,
                    attack_scenario,
                    json.dumps([m.model_dump() for m in messages]),
                    audit_log_path,
                    agentguard_mode,
                    error,
                    now,
                    str(run_id),
                ),
            )

    def get(self, run_id: uuid.UUID) -> dict | None:
        with self._session() as conn:
            row = conn.execute("SELECT * FROM runs WHERE id = ?", (str(run_id),)).fetchone()
        if row is None:
            return None
        return _row_to_dict(row)

    def list_recent(self, limit: int = 20) -> list[dict]:
        with self._session() as conn:
            rows = conn.execute(
                "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [_row_to_dict(row) for row in rows]


def _sqlite_path(database_url: str) -> Path:
    prefix = "sqlite:///"
    if database_url.startswith(prefix):
        return Path(database_url.removeprefix(prefix))
    msg = f"Unsupported database URL: {database_url}"
    raise ValueError(msg)


def _row_to_dict(row: sqlite3.Row) -> dict:
    messages = json.loads(row["messages_json"] or "[]")
    return {
        "id": uuid.UUID(row["id"]),
        "status": RunStatus(row["status"]),
        "security_mode": SecurityMode(row["security_mode"]),
        "task": row["task"],
        "poisoned_source": bool(row["poisoned_source"]),
        "writer_action": row["writer_action"],
        "attack_succeeded": bool(row["attack_succeeded"]),
        "blocked_reason": row["blocked_reason"],
        "blocked_hop": row["blocked_hop"],
        "blocked_layer": row["blocked_layer"] if "blocked_layer" in row.keys() else None,
        "attack_scenario": row["attack_scenario"] if "attack_scenario" in row.keys() else "injection",
        "messages": [AgentMessage.model_validate(m) for m in messages],
        "audit_log_path": row["audit_log_path"],
        "llm_backend": row["llm_backend"],
        "llm_model": row["llm_model"],
        "agentguard_mode": row["agentguard_mode"],
        "error": row["error"],
        "created_at": datetime.fromisoformat(row["created_at"]),
        "completed_at": datetime.fromisoformat(row["completed_at"])
        if row["completed_at"]
        else None,
    }


def to_summary(record: dict) -> RunSummary:
    return RunSummary(
        id=record["id"],
        status=record["status"],
        security_mode=record["security_mode"],
        task=record["task"],
        attack_succeeded=record["attack_succeeded"],
        blocked_reason=record["blocked_reason"],
        blocked_layer=record.get("blocked_layer"),
        attack_scenario=record.get("attack_scenario", "injection"),
        created_at=record["created_at"],
    )
