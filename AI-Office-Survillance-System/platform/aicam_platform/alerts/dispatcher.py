"""Multi-channel alert fan-out: push (FCM), SMS + WhatsApp (Twilio), email (SMTP),
webhook. Includes per-key throttling so a single ongoing incident doesn't spam.

All providers are optional and lazily imported; configure via env. A channel with no
credentials is skipped (logged), never crashes the pipeline.
"""
from __future__ import annotations
import smtplib
import time
from dataclasses import dataclass, field
from email.mime.text import MIMEText
from enum import Enum
from typing import Optional

from ..common.logging import get_logger

log = get_logger("alerts")


class Channel(str, Enum):
    PUSH = "push"
    SMS = "sms"
    WHATSAPP = "whatsapp"
    EMAIL = "email"
    WEBHOOK = "webhook"


@dataclass
class AlertMessage:
    title: str
    body: str
    severity: str = "warning"          # info | warning | critical
    media_url: Optional[str] = None
    data: dict = field(default_factory=dict)


@dataclass
class AlertDispatcher:
    # credentials (inject from settings/secrets)
    twilio_sid: Optional[str] = None
    twilio_token: Optional[str] = None
    twilio_from_sms: Optional[str] = None
    twilio_from_wa: Optional[str] = None
    fcm_credentials_path: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_pass: Optional[str] = None
    webhook_url: Optional[str] = None
    throttle_s: float = 30.0
    _last: dict[str, float] = field(default_factory=dict)

    def _throttled(self, key: str) -> bool:
        now = time.time()
        last = self._last.get(key)
        if last and now - last < self.throttle_s:
            return True
        self._last[key] = now
        return False

    def send(self, msg: AlertMessage, channels: list[Channel], recipients: dict,
             throttle_key: Optional[str] = None) -> dict[str, bool]:
        """recipients example:
        {"sms": ["+1..."], "whatsapp": ["+1..."], "email": ["a@b.com"],
         "push": ["<fcm_token>"], "webhook": True}
        """
        if throttle_key and self._throttled(throttle_key):
            log.info(f"throttled alert '{throttle_key}'")
            return {}
        results: dict[str, bool] = {}
        for ch in channels:
            try:
                if ch == Channel.SMS:
                    results["sms"] = self._twilio(recipients.get("sms", []), msg, wa=False)
                elif ch == Channel.WHATSAPP:
                    results["whatsapp"] = self._twilio(recipients.get("whatsapp", []), msg, wa=True)
                elif ch == Channel.EMAIL:
                    results["email"] = self._email(recipients.get("email", []), msg)
                elif ch == Channel.PUSH:
                    results["push"] = self._fcm(recipients.get("push", []), msg)
                elif ch == Channel.WEBHOOK:
                    results["webhook"] = self._webhook(msg)
            except Exception as e:  # never let alerting crash the pipeline
                log.error(f"channel {ch} failed: {e}")
                results[ch.value] = False
        return results

    # --- providers (lazy, optional) ---
    def _twilio(self, to: list[str], msg: AlertMessage, wa: bool) -> bool:
        if not (self.twilio_sid and self.twilio_token and to):
            log.warning("twilio not configured / no recipients"); return False
        from twilio.rest import Client
        client = Client(self.twilio_sid, self.twilio_token)
        frm = self.twilio_from_wa if wa else self.twilio_from_sms
        for num in to:
            dst = f"whatsapp:{num}" if wa else num
            src = f"whatsapp:{frm}" if wa else frm
            client.messages.create(body=f"[{msg.severity.upper()}] {msg.title}\n{msg.body}",
                                    from_=src, to=dst,
                                    media_url=[msg.media_url] if msg.media_url else None)
        return True

    def _email(self, to: list[str], msg: AlertMessage) -> bool:
        if not (self.smtp_host and self.smtp_user and to):
            log.warning("smtp not configured / no recipients"); return False
        mime = MIMEText(msg.body + (f"\n\nEvidence: {msg.media_url}" if msg.media_url else ""))
        mime["Subject"] = f"[{msg.severity.upper()}] {msg.title}"
        mime["From"] = self.smtp_user
        mime["To"] = ", ".join(to)
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as s:
            s.starttls(); s.login(self.smtp_user, self.smtp_pass)
            s.sendmail(self.smtp_user, to, mime.as_string())
        return True

    def _fcm(self, tokens: list[str], msg: AlertMessage) -> bool:
        if not (self.fcm_credentials_path and tokens):
            log.warning("fcm not configured / no tokens"); return False
        import firebase_admin
        from firebase_admin import credentials, messaging
        if not firebase_admin._apps:
            firebase_admin.initialize_app(credentials.Certificate(self.fcm_credentials_path))
        messaging.send_each([
            messaging.Message(
                notification=messaging.Notification(title=msg.title, body=msg.body),
                data={k: str(v) for k, v in msg.data.items()}, token=t,
            ) for t in tokens
        ])
        return True

    def _webhook(self, msg: AlertMessage) -> bool:
        if not self.webhook_url:
            return False
        import httpx
        httpx.post(self.webhook_url, json=msg.__dict__, timeout=10)
        return True
