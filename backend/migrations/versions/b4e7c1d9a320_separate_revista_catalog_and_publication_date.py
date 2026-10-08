"""Separate journal type catalog and publication date contract."""

from alembic import op
import sqlalchemy as sa


revision = "b4e7c1d9a320"
down_revision = "a1d7c9e2f4b6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tipo_revista",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(length=100), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("activo", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("deleted_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["usuario.id"], name="fk_tipo_revista_created_by_usuario"),
        sa.ForeignKeyConstraint(["updated_by"], ["usuario.id"], name="fk_tipo_revista_updated_by_usuario"),
        sa.ForeignKeyConstraint(["deleted_by"], ["usuario.id"], name="fk_tipo_revista_deleted_by_usuario"),
    )
    tipo_revista = sa.table("tipo_revista", sa.column("nombre", sa.String()))
    op.bulk_insert(tipo_revista, [{"nombre": "Nacional"}, {"nombre": "Internacional"}])

    for table_name in ("trabajos_revista", "trabajos_revista_memoria_version"):
        op.add_column(table_name, sa.Column("fecha_publicacion", sa.Date(), nullable=True))
        op.add_column(table_name, sa.Column("tipo_revista_id", sa.Integer(), nullable=True))
        op.execute(sa.text(f"UPDATE {table_name} SET fecha_publicacion = fecha"))
        op.execute(sa.text(
            f"UPDATE {table_name} SET tipo_revista_id = "
            "(SELECT id FROM tipo_revista WHERE nombre = 'Nacional')"
        ))
        op.alter_column(table_name, "fecha_publicacion", nullable=False)
        op.alter_column(table_name, "tipo_revista_id", nullable=False)
        op.create_foreign_key(
            f"fk_{table_name}_tipo_revista_id",
            table_name,
            "tipo_revista",
            ["tipo_revista_id"],
            ["id"],
        )

    op.drop_constraint(
        "trabajos_revista_tipo_reunion_id_fkey",
        "trabajos_revista",
        type_="foreignkey",
    )
    op.drop_column("trabajos_revista", "tipo_reunion_id")
    op.drop_column("trabajos_revista", "fecha")

    op.drop_constraint(
        "trabajos_revista_memoria_version_tipo_reunion_id_fkey",
        "trabajos_revista_memoria_version",
        type_="foreignkey",
    )
    op.drop_column("trabajos_revista_memoria_version", "tipo_reunion_id")
    op.drop_column("trabajos_revista_memoria_version", "tipo_reunion_nombre")
    op.drop_column("trabajos_revista_memoria_version", "fecha")
    op.add_column(
        "trabajos_revista_memoria_version",
        sa.Column("tipo_revista_nombre", sa.String(length=100), nullable=True),
    )


def downgrade():
    op.add_column("trabajos_revista", sa.Column("fecha", sa.Date(), nullable=True))
    op.add_column("trabajos_revista", sa.Column("tipo_reunion_id", sa.Integer(), nullable=True))
    op.add_column("trabajos_revista_memoria_version", sa.Column("fecha", sa.Date(), nullable=True))
    op.add_column("trabajos_revista_memoria_version", sa.Column("tipo_reunion_id", sa.Integer(), nullable=True))
    op.add_column("trabajos_revista_memoria_version", sa.Column("tipo_reunion_nombre", sa.String(length=100), nullable=True))

    op.execute(sa.text("UPDATE trabajos_revista SET fecha = fecha_publicacion"))
    op.execute(sa.text("UPDATE trabajos_revista_memoria_version SET fecha = fecha_publicacion"))
    op.execute(sa.text(
        "UPDATE trabajos_revista SET tipo_reunion_id = "
        "(SELECT MIN(id) FROM tipo_reunion_cientifica)"
    ))
    op.execute(sa.text(
        "UPDATE trabajos_revista_memoria_version SET tipo_reunion_id = "
        "(SELECT MIN(id) FROM tipo_reunion_cientifica)"
    ))
    op.alter_column("trabajos_revista", "fecha", nullable=False)
    op.alter_column("trabajos_revista", "tipo_reunion_id", nullable=False)
    op.alter_column("trabajos_revista_memoria_version", "fecha", nullable=False)
    op.alter_column("trabajos_revista_memoria_version", "tipo_reunion_id", nullable=False)
    op.create_foreign_key(
        "trabajos_revista_tipo_reunion_id_fkey",
        "trabajos_revista",
        "tipo_reunion_cientifica",
        ["tipo_reunion_id"],
        ["id"],
    )
    op.create_foreign_key(
        "trabajos_revista_memoria_version_tipo_reunion_id_fkey",
        "trabajos_revista_memoria_version",
        "tipo_reunion_cientifica",
        ["tipo_reunion_id"],
        ["id"],
    )

    op.drop_constraint("fk_trabajos_revista_tipo_revista_id", "trabajos_revista", type_="foreignkey")
    op.drop_constraint(
        "fk_trabajos_revista_memoria_version_tipo_revista_id",
        "trabajos_revista_memoria_version",
        type_="foreignkey",
    )
    op.drop_column("trabajos_revista_memoria_version", "tipo_revista_nombre")
    for table_name in ("trabajos_revista_memoria_version", "trabajos_revista"):
        op.drop_column(table_name, "tipo_revista_id")
        op.drop_column(table_name, "fecha_publicacion")
    op.drop_table("tipo_revista")
