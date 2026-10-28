# -*- coding: utf-8 -*-
"""
Lightweight SQLite persistence layer for Knowledge Ocean.
Stores tasks, rate limiting, and execution states reliably across restarts.
"""

import os
import sqlite3
import json
import time
import threading
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

# Baghdad timezone is UTC+3 (Arabia Standard Time, no DST)
BAGHDAD_TZ = timezone(timedelta(hours=3))

def get_baghdad_now() -> datetime:
    """Returns current datetime in Baghdad timezone (UTC+3)."""
    return datetime.now(timezone.utc).astimezone(BAGHDAD_TZ)

def get_baghdad_today() -> str:
    """
    Returns current date string (YYYY-MM-DD) in Baghdad time (UTC+3).
    Automatically rolls over at 12:00 AM (midnight) Baghdad time.
    """
    return get_baghdad_now().strftime("%Y-%m-%d")

DB_PATH = os.path.join(os.environ.get("DOWNLOAD_DIR", "downloads"), "knowledge_ocean.db")
_db_lock = threading.Lock()

def _get_connection():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    with _db_lock:
        conn = _get_connection()
        try:
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS tasks (
                        task_id TEXT PRIMARY KEY,
                        status TEXT,
                        progress INTEGER DEFAULT 0,
                        message TEXT,
                        data_json TEXT,
                        created_at REAL,
                        updated_at REAL
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS usage (
                        key TEXT PRIMARY KEY,
                        day TEXT,
                        papers_count INTEGER DEFAULT 0,
                        updated_at REAL
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS auth_security (
                        ip TEXT PRIMARY KEY,
                        failed_attempts INTEGER DEFAULT 0,
                        banned_until REAL DEFAULT 0,
                        last_attempt REAL DEFAULT 0
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_auth_banned ON auth_security(banned_until);")
        finally:
            conn.close()

def db_set_task(task_id: str, **kwargs):
    now = time.time()
    with _db_lock:
        conn = _get_connection()
        try:
            with conn:
                cur = conn.cursor()
                cur.execute("SELECT data_json FROM tasks WHERE task_id = ?", (task_id,))
                row = cur.fetchone()
                existing = json.loads(row[0]) if row and row[0] else {}
                existing.update(kwargs)
                status = existing.get("status", "queued")
                progress = existing.get("progress", 0)
                message = existing.get("message", "")

                cur.execute("""
                    INSERT INTO tasks (task_id, status, progress, message, data_json, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(task_id) DO UPDATE SET
                        status = excluded.status,
                        progress = excluded.progress,
                        message = excluded.message,
                        data_json = excluded.data_json,
                        updated_at = excluded.updated_at
                """, (task_id, status, progress, message, json.dumps(existing, ensure_ascii=False), now, now))
        finally:
            conn.close()

def db_get_task(task_id: str) -> Optional[Dict[str, Any]]:
    with _db_lock:
        conn = _get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT data_json FROM tasks WHERE task_id = ?", (task_id,))
            row = cur.fetchone()
            if row and row[0]:
                return json.loads(row[0])
            return None
        finally:
            conn.close()

def db_get_tasks_for_guest(guest_token: str = "", user_hashes: Optional[list] = None) -> list:
    """
    Retrieves completed task records strictly matching a guest's unique token or user hashes.
    Guarantees strict isolation so users sharing an IP or network never see each other's files.
    """
    hashes_set = set(user_hashes or [])
    results = []
    with _db_lock:
        conn = _get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT task_id, status, data_json, updated_at FROM tasks WHERE status = 'completed' ORDER BY updated_at DESC")
            rows = cur.fetchall()
            for r in rows:
                if not r[2]:
                    continue
                try:
                    data = json.loads(r[2])
                except Exception:
                    continue
                
                t_token = data.get("guest_token", "")
                t_uh = data.get("user_hash", "")
                
                # Strict isolation: Match ONLY by unique guest token or specific user hashes
                if (guest_token and t_token == guest_token) or (t_uh and t_uh in hashes_set):
                    if "task_id" not in data:
                        data["task_id"] = r[0]
                    results.append(data)
        finally:
            conn.close()
    return results

def db_check_rate_limit(key: str, today: str, requested: int, limit: int) -> tuple[bool, int]:
    now = time.time()
    with _db_lock:
        conn = _get_connection()
        try:
            with conn:
                cur = conn.cursor()
                cur.execute("SELECT day, papers_count FROM usage WHERE key = ?", (key,))
                row = cur.fetchone()
                current_count = 0
                if row:
                    db_day, db_count = row[0], row[1]
                    if db_day == today:
                        current_count = db_count
                    else:
                        # Reset for new day
                        current_count = 0

                if current_count + requested > limit:
                    remaining = max(0, limit - current_count)
                    return True, remaining

                new_count = current_count + requested
                cur.execute("""
                    INSERT INTO usage (key, day, papers_count, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        day = excluded.day,
                        papers_count = excluded.papers_count,
                        updated_at = excluded.updated_at
                """, (key, today, new_count, now))
                return False, max(0, limit - new_count)
        finally:
            conn.close()


def db_get_remaining_quota(key: str, today: str, limit: int) -> int:
    """Returns remaining quota for key on given day without incrementing."""
    with _db_lock:
        conn = _get_connection()
        try:
            with conn:
                cur = conn.cursor()
                cur.execute("SELECT day, papers_count FROM usage WHERE key = ?", (key,))
                row = cur.fetchone()
                if row and row[0] == today:
                    return max(0, limit - row[1])
                return limit
        finally:
            conn.close()


def db_refund_quota(keys: list[str], today: str, refund_amount: int) -> None:
    """Refunds unused quota units back to usage table."""
    if refund_amount <= 0:
        return
    now = time.time()
    with _db_lock:
        conn = _get_connection()
        try:
            with conn:
                cur = conn.cursor()
                for key in keys:
                    cur.execute("SELECT day, papers_count FROM usage WHERE key = ?", (key,))
                    row = cur.fetchone()
                    if row and row[0] == today:
                        new_count = max(0, row[1] - refund_amount)
                        cur.execute("UPDATE usage SET papers_count = ?, updated_at = ? WHERE key = ?", (new_count, now, key))
        finally:
            conn.close()


def db_reset_quota(keys: list[str], today: str) -> None:
    """Resets usage counts for given keys back to 0 on today (used for auto-renewing secondary password)."""
    now = time.time()
    with _db_lock:
        conn = _get_connection()
        try:
            with conn:
                cur = conn.cursor()
                for key in keys:
                    cur.execute("""
                        INSERT INTO usage (key, day, papers_count, updated_at)
                        VALUES (?, ?, 0, ?)
                        ON CONFLICT(key) DO UPDATE SET
                            day = excluded.day,
                            papers_count = 0,
                            updated_at = excluded.updated_at
                    """, (key, today, now))
        finally:
            conn.close()


def db_cleanup_old_usage(keep_days: int = 7) -> int:
    """Deletes usage records older than keep_days to maintain optimal database performance."""
    cutoff = time.time() - (keep_days * 86400)
    with _db_lock:
        conn = _get_connection()
        try:
            with conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM usage WHERE updated_at < ?", (cutoff,))
                return cur.rowcount
        except Exception:
            return 0
        finally:
            conn.close()


def save_task(task_id: str, data: Dict[str, Any]):
    """Alias for saving task dict to database."""
    db_set_task(task_id, **data)


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    """Alias for retrieving task dict from database."""
    return db_get_task(task_id)


def record_usage(key: str, today: Optional[str] = None, requested: int = 1) -> int:
    """Increments and returns current usage count."""
    if not today:
        today = get_baghdad_today()
    now = time.time()
    with _db_lock:
        conn = _get_connection()
        try:
            with conn:
                cur = conn.cursor()
                cur.execute("SELECT day, papers_count FROM usage WHERE key = ?", (key,))
                row = cur.fetchone()
                current_count = 0
                if row:
                    db_day, db_count = row[0], row[1]
                    if db_day == today:
                        current_count = db_count
                new_count = current_count + requested
                cur.execute("""
                    INSERT INTO usage (key, day, papers_count, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        day = excluded.day,
                        papers_count = excluded.papers_count,
                        updated_at = excluded.updated_at
                """, (key, today, new_count, now))
                return new_count
        finally:
            conn.close()


def get_usage_count(key: str, today: Optional[str] = None) -> int:
    """Returns current usage count for the given key and day."""
    if not today:
        today = get_baghdad_today()
    with _db_lock:
        conn = _get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT day, papers_count FROM usage WHERE key = ?", (key,))
            row = cur.fetchone()
            if row and row[0] == today:
                return row[1]
            return 0
        finally:
            conn.close()


MAX_FAILED_AUTH_ATTEMPTS = 5
AUTH_BAN_DURATION_SECONDS = 24 * 3600  # 24 hours (86400s)


def db_check_ip_ban(ip: str) -> tuple[bool, float]:
    """
    Checks whether an IP address is currently banned.
    Returns (is_banned, remaining_seconds).
    If ban expired, resets the ban state and returns (False, 0.0).
    """
    if not ip:
        return False, 0.0
    now = time.time()
    with _db_lock:
        conn = _get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT failed_attempts, banned_until FROM auth_security WHERE ip = ?", (ip,))
            row = cur.fetchone()
            if not row:
                return False, 0.0
            failed_attempts, banned_until = row[0], row[1]
            if banned_until > now:
                return True, (banned_until - now)
            # If ban expired, clean up state
            if banned_until > 0 and banned_until <= now:
                with conn:
                    cur.execute("UPDATE auth_security SET failed_attempts = 0, banned_until = 0 WHERE ip = ?", (ip,))
            return False, 0.0
        finally:
            conn.close()


def db_record_auth_attempt(ip: str, success: bool) -> tuple[bool, int, float]:
    """
    Records an authentication attempt for a given IP address.
    Returns (is_banned, attempts_left, remaining_ban_seconds).
    - If success: resets failed attempts and banned_until to 0. Returns (False, MAX_FAILED_AUTH_ATTEMPTS, 0.0).
    - If failure: increments failed attempts. If >= 5, bans IP for 24 hours.
    """
    if not ip:
        return False, MAX_FAILED_AUTH_ATTEMPTS, 0.0
    now = time.time()
    with _db_lock:
        conn = _get_connection()
        try:
            with conn:
                cur = conn.cursor()
                cur.execute("SELECT failed_attempts, banned_until FROM auth_security WHERE ip = ?", (ip,))
                row = cur.fetchone()

                if row:
                    failed_attempts, banned_until = row[0], row[1]
                    if banned_until > now:
                        return True, 0, (banned_until - now)
                else:
                    failed_attempts, banned_until = 0, 0

                if success:
                    cur.execute("""
                        INSERT INTO auth_security (ip, failed_attempts, banned_until, last_attempt)
                        VALUES (?, 0, 0, ?)
                        ON CONFLICT(ip) DO UPDATE SET
                            failed_attempts = 0,
                            banned_until = 0,
                            last_attempt = excluded.last_attempt
                    """, (ip, now))
                    return False, MAX_FAILED_AUTH_ATTEMPTS, 0.0
                else:
                    # Failure
                    new_failed = failed_attempts + 1
                    if new_failed >= MAX_FAILED_AUTH_ATTEMPTS:
                        new_banned_until = now + AUTH_BAN_DURATION_SECONDS
                        cur.execute("""
                            INSERT INTO auth_security (ip, failed_attempts, banned_until, last_attempt)
                            VALUES (?, ?, ?, ?)
                            ON CONFLICT(ip) DO UPDATE SET
                                failed_attempts = excluded.failed_attempts,
                                banned_until = excluded.banned_until,
                                last_attempt = excluded.last_attempt
                        """, (ip, new_failed, new_banned_until, now))
                        return True, 0, float(AUTH_BAN_DURATION_SECONDS)
                    else:
                        cur.execute("""
                            INSERT INTO auth_security (ip, failed_attempts, banned_until, last_attempt)
                            VALUES (?, ?, 0, ?)
                            ON CONFLICT(ip) DO UPDATE SET
                                failed_attempts = excluded.failed_attempts,
                                banned_until = 0,
                                last_attempt = excluded.last_attempt
                        """, (ip, new_failed, now))
                        return False, max(0, MAX_FAILED_AUTH_ATTEMPTS - new_failed), 0.0
        finally:
            conn.close()


def db_reset_ip_ban(ip: str):
    """Manually resets IP ban and failed attempts."""
    with _db_lock:
        conn = _get_connection()
        try:
            with conn:
                cur = conn.cursor()
                cur.execute("DELETE FROM auth_security WHERE ip = ?", (ip,))
        finally:
            conn.close()


# Ensure tables exist on import
try:
    init_db()
except Exception:
    pass


