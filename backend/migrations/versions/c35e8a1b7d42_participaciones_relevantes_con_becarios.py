"""participaciones relevantes con investigadores o becarios

Revision ID: c35e8a1b7d42
Revises: b4e7c1d9a320
Create Date: 2026-09-25 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "c35e8a1b7d42"
down_revision = "b4e7c1d9a320"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("participacion_relevante") as batch_op:
        batch_op.add_column(sa.Column("becario_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_participacion_relevante_becario_id",
            "becario",
            ["becario_id"],
            ["id"],
        )
        batch_op.create_check_constraint(
            "ck_participacion_relevante_un_participante",
            "(investigador_id IS NOT NULL AND becario_id IS NULL) OR "
            "(investigador_id IS NULL AND becario_id IS NOT NULL)",
        )

    with op.batch_alter_table("participacion_relevante_memoria_version") as batch_op:
        batch_op.alter_column("investigador_id", existing_type=sa.Integer(), nullable=True)
        batch_op.add_column(sa.Column("becario_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("becario_nombre", sa.String(length=255), nullable=True))
        batch_op.create_foreign_key(
            "fk_participacion_relevante_memoria_becario_id",
            "becario",
            ["becario_id"],
            ["id"],
        )
        batch_op.create_check_constraint(
            "ck_participacion_relevante_memoria_un_participante",
            "(investigador_id IS NOT NULL AND becario_id IS NULL) OR "
            "(investigador_id IS NULL AND becario_id IS NOT NULL)",
        )


def downgrade():
    # Los snapshots de becarios no tienen una conversion segura a investigador.
    op.execute("DELETE FROM participacion_relevante_memoria_version WHERE becario_id IS NOT NULL")
    op.execute("DELETE FROM participacion_relevante WHERE becario_id IS NOT NULL")

    with op.batch_alter_table("participacion_relevante_memoria_version") as batch_op:
        batch_op.drop_constraint(
            "ck_participacion_relevante_memoria_un_participante", type_="check"
        )
        batch_op.drop_constraint(
            "fk_participacion_relevante_memoria_becario_id", type_="foreignkey"
        )
        batch_op.drop_column("becario_nombre")
        batch_op.drop_column("becario_id")
        batch_op.alter_column("investigador_id", existing_type=sa.Integer(), nullable=False)

    with op.batch_alter_table("participacion_relevante") as batch_op:
        batch_op.drop_constraint("ck_participacion_relevante_un_participante", type_="check")
        batch_op.drop_constraint("fk_participacion_relevante_becario_id", type_="foreignkey")
        batch_op.drop_column("becario_id")
