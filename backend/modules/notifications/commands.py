import json
import signal
import threading
import time
from pathlib import Path

import click

from extension import db
from modules.notifications.services.email_worker import EmailWorker, purge_notifications, queue_stats
from modules.notifications.services.payload_cipher import cipher
from modules.notifications.services.settings import validate_email_settings
from modules.shared.services.logging_config import get_logger


logger = get_logger(__name__)
HEARTBEAT = Path("/tmp/gidas-email-worker-heartbeat")


def register_email_commands(app):
    @app.cli.command("email-worker")
    @click.option("--once", is_flag=True, help="Procesar un lote y terminar.")
    def email_worker(once):
        validate_email_settings(app.config, required=True)
        cipher()
        stopped = threading.Event()
        for name in (signal.SIGTERM, signal.SIGINT):
            signal.signal(name, lambda *_args: stopped.set())
        worker = EmailWorker()
        last_maintenance = 0
        while not stopped.is_set():
            try:
                for message_id, lease in worker.claim():
                    worker.process(message_id, lease)
                    HEARTBEAT.touch()
                    if stopped.is_set(): break
                if time.monotonic() - last_maintenance > 3600:
                    purge_notifications()
                    stats = queue_stats()
                    if stats["pending_older_than_15_minutes"] or stats["failed"] or stats["pending"] > 100:
                        logger.warning("email_queue_alert counts=%s", json.dumps(stats))
                    last_maintenance = time.monotonic()
                HEARTBEAT.touch()
            except Exception as error:
                db.session.rollback()
                logger.error("email_worker_poll_failed class=%s", type(error).__name__)
                if once: raise click.ClickException("No se pudo procesar la cola de correo.") from None
            finally:
                db.session.remove()
            if once: break
            stopped.wait(app.config["EMAIL_WORKER_POLL_SECONDS"])

    @app.cli.command("purge-email-outbox")
    def purge_email_outbox():
        click.echo(json.dumps(purge_notifications()))

    @app.cli.command("email-queue-stats")
    def email_queue_stats():
        click.echo(json.dumps(queue_stats()))
