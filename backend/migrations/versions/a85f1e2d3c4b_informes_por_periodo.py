"""Informes manuales vinculados a periodos de Memoria.

Revision ID: a85f1e2d3c4b
Revises: d5a7e9c1b3f2
"""
from alembic import op
import sqlalchemy as sa

revision = "a85f1e2d3c4b"
down_revision = "d5a7e9c1b3f2"
branch_labels = None
depends_on = None


def _audit_columns():
    return [
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime()),
        sa.Column("deleted_at", sa.DateTime()),
        sa.Column("activo", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("usuario.id")),
        sa.Column("updated_by", sa.Integer(), sa.ForeignKey("usuario.id")),
        sa.Column("deleted_by", sa.Integer(), sa.ForeignKey("usuario.id")),
    ]


def upgrade():
    op.create_table(
        "informe",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("memoria_id", sa.Integer(), sa.ForeignKey("memoria.id"), nullable=False),
        sa.Column("grupo_utn_id", sa.Integer(), sa.ForeignKey("grupo_utn.id"), nullable=False),
        sa.Column("titulo", sa.String(200), nullable=False),
        sa.Column("fecha_realizacion", sa.Date(), nullable=False),
        sa.Column("resumen", sa.Text(), nullable=False),
        sa.Column("actividades", sa.Text(), nullable=False),
        sa.Column("resultados", sa.Text(), nullable=False),
        sa.Column("observaciones", sa.Text(), nullable=False),
        sa.Column("uct_snapshot", sa.JSON(), nullable=False),
        *_audit_columns(),
        sa.CheckConstraint("tipo IN ('investigadores', 'pid', 'uct')", name="ck_informe_tipo"),
    )
    op.create_index("ix_informe_memoria_id", "informe", ["memoria_id"])
    op.create_index("ix_informe_grupo_utn_id", "informe", ["grupo_utn_id"])
    op.create_index("ix_informe_uct_tipo_fecha", "informe", ["grupo_utn_id", "tipo", "fecha_realizacion"])
    for table, entity, target in (
        ("informe_investigador", "investigador", "investigador"),
        ("informe_proyecto", "proyecto", "proyecto_investigacion"),
    ):
        op.create_table(
            table,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("informe_id", sa.Integer(), sa.ForeignKey("informe.id"), nullable=False),
            sa.Column(f"{entity}_id", sa.Integer(), sa.ForeignKey(f"{target}.id"), nullable=False),
            sa.Column("snapshot", sa.JSON(), nullable=False),
            *_audit_columns(),
            sa.UniqueConstraint("informe_id", f"{entity}_id", name=f"uq_{table}"),
        )
        op.create_index(f"ix_{table}_informe_id", table, ["informe_id"])
        op.create_index(f"ix_{table}_{entity}_id", table, [f"{entity}_id"])


def downgrade():
    op.execute("DELETE FROM auditoria_campo WHERE entidad = 'informe'")
    op.drop_table("informe_proyecto")
    op.drop_table("informe_investigador")
    op.drop_table("informe")
