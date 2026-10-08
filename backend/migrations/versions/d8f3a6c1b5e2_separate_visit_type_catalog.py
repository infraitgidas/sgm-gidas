"""Separate visit types from scientific meeting types.

Revision ID: d8f3a6c1b5e2
Revises: c35e8a1b7d42
Create Date: 2026-09-25 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "d8f3a6c1b5e2"
down_revision = "c35e8a1b7d42"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tipo_visita",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(length=100), nullable=False, unique=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("activo", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("deleted_by", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["usuario.id"],
            name="fk_tipo_visita_created_by_usuario",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            ["usuario.id"],
            name="fk_tipo_visita_updated_by_usuario",
        ),
        sa.ForeignKeyConstraint(
            ["deleted_by"],
            ["usuario.id"],
            name="fk_tipo_visita_deleted_by_usuario",
        ),
    )

    tipo_visita = sa.table("tipo_visita", sa.column("nombre", sa.String()))
    op.bulk_insert(
        tipo_visita,
        [
            {"nombre": "Académica"},
            {"nombre": "Intercambio"},
        ],
    )

    # Los registros existentes pertenecen al dataset de prueba y utilizaban un
    # catálogo incorrecto. Se eliminan antes de cambiar las claves foráneas para
    # que el seed los regenere con tipos propios de visita.
    op.execute(
        sa.text(
            "DELETE FROM auditoria_campo "
            "WHERE entidad = 'visita_academica'"
        )
    )
    op.execute(
        sa.text(
            "DELETE FROM form_draft "
            "WHERE module = 'grupo-visitantes'"
        )
    )
    op.execute(sa.text("DELETE FROM visita_academica_memoria_version"))
    op.execute(sa.text("DELETE FROM visita_grupo"))

    op.drop_constraint(
        "visita_grupo_tipo_visita_id_fkey",
        "visita_grupo",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_visita_grupo_tipo_visita_id",
        "visita_grupo",
        "tipo_visita",
        ["tipo_visita_id"],
        ["id"],
    )

    op.drop_constraint(
        "visita_academica_memoria_version_tipo_visita_id_fkey",
        "visita_academica_memoria_version",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_visita_academica_memoria_version_tipo_visita_id",
        "visita_academica_memoria_version",
        "tipo_visita",
        ["tipo_visita_id"],
        ["id"],
    )


def downgrade():
    op.execute(sa.text("DELETE FROM visita_academica_memoria_version"))
    op.execute(sa.text("DELETE FROM visita_grupo"))

    op.drop_constraint(
        "fk_visita_academica_memoria_version_tipo_visita_id",
        "visita_academica_memoria_version",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "visita_academica_memoria_version_tipo_visita_id_fkey",
        "visita_academica_memoria_version",
        "tipo_reunion_cientifica",
        ["tipo_visita_id"],
        ["id"],
    )

    op.drop_constraint(
        "fk_visita_grupo_tipo_visita_id",
        "visita_grupo",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "visita_grupo_tipo_visita_id_fkey",
        "visita_grupo",
        "tipo_reunion_cientifica",
        ["tipo_visita_id"],
        ["id"],
    )

    op.drop_table("tipo_visita")
