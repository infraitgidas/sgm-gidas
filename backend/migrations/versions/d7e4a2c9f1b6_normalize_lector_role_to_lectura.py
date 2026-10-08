"""normalize lector role to lectura

Revision ID: d7e4a2c9f1b6
Revises: 9823db81d6d2
Create Date: 2026-09-09 15:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "d7e4a2c9f1b6"
down_revision = "9823db81d6d2"
branch_labels = None
depends_on = None


def _role_id(bind, name):
    return bind.execute(
        sa.text("SELECT id FROM rol WHERE nombre = :name"),
        {"name": name},
    ).scalar()


def _normalize_lector_role(bind):
    lector_id = _role_id(bind, "LECTOR")
    lectura_id = _role_id(bind, "LECTURA")

    if lector_id is None:
        return

    if lectura_id is None:
        bind.execute(
            sa.text("UPDATE rol SET nombre = 'LECTURA' WHERE id = :role_id"),
            {"role_id": lector_id},
        )
        return

    canonical_id = lector_id if lector_id == 3 else lectura_id
    duplicate_id = lectura_id if canonical_id == lector_id else lector_id

    bind.execute(
        sa.text("UPDATE usuario SET id_rol = :canonical_id WHERE id_rol = :duplicate_id"),
        {"canonical_id": canonical_id, "duplicate_id": duplicate_id},
    )
    bind.execute(
        sa.text("DELETE FROM rol WHERE id = :duplicate_id"),
        {"duplicate_id": duplicate_id},
    )
    bind.execute(
        sa.text("UPDATE rol SET nombre = 'LECTURA' WHERE id = :canonical_id"),
        {"canonical_id": canonical_id},
    )


def _restore_lector_role(bind):
    lectura_id = _role_id(bind, "LECTURA")
    lector_id = _role_id(bind, "LECTOR")

    if lectura_id is not None and lector_id is None:
        bind.execute(
            sa.text("UPDATE rol SET nombre = 'LECTOR' WHERE id = :role_id"),
            {"role_id": lectura_id},
        )


def upgrade():
    _normalize_lector_role(op.get_bind())


def downgrade():
    _restore_lector_role(op.get_bind())
