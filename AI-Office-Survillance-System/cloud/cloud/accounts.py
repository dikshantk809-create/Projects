#!/usr/bin/env python3
"""Tiny SQLite-backed multi-user account store (shared by edge + cloud).

Real logins: many users, each with their own username + password + role,
grouped under an organisation. Pure standard library (sqlite3 + hashlib).
Passwords stored only as a PBKDF2-SHA256 hash + salt, never plain text.
"""
from __future__ import annotations

import sqlite3
import hashlib
import secrets
import datetime as dt
from contextlib import contextmanager

_PBKDF_ROUNDS = 120_000
ROLES = ("owner", "admin", "manager", "staff")


@contextmanager
def _db(db_path):
    c = sqlite3.connect(db_path, timeout=10)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def _now():
    return dt.datetime.now().isoformat(timespec="seconds")


def _hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256", (password or "").encode("utf-8"),
                               bytes.fromhex(salt), _PBKDF_ROUNDS).hex()


def init_db(db_path):
    with _db(db_path) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS orgs(
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            name    TEXT UNIQUE NOT NULL,
            created TEXT NOT NULL)""")
        c.execute("""CREATE TABLE IF NOT EXISTS users(
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            org_id    INTEGER NOT NULL,
            username  TEXT UNIQUE NOT NULL COLLATE NOCASE,
            pass_hash TEXT NOT NULL,
            salt      TEXT NOT NULL,
            role      TEXT NOT NULL DEFAULT 'staff',
            active    INTEGER NOT NULL DEFAULT 1,
            created   TEXT NOT NULL)""")


def create_org(db_path, name):
    with _db(db_path) as c:
        try:
            cur = c.execute("INSERT INTO orgs(name, created) VALUES(?,?)", (name, _now()))
            return cur.lastrowid
        except sqlite3.IntegrityError:
            r = c.execute("SELECT id FROM orgs WHERE name=?", (name,)).fetchone()
            return r["id"] if r else None


def user_count(db_path):
    with _db(db_path) as c:
        return c.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]


def add_user(db_path, org_id, username, password, role="staff"):
    username = (username or "").strip()
    if not username:
        return False, "Username khaali nahi ho sakta."
    if len(password or "") < 4:
        return False, "Password kam se kam 4 character ka rakho."
    if role not in ROLES:
        role = "staff"
    salt = secrets.token_hex(16)
    ph = _hash(password, salt)
    with _db(db_path) as c:
        try:
            c.execute("""INSERT INTO users(org_id, username, pass_hash, salt, role, active, created)
                         VALUES(?,?,?,?,?,1,?)""", (org_id, username, ph, salt, role, _now()))
            return True, f"User '{username}' add ho gaya."
        except sqlite3.IntegrityError:
            return False, f"'{username}' pehle se hai. Dusra naam chuno."


def ensure_admin(db_path, username, password, org_name="My Office"):
    """First-run: if no users exist, create the org + an OWNER account."""
    init_db(db_path)
    if user_count(db_path) > 0:
        return False
    org_id = create_org(db_path, org_name)
    add_user(db_path, org_id, username, password, role="owner")
    return True


def verify(db_path, username, password):
    with _db(db_path) as c:
        r = c.execute("""SELECT u.*, o.name AS org_name
                         FROM users u JOIN orgs o ON o.id = u.org_id
                         WHERE u.username = ? AND u.active = 1""",
                      ((username or "").strip(),)).fetchone()
    if not r:
        return None
    if secrets.compare_digest(_hash(password, r["salt"]), r["pass_hash"]):
        return {"id": r["id"], "username": r["username"], "role": r["role"],
                "org_id": r["org_id"], "org_name": r["org_name"]}
    return None


def list_users(db_path, org_id):
    with _db(db_path) as c:
        rows = c.execute("""SELECT id, username, role, active, created
                            FROM users WHERE org_id=? ORDER BY id""", (org_id,)).fetchall()
        return [dict(r) for r in rows]


def delete_user(db_path, user_id):
    with _db(db_path) as c:
        c.execute("DELETE FROM users WHERE id=?", (int(user_id),))


def set_active(db_path, user_id, active):
    with _db(db_path) as c:
        c.execute("UPDATE users SET active=? WHERE id=?", (1 if active else 0, int(user_id)))


def change_password(db_path, user_id, new_password):
    if len(new_password or "") < 4:
        return False, "Password kam se kam 4 character ka rakho."
    salt = secrets.token_hex(16)
    ph = _hash(new_password, salt)
    with _db(db_path) as c:
        c.execute("UPDATE users SET pass_hash=?, salt=? WHERE id=?", (ph, salt, int(user_id)))
    return True, "Password badal gaya."
