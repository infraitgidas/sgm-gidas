"""Claim durable antes del I/O; lease y revalidacion impiden envios cancelados."""
import datetime as dt
import uuid

from sqlalchemy import and_, or_

from extension import db
from modules.auth.models.password_reset_request import PasswordResetRequest
from modules.auth.services.password_reset_service import begin_sqlite_write, lock_user
from modules.notifications.models.email_outbox import EmailOutbox
from modules.notifications.services.payload_cipher import decrypt_payload
from modules.notifications.services.smtp_transport import SMTPTransport
from modules.shared.services.logging_config import get_logger


logger = get_logger(__name__)
RETRY_MINUTES = (1, 5, 15, 60, 240)  # Cinco reintentos DESPUES del primer intento.
LEASE_SECONDS = 300


class EmailWorker:
    def __init__(self, transport=None, worker_id=None):
        self.transport = transport or SMTPTransport()
        self.worker_id = worker_id or uuid.uuid4().hex

    def claim(self, limit=20, now=None):
        now = now or dt.datetime.utcnow()
        begin_sqlite_write()
        rows = EmailOutbox.query.filter(or_(
            and_(EmailOutbox.status == "pending", EmailOutbox.next_attempt_at <= now),
            and_(EmailOutbox.status == "processing", EmailOutbox.locked_at < now - dt.timedelta(seconds=LEASE_SECONDS)),
        )).order_by(EmailOutbox.next_attempt_at, EmailOutbox.created_at).limit(min(20, max(1, limit))).with_for_update(skip_locked=True).all()
        claims = []
        for message in rows:
            lease = f"{self.worker_id[:40]}:{uuid.uuid4().hex}"
            message.status = "processing"
            message.locked_by = lease
            message.locked_at = message.updated_at = now
            message.attempt_count += 1
            claims.append((message.id, lease))
        db.session.commit()
        return claims

    def process(self, message_id, lease, now=None):
        fixed_now = now
        # El claim ya esta confirmado. El segundo bloqueo serializa envio,
        # reemplazo y confirmacion por usuario durante el timeout SMTP acotado.
        begin_sqlite_write()
        reset = PasswordResetRequest.query.filter_by(email_message_id=message_id).first()
        user = lock_user(reset.user_id) if reset else None
        if reset:
            reset = PasswordResetRequest.query.filter_by(id=reset.id).populate_existing().with_for_update().first()
        message = EmailOutbox.query.filter_by(id=message_id).populate_existing().with_for_update().first()
        if not message or message.status != "processing" or message.locked_by != lease:
            db.session.rollback()
            return False
        now = now or dt.datetime.utcnow()
        if (not reset or reset.revoked_at or reset.consumed_at or not user or not user.activo or user.deleted_at
                or message.message_type != "password_reset"):
            message.status = "cancelled"
            message.payload_encrypted = None
            message.locked_at = message.locked_by = None
            message.updated_at = now
            if reset and not reset.revoked_at:
                reset.revoked_at = now
            db.session.commit()
            return False
        try:
            self.transport.send(str(message.id), decrypt_payload(message.payload_encrypted))
        except Exception as error:
            now = dt.datetime.utcnow() if fixed_now is None else fixed_now
            message.last_error_class = type(error).__name__[:64]
            message.updated_at = now
            message.locked_at = message.locked_by = None
            if message.attempt_count > len(RETRY_MINUTES):
                message.status = "failed"
                message.failed_at = now
                message.payload_encrypted = None
                reset.revoked_at = now
                logger.error("email_terminal_failure message=%s attempt=%s class=%s", message.id, message.attempt_count, message.last_error_class)
            else:
                message.status = "pending"
                message.next_attempt_at = now + dt.timedelta(minutes=RETRY_MINUTES[message.attempt_count - 1])
                logger.warning("email_retry message=%s attempt=%s class=%s", message.id, message.attempt_count, message.last_error_class)
            db.session.commit()
            return False
        # La vigencia comienza cuando SMTP acepta el mensaje, no al encolarlo.
        accepted_at = dt.datetime.utcnow() if fixed_now is None else fixed_now
        message.status = "sent"
        message.sent_at = message.updated_at = accepted_at
        message.payload_encrypted = None
        message.locked_at = message.locked_by = None
        message.last_error_class = None
        reset.activated_at = accepted_at
        reset.expires_at = accepted_at + dt.timedelta(minutes=30)
        db.session.commit()
        logger.info("email_sent message=%s attempt=%s", message_id, message.attempt_count)
        return True

    def run_once(self):
        claims = self.claim()
        for message_id, lease in claims:
            try:
                self.process(message_id, lease)
            except Exception as error:
                db.session.rollback()
                logger.error("email_processing_error message=%s class=%s", message_id, type(error).__name__)
                # Ante un fallo de transaccion el lease permite recuperar el trabajo.
        return len(claims)


def purge_notifications(now=None):
    now = now or dt.datetime.utcnow()
    cutoff = now - dt.timedelta(days=30)
    reset_count = PasswordResetRequest.query.filter(or_(
        PasswordResetRequest.consumed_at < cutoff, PasswordResetRequest.revoked_at < cutoff,
        PasswordResetRequest.expires_at < cutoff,
    )).delete(synchronize_session=False)
    message_count = EmailOutbox.query.filter(or_(
        and_(EmailOutbox.status == "sent", EmailOutbox.sent_at < now - dt.timedelta(days=7)),
        and_(EmailOutbox.status.in_(("failed", "cancelled")), EmailOutbox.updated_at < cutoff),
    )).delete(synchronize_session=False)
    db.session.commit()
    return {"requests_deleted": reset_count, "messages_deleted": message_count}


def queue_stats(now=None):
    now = now or dt.datetime.utcnow()
    pending = EmailOutbox.query.filter_by(status="pending")
    return {
        "pending": pending.count(),
        "pending_older_than_15_minutes": pending.filter(EmailOutbox.created_at < now - dt.timedelta(minutes=15)).count(),
        "retrying": pending.filter(EmailOutbox.attempt_count > 0).count(),
        "processing": EmailOutbox.query.filter_by(status="processing").count(),
        "failed": EmailOutbox.query.filter_by(status="failed").count(),
    }
