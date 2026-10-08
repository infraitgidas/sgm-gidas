"""Asocia egresos con fuente y, opcionalmente, equipamiento.

Revision ID: f4b8c6d2e9a1
Revises: e3a7d9b2c4f1
"""

from alembic import op
import sqlalchemy as sa


revision = "f4b8c6d2e9a1"
down_revision = "e3a7d9b2c4f1"
branch_labels = None
depends_on = None


def upgrade():
    # La etapa financiera contiene únicamente datos ficticios. No se puede atribuir
    # retrospectivamente una fuente real a los egresos previos.
    op.execute("DELETE FROM movimiento_memoria_version")
    op.execute("DELETE FROM auditoria_campo WHERE entidad = 'movimiento_financiero'")
    op.execute("DELETE FROM movimiento_financiero")
    with op.batch_alter_table("movimiento_financiero") as batch:
        batch.add_column(sa.Column("equipamiento_id", sa.Integer(), nullable=True))
        batch.alter_column("fuente_financiamiento_id", existing_type=sa.Integer(), nullable=False)
        batch.create_foreign_key("fk_movimiento_equipamiento", "equipamiento_grupo", ["equipamiento_id"], ["id"])
        batch.create_unique_constraint("uq_movimiento_equipamiento", ["equipamiento_id"])
        batch.drop_constraint("ck_movimiento_relacion_tipo", type_="check")
        batch.create_check_constraint(
            "ck_movimiento_relacion_tipo",
            "fuente_financiamiento_id IS NOT NULL AND "
            "((tipo_movimiento = 'INGRESO' AND categoria_erogacion_id IS NULL "
            "AND equipamiento_id IS NULL) OR "
            "(tipo_movimiento = 'EGRESO' AND categoria_erogacion_id IS NOT NULL))",
        )
    with op.batch_alter_table("movimiento_memoria_version") as batch:
        batch.add_column(sa.Column("equipamiento_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("equipamiento_denominacion", sa.Text(), nullable=True))


def downgrade():
    op.execute("DELETE FROM movimiento_memoria_version")
    op.execute("DELETE FROM auditoria_campo WHERE entidad = 'movimiento_financiero'")
    op.execute("DELETE FROM movimiento_financiero")
    with op.batch_alter_table("movimiento_memoria_version") as batch:
        batch.drop_column("equipamiento_denominacion")
        batch.drop_column("equipamiento_id")
    with op.batch_alter_table("movimiento_financiero") as batch:
        batch.drop_constraint("ck_movimiento_relacion_tipo", type_="check")
        batch.create_check_constraint(
            "ck_movimiento_relacion_tipo",
            "(tipo_movimiento = 'INGRESO' AND fuente_financiamiento_id IS NOT NULL "
            "AND categoria_erogacion_id IS NULL) OR "
            "(tipo_movimiento = 'EGRESO' AND categoria_erogacion_id IS NOT NULL "
            "AND fuente_financiamiento_id IS NULL)",
        )
        batch.drop_constraint("uq_movimiento_equipamiento", type_="unique")
        batch.drop_constraint("fk_movimiento_equipamiento", type_="foreignkey")
        batch.alter_column("fuente_financiamiento_id", existing_type=sa.Integer(), nullable=True)
        batch.drop_column("equipamiento_id")
