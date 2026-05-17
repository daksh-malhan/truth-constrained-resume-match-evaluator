from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from .config import DB_PATH, ensure_dirs


RUN_UPDATE_FIELDS = {
    "job_title",
    "initial_score",
    "projected_final_score",
    "iterations_used",
    "stop_reason",
    "processing_time_ms",
    "llm_calls_count",
    "retrieval_calls_count",
    "average_retrieval_similarity",
    "citations_count",
    "safe_suggestions_count",
    "needs_confirmation_count",
    "unsafe_rejected_count",
    "prompt_injection_detected",
    "status",
    "error_message",
    "final_report_json",
    "config_json",
}

JSON_ROW_TABLES = {
    "citations": ("citation_json", None),
    "suggestions": ("suggestion_json", "id"),
    "requirement_matches": ("match_json", None),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_conn() -> sqlite3.Connection:
    ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                resume_filename TEXT NOT NULL,
                job_title TEXT,
                initial_score REAL,
                projected_final_score REAL,
                threshold REAL NOT NULL,
                iterations_used INTEGER DEFAULT 0,
                stop_reason TEXT,
                processing_time_ms INTEGER,
                llm_calls_count INTEGER DEFAULT 0,
                retrieval_calls_count INTEGER DEFAULT 0,
                average_retrieval_similarity REAL DEFAULT 0,
                citations_count INTEGER DEFAULT 0,
                safe_suggestions_count INTEGER DEFAULT 0,
                needs_confirmation_count INTEGER DEFAULT 0,
                unsafe_rejected_count INTEGER DEFAULT 0,
                prompt_injection_detected INTEGER DEFAULT 0,
                status TEXT NOT NULL,
                error_message TEXT,
                final_report_json TEXT,
                config_json TEXT
            );

            CREATE TABLE IF NOT EXISTS logs (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                event_type TEXT NOT NULL,
                message TEXT NOT NULL,
                duration_ms INTEGER,
                metadata_json TEXT NOT NULL,
                level TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS admin_config (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                config_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS rag_chunks (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                source_type TEXT NOT NULL,
                text TEXT NOT NULL,
                embedding_json TEXT,
                metadata_json TEXT NOT NULL,
                page_number INTEGER,
                section_name TEXT,
                paragraph_index INTEGER,
                chunk_index INTEGER NOT NULL,
                original_text TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS citations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                citation_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS suggestions (
                id TEXT PRIMARY KEY,
                run_id TEXT NOT NULL,
                suggestion_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS requirement_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                match_json TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS score_breakdowns (
                run_id TEXT PRIMARY KEY,
                score_json TEXT NOT NULL
            );
            """
        )


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def insert_run(run_id: str, resume_filename: str, threshold: float, config: Dict[str, Any]) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO runs (run_id, created_at, resume_filename, threshold, status, config_json)
            VALUES (?, ?, ?, ?, 'running', ?)
            """,
            (run_id, utc_now(), resume_filename, threshold, json.dumps(config)),
        )


def update_run(run_id: str, **fields: Any) -> None:
    if not fields:
        return
    unknown = set(fields) - RUN_UPDATE_FIELDS
    if unknown:
        raise ValueError(f"Unsupported run fields: {', '.join(sorted(unknown))}")
    assignments = ", ".join(f"{key} = ?" for key in fields)
    values = [json.dumps(value) if key.endswith("_json") and not isinstance(value, str) else value for key, value in fields.items()]
    values.append(run_id)
    with get_conn() as conn:
        conn.execute(f"UPDATE runs SET {assignments} WHERE run_id = ?", values)


def fetch_run(run_id: str) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    return row_to_dict(row) if row else None


def fetch_runs(limit: int = 50) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [row_to_dict(row) for row in rows]


def insert_log(log: Dict[str, Any]) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO logs (id, run_id, timestamp, event_type, message, duration_ms, metadata_json, level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                log["id"],
                log["run_id"],
                log["timestamp"],
                log["event_type"],
                log["message"],
                log.get("duration_ms"),
                json.dumps(log.get("metadata", {})),
                log.get("level", "info"),
            ),
        )


def fetch_logs(run_id: Optional[str] = None, level: Optional[str] = None, limit: int = 200) -> List[Dict[str, Any]]:
    query = "SELECT * FROM logs"
    clauses: List[str] = []
    params: List[Any] = []
    if run_id:
        clauses.append("run_id = ?")
        params.append(run_id)
    if level:
        clauses.append("level = ?")
        params.append(level)
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    results = []
    for row in rows:
        item = row_to_dict(row)
        item["metadata"] = json.loads(item.pop("metadata_json"))
        results.append(item)
    return results


def save_admin_config(config: Dict[str, Any]) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO admin_config (id, config_json, updated_at)
            VALUES (1, ?, ?)
            ON CONFLICT(id) DO UPDATE SET config_json = excluded.config_json, updated_at = excluded.updated_at
            """,
            (json.dumps(config), utc_now()),
        )


def get_admin_config() -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute("SELECT config_json FROM admin_config WHERE id = 1").fetchone()
    return json.loads(row["config_json"]) if row else None


def reset_admin_config() -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM admin_config WHERE id = 1")


def save_chunks(chunks: Iterable[Dict[str, Any]]) -> None:
    with get_conn() as conn:
        conn.executemany(
            """
            INSERT OR REPLACE INTO rag_chunks
            (id, run_id, source_type, text, embedding_json, metadata_json, page_number, section_name, paragraph_index, chunk_index, original_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    c["id"],
                    c["run_id"],
                    c["source_type"],
                    c["text"],
                    json.dumps(c.get("embedding")),
                    json.dumps(c.get("metadata", {})),
                    c.get("page_number"),
                    c.get("section_name"),
                    c.get("paragraph_index"),
                    c["chunk_index"],
                    c["original_text"],
                )
                for c in chunks
            ],
        )


def fetch_chunks(run_id: str) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM rag_chunks WHERE run_id = ? ORDER BY chunk_index", (run_id,)).fetchall()
    chunks = []
    for row in rows:
        item = row_to_dict(row)
        item["embedding"] = json.loads(item.pop("embedding_json")) if item["embedding_json"] else None
        item["metadata"] = json.loads(item.pop("metadata_json"))
        chunks.append(item)
    return chunks


def save_json_rows(table: str, run_id: str, rows: Iterable[Dict[str, Any]], json_column: str) -> None:
    expected = JSON_ROW_TABLES.get(table)
    if not expected or expected[0] != json_column:
        raise ValueError(f"Unsupported JSON row target: {table}.{json_column}")
    id_column = expected[1]
    with get_conn() as conn:
        for row in rows:
            if id_column:
                conn.execute(f"INSERT OR REPLACE INTO {table} (id, run_id, {json_column}) VALUES (?, ?, ?)", (row["id"], run_id, json.dumps(row)))
            else:
                conn.execute(f"INSERT INTO {table} (run_id, {json_column}) VALUES (?, ?)", (run_id, json.dumps(row)))
