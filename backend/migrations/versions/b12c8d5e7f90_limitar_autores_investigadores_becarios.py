"""ISS-12: limitar autores a investigadores y becarios.

Retira las asociaciones y autores de snapshots de Personal creados por la
ampliación anterior en testing. Conserva investigadores, becarios y auditoría.
El downgrade restaura la estructura de tres orígenes, sin recuperar esos datos.
"""
from alembic import op
import sqlalchemy as sa

revision = "b12c8d5e7f90"
down_revision = "a12b9c4d6e80"
branch_labels = None
depends_on = None

TABLAS = ("trabajo_reunion_autor", "trabajo_revista_autor")
SNAPSHOTS = ("trabajo_reunion_cientifica_memoria_version", "trabajos_revista_memoria_version")


def _check(tres_origenes=False):
    campos = ("investigador", "becario", "personal") if tres_origenes else ("investigador", "becario")
    return "(" + " + ".join(f"CASE WHEN {rol}_id IS NULL THEN 0 ELSE 1 END" for rol in campos) + ") = 1"


def upgrade():
    for tabla in TABLAS:
        op.execute(sa.text(f"DELETE FROM {tabla} WHERE personal_id IS NOT NULL"))
        op.drop_constraint(f"ck_{tabla}_un_integrante", tabla, type_="check")
        op.drop_constraint(f"uq_{tabla}_personal", tabla, type_="unique")
        op.drop_index(f"ix_{tabla}_personal_id", table_name=tabla)
        op.drop_column(tabla, "personal_id")
        op.create_check_constraint(f"ck_{tabla}_un_integrante", tabla, _check())
    for tabla in SNAPSHOTS:
        op.execute(sa.text(f"""
            UPDATE {tabla} SET autores = COALESCE(
                (SELECT json_agg(autor ORDER BY orden)
                 FROM json_array_elements(autores) WITH ORDINALITY AS elementos(autor, orden)
                 WHERE autor->>'rol' IN ('investigador', 'becario')), '[]'::json)
        """))


def downgrade():
    for tabla in TABLAS:
        op.drop_constraint(f"ck_{tabla}_un_integrante", tabla, type_="check")
        op.add_column(tabla, sa.Column("personal_id", sa.Integer(), sa.ForeignKey("personal.id", ondelete="RESTRICT")))
        op.create_index(f"ix_{tabla}_personal_id", tabla, ["personal_id"])
        op.create_unique_constraint(f"uq_{tabla}_personal", tabla, ["trabajo_id", "personal_id"])
        op.create_check_constraint(f"ck_{tabla}_un_integrante", tabla, _check(tres_origenes=True))
