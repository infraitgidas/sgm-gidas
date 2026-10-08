"""Cotizaciones oficiales y equivalentes históricos de movimientos.

Revision ID: d8e1f4a6b2c9
Revises: a85f1e2d3c4b
"""

from alembic import op
import sqlalchemy as sa

revision = "d8e1f4a6b2c9"
down_revision = "a85f1e2d3c4b"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tipo_cambio",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("moneda_origen", sa.String(3), nullable=False),
        sa.Column("moneda_destino", sa.String(3), nullable=False),
        sa.Column("fecha_cotizacion", sa.Date(), nullable=False),
        sa.Column("valor", sa.Numeric(18, 6), nullable=False),
        sa.Column("serie_bcra", sa.Integer(), nullable=False),
        sa.Column("fuente", sa.String(32), nullable=False),
        sa.Column("fecha_obtencion", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("moneda_origen", "moneda_destino", "fecha_cotizacion", "serie_bcra",
                            name="uq_tipo_cambio_observacion"),
        sa.CheckConstraint("valor > 0", name="ck_tipo_cambio_valor_positivo"),
    )
    op.create_index("ix_tipo_cambio_vigente", "tipo_cambio",
                    ["moneda_origen", "moneda_destino", "serie_bcra", "fecha_cotizacion"])
    with op.batch_alter_table("movimiento_financiero") as batch:
        batch.add_column(sa.Column("tipo_cambio_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("tipo_cambio_aplicado", sa.Numeric(18, 6), nullable=True))
        batch.add_column(sa.Column("monto_equivalente_ars", sa.Numeric(24, 2), nullable=True))
        batch.create_foreign_key("fk_movimiento_tipo_cambio", "tipo_cambio", ["tipo_cambio_id"], ["id"])
    op.execute("UPDATE movimiento_financiero SET monto_equivalente_ars = monto WHERE moneda = 'ARS'")
    with op.batch_alter_table("movimiento_financiero") as batch:
        batch.create_check_constraint("ck_movimiento_tipo_cambio",
            "(moneda = 'ARS' AND tipo_cambio_id IS NULL AND tipo_cambio_aplicado IS NULL) OR "
            "(moneda = 'USD' AND tipo_cambio_id IS NOT NULL AND tipo_cambio_aplicado IS NOT NULL "
            "AND tipo_cambio_aplicado > 0 AND monto_equivalente_ars IS NOT NULL "
            "AND monto_equivalente_ars > 0)")
    with op.batch_alter_table("movimiento_memoria_version") as batch:
        batch.add_column(sa.Column("tipo_cambio_aplicado", sa.Numeric(18, 6), nullable=True))
        batch.add_column(sa.Column("monto_equivalente_ars", sa.Numeric(24, 2), nullable=True))
        batch.add_column(sa.Column("fecha_cotizacion", sa.Date(), nullable=True))
        batch.add_column(sa.Column("serie_bcra", sa.Integer(), nullable=True))
    op.execute("UPDATE movimiento_memoria_version SET monto_equivalente_ars = monto WHERE moneda = 'ARS'")


def downgrade():
    with op.batch_alter_table("movimiento_memoria_version") as batch:
        batch.drop_column("serie_bcra")
        batch.drop_column("fecha_cotizacion")
        batch.drop_column("monto_equivalente_ars")
        batch.drop_column("tipo_cambio_aplicado")
    with op.batch_alter_table("movimiento_financiero") as batch:
        batch.drop_constraint("ck_movimiento_tipo_cambio", type_="check")
        batch.drop_constraint("fk_movimiento_tipo_cambio", type_="foreignkey")
        batch.drop_column("monto_equivalente_ars")
        batch.drop_column("tipo_cambio_aplicado")
        batch.drop_column("tipo_cambio_id")
    op.drop_index("ix_tipo_cambio_vigente", table_name="tipo_cambio")
    op.drop_table("tipo_cambio")
