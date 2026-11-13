import smtplib
import ssl
from email.message import EmailMessage
from typing import Protocol

from flask import current_app


class EmailTransport(Protocol):
    def send(self, message_id: str, payload: dict) -> None: ...


class SMTPTransport:
    def send(self, message_id: str, payload: dict) -> None:
        cfg = current_app.config
        message = EmailMessage()
        message["From"] = cfg["MAIL_DEFAULT_SENDER"]
        message["To"] = payload["to"]
        message["Subject"] = payload["subject"]
        message["Message-ID"] = f"<{message_id}@gidas>"
        message.set_content(payload["text"])
        message.add_alternative(payload["html"], subtype="html")
        mode = cfg["SMTP_TLS_MODE"]
        context = ssl.create_default_context()
        factory = smtplib.SMTP_SSL if mode == "ssl" else smtplib.SMTP
        options = {"timeout": cfg["SMTP_TIMEOUT_SECONDS"]}
        if mode == "ssl": options["context"] = context
        with factory(cfg["MAIL_SERVER"], cfg["MAIL_PORT"], **options) as smtp:
            smtp.ehlo()
            if mode == "starttls":
                smtp.starttls(context=context)
                smtp.ehlo()
            if cfg.get("MAIL_USERNAME"):
                smtp.login(cfg["MAIL_USERNAME"], cfg.get("MAIL_PASSWORD") or "")
            refused = smtp.send_message(message)
            if refused:
                raise smtplib.SMTPRecipientsRefused(refused)
