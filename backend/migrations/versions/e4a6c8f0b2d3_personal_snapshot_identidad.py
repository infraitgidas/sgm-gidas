"""Vincula fotos de personal a su identidad estable, conservando su contenido.

Revision ID: e4a6c8f0b2d3
Revises: d3f5a7c9e1b2
"""
from alembic import op
import sqlalchemy as sa

revision = "e4a6c8f0b2d3"
down_revision = "d3f5a7c9e1b2"
branch_labels = None
depends_on = None

CLASES = ("personal", "becario", "investigador")
NAMING = {"fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"}


def upgrade():
    bind = op.get_bind()
    for clase in CLASES:
        tabla = f"{clase}_memoria_version"
        origen_id = f"{clase}_id"
        referencias = [fk for fk in sa.inspect(bind).get_foreign_keys(tabla)
                       if fk["constrained_columns"] == [origen_id] and fk["referred_table"] == clase]
        if len(referencias) != 1:
            raise RuntimeError(f"No se encontró una referencia de origen única en {tabla}.")
        op.add_column(tabla, sa.Column("identidad_id", sa.Integer(), nullable=True))
        # Solo se completa metadata del vínculo: no cambia ningún dato de la foto.
        op.execute(sa.text(f"UPDATE {tabla} SET identidad_id = "
                           f"(SELECT identidad_id FROM {clase} WHERE {clase}.id = {tabla}.{origen_id})"))
        with op.batch_alter_table(tabla, naming_convention=NAMING) as batch:
            nombre_fk = referencias[0]["name"] or f"fk_{tabla}_{origen_id}_{clase}"
            batch.drop_constraint(nombre_fk, type_="foreignkey")
            batch.create_foreign_key(f"fk_{tabla}_identidad", "identidad_personal", ["identidad_id"], ["id"], ondelete="RESTRICT")
            batch.create_unique_constraint(f"uq_{clase}_memoria_identidad", ["memoria_version_id", "identidad_id"])
            batch.create_index(f"ix_{tabla}_identidad_id", ["identidad_id"])


def downgrade():
    bind = op.get_bind()
    # Después de reclasificar no es seguro reinstalar una FK al registro eliminado.
    # Se valida todo antes de alterar tablas para impedir una reversión parcial.
    for clase in CLASES:
        tabla = f"{clase}_memoria_version"
        falta = bind.execute(sa.text(
            f"SELECT 1 FROM {tabla} foto LEFT JOIN {clase} origen ON origen.id = foto.{clase}_id "
            f"WHERE origen.id IS NULL OR (foto.identidad_id IS NOT NULL AND "
            f"(origen.identidad_id IS NULL OR origen.identidad_id != foto.identidad_id)) LIMIT 1"
        )).first()
        if falta:
            raise RuntimeError("No se puede revertir tras una reclasificación con fotos históricas. Restaure primero los registros de origen desde un respaldo coherente.")
    for clase in reversed(CLASES):
        tabla = f"{clase}_memoria_version"
        with op.batch_alter_table(tabla, naming_convention=NAMING) as batch:
            batch.drop_index(f"ix_{tabla}_identidad_id")
            batch.drop_constraint(f"uq_{clase}_memoria_identidad", type_="unique")
            batch.drop_constraint(f"fk_{tabla}_identidad", type_="foreignkey")
            batch.create_foreign_key(f"fk_{tabla}_{clase}_id_{clase}", clase, [f"{clase}_id"], ["id"])
            batch.drop_column("identidad_id")
