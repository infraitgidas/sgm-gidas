"""Introduce el esquema de movimientos financieros.

Revision ID: e3a7d9b2c4f1
Revises: d8f3a6c1b5e2
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime


revision = "e3a7d9b2c4f1"
down_revision = "d8f3a6c1b5e2"
branch_labels = None
depends_on = None


def upgrade():
    categoria_table = op.create_table(
        "categoria_erogacion",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("codigo", sa.String(length=20), nullable=False, unique=True),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("deleted_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["usuario.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["usuario.id"]),
        sa.ForeignKeyConstraint(["deleted_by"], ["usuario.id"]),
    )
    now = datetime.utcnow()
    op.bulk_insert(categoria_table, [
        {"codigo": "CORRIENTE", "nombre": "Corriente", "created_at": now, "activo": True},
        {"codigo": "CAPITAL", "nombre": "Capital", "created_at": now, "activo": True},
    ])
    op.create_table(
        "movimiento_financiero",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("grupo_utn_id", sa.Integer(), nullable=False),
        sa.Column("numero_movimiento", sa.Integer(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("tipo_movimiento", sa.String(length=7), nullable=False),
        sa.Column("monto", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("moneda", sa.String(length=3), nullable=False),
        sa.Column("fuente_financiamiento_id", sa.Integer(), nullable=True),
        sa.Column("categoria_erogacion_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("deleted_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["grupo_utn_id"], ["grupo_utn.id"]),
        sa.ForeignKeyConstraint(["fuente_financiamiento_id"], ["fuente_financiamiento.id"]),
        sa.ForeignKeyConstraint(["categoria_erogacion_id"], ["categoria_erogacion.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["usuario.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["usuario.id"]),
        sa.ForeignKeyConstraint(["deleted_by"], ["usuario.id"]),
        sa.UniqueConstraint("grupo_utn_id", "numero_movimiento", name="uq_movimiento_numero_grupo"),
        sa.CheckConstraint("tipo_movimiento IN ('INGRESO', 'EGRESO')", name="ck_movimiento_tipo"),
        sa.CheckConstraint("monto > 0", name="ck_movimiento_monto_positivo"),
        sa.CheckConstraint("moneda IN ('ARS', 'USD')", name="ck_movimiento_moneda"),
        sa.CheckConstraint("numero_movimiento > 0", name="ck_movimiento_numero_positivo"),
        sa.CheckConstraint(
            "(tipo_movimiento = 'INGRESO' AND fuente_financiamiento_id IS NOT NULL "
            "AND categoria_erogacion_id IS NULL) OR "
            "(tipo_movimiento = 'EGRESO' AND categoria_erogacion_id IS NOT NULL "
            "AND fuente_financiamiento_id IS NULL)",
            name="ck_movimiento_relacion_tipo",
        ),
    )
    op.create_table(
        "movimiento_memoria_version",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("memoria_version_id", sa.Integer(), nullable=False),
        sa.Column("movimiento_id", sa.Integer(), nullable=False),
        sa.Column("numero_movimiento", sa.Integer(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("tipo_movimiento", sa.String(length=7), nullable=False),
        sa.Column("monto", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("moneda", sa.String(length=3), nullable=False),
        sa.Column("fuente_financiamiento_id", sa.Integer(), nullable=True),
        sa.Column("fuente_financiamiento_nombre", sa.String(length=255), nullable=True),
        sa.Column("categoria_erogacion_id", sa.Integer(), nullable=True),
        sa.Column("categoria_erogacion_codigo", sa.String(length=20), nullable=True),
        sa.Column("categoria_erogacion_nombre", sa.String(length=100), nullable=True),
        sa.Column("grupo_utn_id", sa.Integer(), nullable=False),
        sa.Column("grupo_utn_nombre", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("deleted_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["memoria_version_id"], ["memoria_version.id"]),
        sa.ForeignKeyConstraint(["movimiento_id"], ["movimiento_financiero.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["usuario.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["usuario.id"]),
        sa.ForeignKeyConstraint(["deleted_by"], ["usuario.id"]),
        sa.UniqueConstraint("memoria_version_id", "movimiento_id", name="uq_movimiento_memoria_version"),
    )


def downgrade():
    op.drop_table("movimiento_memoria_version")
    op.drop_table("movimiento_financiero")
    op.drop_table("categoria_erogacion")
