"""Telling you something happened while you are not looking at the website.

Two ways, both optional:

  * the website itself pops a message up while it is open
  * Telegram sends it to your phone, wherever you are

Telegram is set up entirely from the Settings page: paste a bot token and your
chat id, press Test. Nothing here needs a subscription, an account with us, or
a port open to the internet - the Pi makes an outgoing call, which your router
already allows.

Getting the two numbers, once:
  1. in Telegram, message @BotFather, send /newbot, it gives you the token
  2. message your new bot anything, then open
     https://api.telegram.org/bot<token>/getUpdates and read chat.id
"""
from __future__ import annotations

import json
import threading
import time
import urllib.parse
import urllib.request
from typing import Optional

TIMEOUT = 8


class Notifier:
    def __init__(self, settings, state):
        self.s = settings
        self.state = state
        self._last: dict = {}
        self._lock = threading.Lock()

    # --------------------------------------------------------------- sending
    def send(self, kind: str, text: str, quiet_seconds: float = 120.0) -> None:
        """Send once. The same kind will not be repeated within quiet_seconds."""
        if not self.s.get("notify.on_" + kind, True):
            return
        with self._lock:
            if time.time() - self._last.get(kind, 0) < quiet_seconds:
                return
            self._last[kind] = time.time()
        threading.Thread(target=self._telegram, args=(text,), daemon=True).start()

    def test(self) -> tuple:
        return self._telegram("AR-750: this is a test. If you can read "
                              "this, your rover can reach you.", raise_errors=True)

    # -------------------------------------------------------------- telegram
    def _telegram(self, text: str, raise_errors: bool = False) -> tuple:
        token = str(self.s.get("notify.telegram_token", "") or "").strip()
        chat = str(self.s.get("notify.telegram_chat_id", "") or "").strip()
        if not token or not chat:
            return False, "Telegram is not set up"
        url = "https://api.telegram.org/bot%s/sendMessage" % urllib.parse.quote(token)
        body = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
        try:
            req = urllib.request.Request(url, data=body)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                ok = json.loads(r.read()).get("ok", False)
            return bool(ok), "sent" if ok else "Telegram refused it"
        except Exception as e:                            # network, bad token
            msg = "could not reach Telegram: %s" % e
            if raise_errors:
                return False, msg
            try:
                self.state.say(msg, "warn")
            except Exception:
                pass
            return False, msg
