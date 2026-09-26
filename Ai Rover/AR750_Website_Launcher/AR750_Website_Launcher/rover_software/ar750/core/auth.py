"""Who is allowed in. Username and password, changed from the website.

You never edit a file to change your password. Sign in, open Settings, change it.

How it is stored: the password itself is never written down anywhere. What gets
saved is a PBKDF2-SHA256 hash with a random salt, which cannot be turned back
into your password. If someone steals data/users.json they still cannot sign in.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from typing import Dict, Optional, Tuple

ITERATIONS = 240_000
SESSION_HOURS = 24 * 14          # stay signed in for two weeks
MAX_TRIES = 6                    # then that address waits
LOCK_SECONDS = 120

FIRST_USER = "admin"
FIRST_PASSWORD = "agrirover"     # must be changed at the first sign in


def _hash(password: str, salt: bytes) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return base64.b64encode(dk).decode("ascii")


class Auth:
    def __init__(self, path: str):
        self.path = path
        self._lock = threading.RLock()
        self.users: Dict[str, dict] = {}
        self.sessions: Dict[str, dict] = {}
        self._tries: Dict[str, list] = {}
        self._load()

    # ------------------------------------------------------------------ disk
    def _load(self) -> None:
        try:
            with open(self.path, encoding="utf-8") as f:
                self.users = json.load(f)
        except (OSError, ValueError):
            self.users = {}
        if not self.users:
            self.add_user(FIRST_USER, FIRST_PASSWORD, must_change=True)

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.users, f, indent=2)
        os.replace(tmp, self.path)
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass

    # ----------------------------------------------------------------- users
    def add_user(self, name: str, password: str, must_change: bool = False) -> None:
        salt = secrets.token_bytes(16)
        with self._lock:
            self.users[name.strip().lower()] = {
                "name": name.strip(),
                "salt": base64.b64encode(salt).decode("ascii"),
                "hash": _hash(password, salt),
                "must_change": bool(must_change),
                "made": time.time(),
            }
            self._save()

    def is_first_run(self) -> bool:
        u = self.users.get(FIRST_USER)
        return bool(u and u.get("must_change"))

    def check_password(self, name: str, password: str) -> bool:
        u = self.users.get((name or "").strip().lower())
        if not u:
            # take the same time as a real check so you cannot tell from the
            # delay whether the username exists
            _hash(password or "", b"0" * 16)
            return False
        salt = base64.b64decode(u["salt"])
        return hmac.compare_digest(_hash(password or "", salt), u["hash"])

    def change(self, name: str, old: str, new: str,
               new_name: str = "") -> Tuple[bool, str]:
        key = (name or "").strip().lower()
        if key not in self.users:
            return False, "no such user"
        if not self.check_password(name, old):
            return False, "the current password is wrong"
        if len(new or "") < 6:
            return False, "the new password needs at least 6 characters"
        if new == FIRST_PASSWORD:
            return False, "pick something other than the one it came with"

        wanted = (new_name or name).strip()
        if not wanted or len(wanted) > 40 or "/" in wanted:
            return False, "that username will not work"
        newkey = wanted.lower()
        if newkey != key and newkey in self.users:
            return False, "that username is taken"

        salt = secrets.token_bytes(16)
        with self._lock:
            rec = self.users.pop(key)
            rec.update(name=wanted,
                       salt=base64.b64encode(salt).decode("ascii"),
                       hash=_hash(new, salt), must_change=False,
                       changed=time.time())
            self.users[newkey] = rec
            # anyone signed in as the old name has to sign in again
            for tok, s in list(self.sessions.items()):
                if s["user"] == key:
                    self.sessions.pop(tok, None)
            self._save()
        return True, "changed"

    # -------------------------------------------------------------- sessions
    def rate_limited(self, who: str) -> int:
        """Seconds this address still has to wait, 0 if it may try."""
        now = time.time()
        tries = [t for t in self._tries.get(who, []) if now - t < LOCK_SECONDS]
        self._tries[who] = tries
        if len(tries) >= MAX_TRIES:
            return int(LOCK_SECONDS - (now - tries[0])) + 1
        return 0

    def note_failure(self, who: str) -> None:
        self._tries.setdefault(who, []).append(time.time())

    def login(self, name: str, password: str, who: str = "") -> Optional[str]:
        wait = self.rate_limited(who)
        if wait:
            return None
        if not self.check_password(name, password):
            self.note_failure(who)
            return None
        self._tries.pop(who, None)
        token = secrets.token_urlsafe(32)
        with self._lock:
            self.sessions[token] = {"user": (name or "").strip().lower(),
                                    "made": time.time(),
                                    "seen": time.time()}
        return token

    def user_for(self, token: str) -> Optional[dict]:
        if not token:
            return None
        s = self.sessions.get(token)
        if not s:
            return None
        if time.time() - s["made"] > SESSION_HOURS * 3600:
            self.sessions.pop(token, None)
            return None
        s["seen"] = time.time()
        u = self.users.get(s["user"])
        if not u:
            return None
        return {"name": u.get("name", s["user"]),
                "must_change": bool(u.get("must_change"))}

    def logout(self, token: str) -> None:
        self.sessions.pop(token or "", None)
