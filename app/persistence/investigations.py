import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

from app.schemas.investigations import InvestigationResponse


class InvestigationNotFoundError(KeyError):
    pass


@dataclass(frozen=True)
class InvestigationRecord:
    investigation_id: str
    request_id: str | None
    route: str | None
    status: str
    service_name: str | None
    checkpoint_thread_id: str
    response: dict[str, Any]
    state: dict[str, Any]
    created_at: str
    updated_at: str


class InvestigationRepository(Protocol):
    def save_completed_investigation(
        self,
        *,
        state: dict[str, Any],
        response: InvestigationResponse,
        checkpoint_thread_id: str,
    ) -> None:
        ...

    def get_investigation(self, investigation_id: str) -> InvestigationRecord:
        ...

    def get_response(self, investigation_id: str) -> InvestigationResponse:
        ...


class SQLiteInvestigationRepository:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def save_completed_investigation(
        self,
        *,
        state: dict[str, Any],
        response: InvestigationResponse,
        checkpoint_thread_id: str,
    ) -> None:
        now = _utc_now()
        response_data = response.model_dump(mode="json")
        state_data = _jsonable(state)
        with self._connect() as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute(
                """
                INSERT INTO investigations (
                    investigation_id,
                    request_id,
                    route,
                    status,
                    service_name,
                    checkpoint_thread_id,
                    response_json,
                    state_json,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(investigation_id) DO UPDATE SET
                    request_id = excluded.request_id,
                    route = excluded.route,
                    status = excluded.status,
                    service_name = excluded.service_name,
                    checkpoint_thread_id = excluded.checkpoint_thread_id,
                    response_json = excluded.response_json,
                    state_json = excluded.state_json,
                    updated_at = excluded.updated_at
                """,
                (
                    response.investigation_id,
                    response.request_id,
                    getattr(response.route, "value", response.route),
                    response.status,
                    response.service_name,
                    checkpoint_thread_id,
                    json.dumps(response_data, sort_keys=True),
                    json.dumps(state_data, sort_keys=True),
                    now,
                    now,
                ),
            )
            connection.execute(
                "DELETE FROM tool_calls WHERE investigation_id = ?",
                (response.investigation_id,),
            )
            connection.execute(
                "DELETE FROM subagent_results WHERE investigation_id = ?",
                (response.investigation_id,),
            )
            connection.execute(
                "DELETE FROM handoff_events WHERE investigation_id = ?",
                (response.investigation_id,),
            )
            self._insert_subagent_results(connection, state_data, response, now)
            self._insert_tool_calls(connection, state_data, response, now)
            self._insert_handoff_event(connection, state_data, response, now)

    def get_investigation(self, investigation_id: str) -> InvestigationRecord:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT investigation_id, request_id, route, status, service_name,
                       checkpoint_thread_id, response_json, state_json, created_at, updated_at
                FROM investigations
                WHERE investigation_id = ?
                """,
                (investigation_id,),
            ).fetchone()
        if row is None:
            raise InvestigationNotFoundError(investigation_id)
        return InvestigationRecord(
            investigation_id=row["investigation_id"],
            request_id=row["request_id"],
            route=row["route"],
            status=row["status"],
            service_name=row["service_name"],
            checkpoint_thread_id=row["checkpoint_thread_id"],
            response=json.loads(row["response_json"]),
            state=json.loads(row["state_json"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def get_response(self, investigation_id: str) -> InvestigationResponse:
        record = self.get_investigation(investigation_id)
        return InvestigationResponse.model_validate(record.response)

    def list_tool_calls(self, investigation_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT agent, tool_name, source_type, source_id, location,
                       input_json, output_json, created_at
                FROM tool_calls
                WHERE investigation_id = ?
                ORDER BY id
                """,
                (investigation_id,),
            ).fetchall()
        return [_row_to_json(row, ["input_json", "output_json"]) for row in rows]

    def list_subagent_results(self, investigation_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT agent, result_json, created_at
                FROM subagent_results
                WHERE investigation_id = ?
                ORDER BY id
                """,
                (investigation_id,),
            ).fetchall()
        return [_row_to_json(row, ["result_json"]) for row in rows]

    def list_handoff_events(self, investigation_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT previous_active_agent, target_agent, reason, event_timestamp,
                       decision_json, result_json, created_at
                FROM handoff_events
                WHERE investigation_id = ?
                ORDER BY id
                """,
                (investigation_id,),
            ).fetchall()
        return [_row_to_json(row, ["decision_json", "result_json"]) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS investigations (
                    investigation_id TEXT PRIMARY KEY,
                    request_id TEXT,
                    route TEXT,
                    status TEXT NOT NULL,
                    service_name TEXT,
                    checkpoint_thread_id TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    state_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS tool_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    investigation_id TEXT NOT NULL REFERENCES investigations(investigation_id) ON DELETE CASCADE,
                    request_id TEXT,
                    agent TEXT NOT NULL,
                    tool_name TEXT NOT NULL,
                    source_type TEXT,
                    source_id TEXT,
                    location TEXT,
                    input_json TEXT NOT NULL,
                    output_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS subagent_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    investigation_id TEXT NOT NULL REFERENCES investigations(investigation_id) ON DELETE CASCADE,
                    request_id TEXT,
                    agent TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS handoff_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    investigation_id TEXT NOT NULL REFERENCES investigations(investigation_id) ON DELETE CASCADE,
                    request_id TEXT,
                    previous_active_agent TEXT,
                    target_agent TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    event_timestamp TEXT,
                    decision_json TEXT NOT NULL,
                    result_json TEXT,
                    created_at TEXT NOT NULL
                );
                """
            )

    def _insert_subagent_results(
        self,
        connection: sqlite3.Connection,
        state: dict[str, Any],
        response: InvestigationResponse,
        created_at: str,
    ) -> None:
        rows = [
            (
                response.investigation_id,
                response.request_id,
                finding.get("agent", "unknown"),
                json.dumps(finding, sort_keys=True),
                created_at,
            )
            for finding in state.get("specialist_findings", [])
        ]
        connection.executemany(
            """
            INSERT INTO subagent_results (
                investigation_id, request_id, agent, result_json, created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            rows,
        )

    def _insert_tool_calls(
        self,
        connection: sqlite3.Connection,
        state: dict[str, Any],
        response: InvestigationResponse,
        created_at: str,
    ) -> None:
        rows = []
        for finding in state.get("specialist_findings", []):
            agent = finding.get("agent", "unknown")
            tool_names = finding.get("skills_used") or [_fallback_tool_name(agent)]
            evidence_items = finding.get("evidence") or [{}]
            for tool_name in tool_names:
                for evidence in evidence_items:
                    rows.append(
                        (
                            response.investigation_id,
                            response.request_id,
                            agent,
                            tool_name,
                            evidence.get("source_type"),
                            evidence.get("source_id"),
                            evidence.get("location"),
                            json.dumps(
                                {
                                    "service_name": state.get("service_name"),
                                    "environment": state.get("environment"),
                                    "incident_id": state.get("incident_id"),
                                    "deployment_id": state.get("deployment_id"),
                                },
                                sort_keys=True,
                            ),
                            json.dumps(evidence, sort_keys=True),
                            created_at,
                        )
                    )
        connection.executemany(
            """
            INSERT INTO tool_calls (
                investigation_id, request_id, agent, tool_name, source_type,
                source_id, location, input_json, output_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

    def _insert_handoff_event(
        self,
        connection: sqlite3.Connection,
        state: dict[str, Any],
        response: InvestigationResponse,
        created_at: str,
    ) -> None:
        decision = state.get("handoff_decision")
        target = state.get("handoff_target")
        reason = state.get("handoff_reason")
        if not decision or not target or not reason:
            return
        connection.execute(
            """
            INSERT INTO handoff_events (
                investigation_id, request_id, previous_active_agent, target_agent,
                reason, event_timestamp, decision_json, result_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                response.investigation_id,
                response.request_id,
                state.get("previous_active_agent"),
                target,
                reason,
                state.get("handoff_timestamp"),
                json.dumps(decision, sort_keys=True),
                json.dumps(state.get("specialist_result"), sort_keys=True),
                created_at,
            ),
        )


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _jsonable(value: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(value, default=str))


def _fallback_tool_name(agent: str) -> str:
    return {
        "metrics_analysis": "get_metrics",
        "log_analysis": "search_logs",
        "deployment_analysis": "get_recent_deployments",
        "runbook_analysis": "search_runbooks",
    }.get(agent, "unknown_tool")


def _row_to_json(row: sqlite3.Row, json_fields: list[str]) -> dict[str, Any]:
    data = dict(row)
    for field in json_fields:
        data[field] = json.loads(data[field]) if data[field] is not None else None
    return data
