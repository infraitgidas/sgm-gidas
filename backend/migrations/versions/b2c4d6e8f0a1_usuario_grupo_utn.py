"""Add audited UCT membership without assigning ambiguous existing data.

Revision ID: b2c4d6e8f0a1
Revises: f0a8c1d2e3b4
"""

from alembic import op
import sqlalchemy as sa


revision = "b2c4d6e8f0a1"
down_revision = "f0a8c1d2e3b4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "usuario_grupo_utn",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("grupo_utn_id", sa.Integer(), sa.ForeignKey("grupo_utn.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("usuario.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("updated_at", sa.DateTime()),
        sa.Column("updated_by", sa.Integer(), sa.ForeignKey("usuario.id", ondelete="RESTRICT")),
        sa.Column("deleted_at", sa.DateTime()),
        sa.Column("deleted_by", sa.Integer(), sa.ForeignKey("usuario.id", ondelete="RESTRICT")),
    )
    op.create_index("ix_usuario_grupo_utn_usuario_activo", "usuario_grupo_utn", ["usuario_id", "activo", "grupo_utn_id"])
    op.create_index("ix_usuario_grupo_utn_grupo_activo", "usuario_grupo_utn", ["grupo_utn_id", "activo", "usuario_id"])
    op.create_index(
        "uq_usuario_grupo_utn_activa", "usuario_grupo_utn", ["usuario_id", "grupo_utn_id"],
        unique=True,
        postgresql_where=sa.text("activo = true AND deleted_at IS NULL"),
        sqlite_where=sa.text("activo = 1 AND deleted_at IS NULL"),
    )

    # The current installation has one UCT. Only that unambiguous case can
    # receive an automatic migration; multiple active UCTs fail closed.
    connection = op.get_bind()
    group_ids = connection.execute(sa.text(
        "SELECT id FROM grupo_utn WHERE activo = true AND deleted_at IS NULL"
    )).scalars().all()
    if len(group_ids) == 1:
        administrator_id = connection.execute(sa.text(
            "SELECT usuario.id FROM usuario JOIN rol ON usuario.id_rol = rol.id "
            "WHERE rol.nombre = 'ADMIN' AND usuario.activo = true "
            "AND usuario.deleted_at IS NULL ORDER BY usuario.id LIMIT 1"
        )).scalar()
        if administrator_id is not None:
            connection.execute(sa.text(
                "INSERT INTO usuario_grupo_utn "
                "(usuario_id, grupo_utn_id, activo, created_at, created_by) "
                "SELECT id, :group_id, true, CURRENT_TIMESTAMP, :actor_id "
                "FROM usuario WHERE activo = true AND deleted_at IS NULL"
            ), {"group_id": group_ids[0], "actor_id": administrator_id})


def downgrade():
    op.drop_index("uq_usuario_grupo_utn_activa", table_name="usuario_grupo_utn")
    op.drop_index("ix_usuario_grupo_utn_grupo_activo", table_name="usuario_grupo_utn")
    op.drop_index("ix_usuario_grupo_utn_usuario_activo", table_name="usuario_grupo_utn")
    op.drop_table("usuario_grupo_utn")
