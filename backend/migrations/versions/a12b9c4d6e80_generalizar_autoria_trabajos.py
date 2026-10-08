"""ISS-12: reemplazo de esquema para datos de testeo regenerables.

No copia asociaciones ni autores de snapshots anteriores. El downgrade restaura
la estructura anterior sin recuperar datos. Regenerar el dataset tras el upgrade.
"""
from alembic import op
import sqlalchemy as sa

revision = "a12b9c4d6e80"
down_revision = "c6e8a1f4b2d9"
branch_labels = None
depends_on = None

TABLAS = (
    ("trabajo_reunion_autor", "trabajo_reunion_cientifica", "investigador_x_trabajo_reunion", "trabajo_reunion_id"),
    ("trabajo_revista_autor", "trabajos_revista", "investigador_x_trabajo_revista", "trabajos_revista_id"),
)
SNAPSHOTS = ("trabajo_reunion_cientifica_memoria_version", "trabajos_revista_memoria_version")


def upgrade():
    for tabla, trabajo, anterior, _ in TABLAS:
        op.create_table(tabla,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("trabajo_id", sa.Integer(), sa.ForeignKey(f"{trabajo}.id", ondelete="CASCADE"), nullable=False),
            *(sa.Column(f"{rol}_id", sa.Integer(), sa.ForeignKey(f"{rol}.id", ondelete="RESTRICT"))
              for rol in ("investigador", "becario", "personal")),
            sa.CheckConstraint(
                "(CASE WHEN investigador_id IS NULL THEN 0 ELSE 1 END + "
                "CASE WHEN becario_id IS NULL THEN 0 ELSE 1 END + "
                "CASE WHEN personal_id IS NULL THEN 0 ELSE 1 END) = 1",
                name=f"ck_{tabla}_un_integrante"),
            *(sa.UniqueConstraint("trabajo_id", f"{rol}_id", name=f"uq_{tabla}_{rol}")
              for rol in ("investigador", "becario", "personal")),
        )
        for campo in ("trabajo_id", "investigador_id", "becario_id", "personal_id"):
            op.create_index(f"ix_{tabla}_{campo}", tabla, [campo])
        op.drop_table(anterior)
    for tabla in SNAPSHOTS:
        with op.batch_alter_table(tabla) as batch:
            batch.add_column(sa.Column("autores", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
            batch.drop_column("investigadores_participantes")


def downgrade():
    for tabla in SNAPSHOTS:
        with op.batch_alter_table(tabla) as batch:
            batch.add_column(sa.Column("investigadores_participantes", sa.Text(), nullable=True))
            batch.drop_column("autores")
    for tabla, trabajo, anterior, campo in TABLAS:
        op.create_table(anterior,
            sa.Column("investigador_id", sa.Integer(), sa.ForeignKey("investigador.id"), primary_key=True),
            sa.Column(campo, sa.Integer(), sa.ForeignKey(f"{trabajo}.id"), primary_key=True),
        )
        op.drop_table(tabla)
