"""Persist UCT ownership for records created before their first relation.

Revision ID: c3d5e7f9a1b2
Revises: b2c4d6e8f0a1
"""

from collections import defaultdict

from alembic import op
import sqlalchemy as sa


revision = "c3d5e7f9a1b2"
down_revision = "b2c4d6e8f0a1"
branch_labels = None
depends_on = None


OWNERS = {
    "beca": (
        "SELECT bb.id_beca, b.grupo_utn_id FROM beca_becario bb "
        "JOIN becario b ON b.id = bb.id_becario"
    ),
    "autor": (
        "SELECT al.id_autor, d.grupo_id FROM autorxlibro al "
        "JOIN documentacion_bibliografica d ON d.id = al.id_libro"
    ),
    "directivo": "SELECT id_directivo, id_grupo_utn FROM directivo_grupo",
    "adoptante": (
        "SELECT at.adoptante_id, t.grupo_utn_id FROM adoptante_x_transferencia at "
        "JOIN transferencia_socio_productiva t ON t.id = at.transferencia_id"
    ),
}


def upgrade():
    connection = op.get_bind()
    active_groups = connection.execute(sa.text(
        "SELECT id FROM grupo_utn WHERE activo = true AND deleted_at IS NULL"
    )).scalars().all()

    for table in OWNERS:
        column = sa.Column(
            "grupo_utn_id", sa.Integer(),
            sa.ForeignKey("grupo_utn.id", name=f"fk_{table}_grupo_utn_id"),
            nullable=True,
        )
        if connection.dialect.name == "sqlite":
            with op.batch_alter_table(table, recreate="always") as batch:
                batch.add_column(column)
        else:
            op.add_column(table, column)
        op.create_index(f"ix_{table}_grupo_utn_id", table, ["grupo_utn_id"])

    for table, relation_sql in OWNERS.items():
        groups_by_record = defaultdict(set)
        for record_id, group_id in connection.execute(sa.text(relation_sql)):
            groups_by_record[record_id].add(group_id)

        values = []
        for record_id in connection.execute(sa.text(f"SELECT id FROM {table}" )).scalars():
            linked_groups = groups_by_record[record_id]
            if len(linked_groups) == 1 and None not in linked_groups:
                group_id = next(iter(linked_groups))
            elif not linked_groups and len(active_groups) == 1:
                group_id = active_groups[0]
            else:
                continue  # Ambiguous records remain inaccessible until reviewed.
            values.append({"id": record_id, "group_id": group_id})

        if values:
            connection.execute(sa.text(
                f"UPDATE {table} SET grupo_utn_id = :group_id WHERE id = :id"
            ), values)


def downgrade():
    for table in reversed(tuple(OWNERS)):
        op.drop_index(f"ix_{table}_grupo_utn_id", table_name=table)
        if op.get_bind().dialect.name == "sqlite":
            with op.batch_alter_table(table, recreate="always") as batch:
                batch.drop_column("grupo_utn_id")
        else:
            op.drop_column(table, "grupo_utn_id")
