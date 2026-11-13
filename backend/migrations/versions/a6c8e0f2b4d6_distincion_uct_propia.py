"""Pertenencia de distinciones independiente de su proyecto opcional."""
from alembic import op
import sqlalchemy as sa

revision = "a6c8e0f2b4d6"
down_revision = "e5a7c9d1f3b6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("distincion_recibida", sa.Column("grupo_utn_id", sa.Integer(), nullable=True))
    bind = op.get_bind()
    bind.execute(sa.text("""
        UPDATE distincion_recibida d SET grupo_utn_id = p.grupo_utn_id
        FROM proyecto_investigacion p WHERE p.id = d.proyecto_investigacion_id
    """))
    # Recuperar la pertenencia de desvinculaciones ya confirmadas en auditoria.
    bind.execute(sa.text("""
        UPDATE distincion_recibida d SET grupo_utn_id = (
            SELECT p.grupo_utn_id FROM auditoria_campo a
            JOIN proyecto_investigacion p ON p.id::text = a.valor_anterior #>> '{}'
            WHERE a.entidad = 'distincion_recibida' AND a.registro_id = d.id
              AND a.campo = 'proyecto_investigacion_id'
            ORDER BY a.fecha_cambio DESC, a.id DESC LIMIT 1
        ) WHERE d.grupo_utn_id IS NULL
    """))
    # Solo inferir del creador cuando su pertenencia sea inequivoca.
    bind.execute(sa.text("""
        UPDATE distincion_recibida d SET grupo_utn_id = m.grupo_id FROM (
            SELECT usuario_id, min(grupo_utn_id) AS grupo_id FROM usuario_grupo_utn
            WHERE activo = true AND deleted_at IS NULL
            GROUP BY usuario_id HAVING count(DISTINCT grupo_utn_id) = 1
        ) m WHERE d.grupo_utn_id IS NULL AND m.usuario_id = d.created_by
    """))
    if bind.execute(sa.text("SELECT 1 FROM distincion_recibida WHERE grupo_utn_id IS NULL LIMIT 1")).first():
        raise RuntimeError("Existen distinciones sin UCT identificable; resolver su pertenencia antes de migrar.")
    op.create_foreign_key("fk_distincion_grupo_utn", "distincion_recibida", "grupo_utn", ["grupo_utn_id"], ["id"])
    op.create_index("ix_distincion_recibida_grupo_utn_id", "distincion_recibida", ["grupo_utn_id"])
    op.alter_column("distincion_recibida", "grupo_utn_id", nullable=False)


def downgrade():
    op.drop_index("ix_distincion_recibida_grupo_utn_id", table_name="distincion_recibida")
    op.drop_constraint("fk_distincion_grupo_utn", "distincion_recibida", type_="foreignkey")
    op.drop_column("distincion_recibida", "grupo_utn_id")
