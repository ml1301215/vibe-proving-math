"""SQLite-backed users, sessions, quotas, settings, and chat history."""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional

from .config import auth_cfg

_APP_DIR = Path(__file__).resolve().parent.parent


def _auth_config() -> dict[str, Any]:
    cfg = {
        "mode": "dev",
        "default_user": "dev_user",
        "session_days": 30,
        "default_quota": 50,
        "allow_register": True,
        "database_path": "data/app.db",
    }
    try:
        cfg.update(auth_cfg())
    except Exception:
        pass
    cfg["mode"] = str(cfg.get("mode") or "dev").strip().lower()
    return cfg


def auth_mode() -> str:
    return _auth_config().get("mode", "dev")


def auth_is_dev() -> bool:
    return auth_mode() != "prod"


def _db_path() -> Path:
    raw = str(_auth_config().get("database_path") or "data/app.db").strip()
    path = Path(raw).expanduser()
    if not path.is_absolute():
        path = _APP_DIR / path
    return path


def _now() -> int:
    return int(time.time())


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), 200_000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        algo, salt, digest = stored.split("$", 2)
    except ValueError:
        return False
    if algo != "pbkdf2_sha256":
        return False
    return hmac.compare_digest(_hash_password(password, salt), stored)


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _init_db(conn)
    return conn


def _init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            disabled INTEGER NOT NULL DEFAULT 0,
            quota_limit INTEGER NOT NULL DEFAULT 50,
            quota_used INTEGER NOT NULL DEFAULT 0,
            is_admin INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            expires_at INTEGER NOT NULL,
            created_at INTEGER NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            data_json TEXT NOT NULL DEFAULT '{}',
            updated_at INTEGER NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS chat_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            mode TEXT NOT NULL,
            messages_json TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """
    )
    conn.commit()


def _user_dict(row: sqlite3.Row | None) -> Optional[dict[str, Any]]:
    if row is None:
        return None
    limit = int(row["quota_limit"])
    used = int(row["quota_used"])
    return {
        "id": int(row["id"]),
        "username": row["username"],
        "disabled": bool(row["disabled"]),
        "quota_limit": limit,
        "quota_used": used,
        "quota_remaining": max(0, limit - used),
        "is_admin": bool(row["is_admin"]),
    }


def get_or_create_dev_user() -> dict[str, Any]:
    cfg = _auth_config()
    username = str(cfg.get("default_user") or "dev_user").strip() or "dev_user"
    return create_user(username, secrets.token_urlsafe(18), allow_existing=True)


def create_user(username: str, password: str, *, allow_existing: bool = False) -> dict[str, Any]:
    username = (username or "").strip()
    if not username:
        raise ValueError("username required")
    if len(username) < 3 or len(username) > 64:
        raise ValueError("username must be 3-64 chars")
    if not allow_existing and len(password or "") < 6:
        raise ValueError("password must be at least 6 chars")

    cfg = _auth_config()
    quota = int(cfg.get("default_quota") or 50)
    with _connect() as conn:
        existing = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if existing is not None:
            if allow_existing:
                return _user_dict(existing)  # type: ignore[return-value]
            raise ValueError("username already exists")
        conn.execute(
            "INSERT INTO users (username, password_hash, created_at, quota_limit) VALUES (?, ?, ?, ?)",
            (username, _hash_password(password), _now(), quota),
        )
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return _user_dict(row)  # type: ignore[return-value]


def authenticate_user(username: str, password: str) -> Optional[dict[str, Any]]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", ((username or "").strip(),)).fetchone()
        if row is None or row["disabled"]:
            return None
        if not _verify_password(password or "", row["password_hash"]):
            return None
        return _user_dict(row)


def create_session(user_id: int) -> tuple[str, int]:
    cfg = _auth_config()
    days = max(1, int(cfg.get("session_days") or 30))
    token = secrets.token_urlsafe(32)
    expires = _now() + days * 86400
    with _connect() as conn:
        conn.execute(
            "INSERT INTO sessions (token_hash, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
            (_hash_token(token), int(user_id), expires, _now()),
        )
    return token, expires


def delete_session(token: str) -> None:
    if not token:
        return
    with _connect() as conn:
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_hash_token(token),))


def get_user_by_session(token: str) -> Optional[dict[str, Any]]:
    if not token:
        return None
    with _connect() as conn:
        row = conn.execute(
            """
            SELECT u.* FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ? AND s.expires_at > ?
            """,
            (_hash_token(token), _now()),
        ).fetchone()
        return _user_dict(row)


def consume_quota(user_id: int, amount: int = 1) -> dict[str, Any]:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (int(user_id),)).fetchone()
        if row is None or row["disabled"]:
            raise ValueError("user unavailable")
        limit = int(row["quota_limit"])
        used = int(row["quota_used"])
        if used + amount > limit:
            raise PermissionError("quota exceeded")
        conn.execute("UPDATE users SET quota_used = quota_used + ? WHERE id = ?", (amount, int(user_id)))
        row2 = conn.execute("SELECT * FROM users WHERE id = ?", (int(user_id),)).fetchone()
        return _user_dict(row2)  # type: ignore[return-value]


def get_settings(user_id: int) -> dict[str, Any]:
    with _connect() as conn:
        row = conn.execute("SELECT data_json FROM user_settings WHERE user_id = ?", (int(user_id),)).fetchone()
        if row is None:
            return {}
        try:
            return json.loads(row["data_json"]) or {}
        except Exception:
            return {}


def update_settings(user_id: int, patch: dict[str, Any]) -> dict[str, Any]:
    current = get_settings(user_id)
    for section, values in patch.items():
        if not isinstance(values, dict):
            continue
        section_data = current.get(section)
        if not isinstance(section_data, dict):
            section_data = {}
        section_data.update({k: v for k, v in values.items() if v is not None})
        current[section] = section_data
    payload = json.dumps(current, ensure_ascii=False)
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO user_settings (user_id, data_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET data_json = excluded.data_json, updated_at = excluded.updated_at
            """,
            (int(user_id), payload, _now()),
        )
    return current


def add_chat_session(user_id: int, title: str, mode: str, messages: list[dict[str, Any]]) -> dict[str, Any]:
    ts = _now()
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO chat_sessions (user_id, title, mode, messages_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (int(user_id), title or "chat", mode or "learning", json.dumps(messages, ensure_ascii=False), ts, ts),
        )
        sid = int(cur.lastrowid)
    return {"id": sid, "title": title or "chat", "mode": mode or "learning", "ts": ts * 1000, "messages": messages}


def list_chat_sessions(user_id: int, limit: int = 50) -> list[dict[str, Any]]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM chat_sessions WHERE user_id = ? ORDER BY updated_at DESC LIMIT ?",
            (int(user_id), int(limit)),
        ).fetchall()
    out = []
    for row in rows:
        try:
            messages = json.loads(row["messages_json"]) or []
        except Exception:
            messages = []
        out.append({
            "id": int(row["id"]),
            "title": row["title"],
            "mode": row["mode"],
            "ts": int(row["updated_at"]) * 1000,
            "messages": messages,
        })
    return out


def delete_chat_session(user_id: int, session_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM chat_sessions WHERE user_id = ? AND id = ?", (int(user_id), int(session_id)))


def clear_chat_sessions(user_id: int) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM chat_sessions WHERE user_id = ?", (int(user_id),))
