"""ISS-16: UCT de memoria y pertenencia historica de integrantes.

Las memorias existentes quedan sin UCT si no puede determinarse sin inventar
historia. Las abiertas pueden asociarse explicitamente mediante PUT.
"""
from alembic import op
import sqlalchemy as sa
revision = "e16a0b2c4d60"
down_revision = "d14e8f0a3c51"
branch_labels = None
depends_on = None
TABLAS = ("investigador_memoria_version", "becario_memoria_version", "personal_memoria_version")


def upgrade():
    op.add_column("memoria_version", sa.Column("contexto_institucional", sa.JSON(), nullable=True))
    with op.batch_alter_table("memoria") as batch:
        batch.add_column(sa.Column("grupo_utn_id", sa.Integer(), nullable=True))
        batch.create_foreign_key("fk_memoria_grupo_utn", "grupo_utn", ["grupo_utn_id"], ["id"])
        batch.create_index("ix_memoria_grupo_utn_id", ["grupo_utn_id"])
    for tabla in TABLAS:
        with op.batch_alter_table(tabla) as batch:
            batch.add_column(sa.Column("fecha_alta_grupo", sa.Date(), nullable=True))
            batch.alter_column("horas_semanales", existing_type=sa.Integer(), nullable=True)


def downgrade():
    # No inventar horas para hacer NOT NULL: el downgrade requiere resolver
    # explicitamente snapshots sin evidencia historica antes de retroceder.
    for tabla in reversed(TABLAS):
        with op.batch_alter_table(tabla) as batch:
            batch.alter_column("horas_semanales", existing_type=sa.Integer(), nullable=False)
            batch.drop_column("fecha_alta_grupo")
    with op.batch_alter_table("memoria") as batch:
        batch.drop_index("ix_memoria_grupo_utn_id")
        batch.drop_constraint("fk_memoria_grupo_utn", type_="foreignkey")
        batch.drop_column("grupo_utn_id")
    op.drop_column("memoria_version", "contexto_institucional")
