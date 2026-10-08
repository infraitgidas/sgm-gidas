"""change project codes to string

Revision ID: c6e8a1f4b2d9
Revises: d7e4a2c9f1b6
Create Date: 2026-09-10 16:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "c6e8a1f4b2d9"
down_revision = "d7e4a2c9f1b6"
branch_labels = None
depends_on = None


PROJECT_CODE_COLUMNS = (
    ("proyecto_investigacion", "codigo_proyecto", False),
    ("proyecto_investigacion_memoria_version", "codigo_proyecto", False),
    ("distincion_recibida_memoria_version", "proyecto_codigo", True),
)


def _alter_column(table_name, column_name, current_type, target_type, nullable):
    if op.get_bind().dialect.name == "postgresql":
        cast_type = "text" if isinstance(target_type, sa.String) else "integer"
        op.alter_column(
            table_name,
            column_name,
            existing_type=current_type,
            type_=target_type,
            existing_nullable=nullable,
            postgresql_using=f'"{column_name}"::{cast_type}',
        )
        return

    with op.batch_alter_table(table_name) as batch_op:
        batch_op.alter_column(
            column_name,
            existing_type=current_type,
            type_=target_type,
            existing_nullable=nullable,
        )


def _assert_safe_integer_downgrade(bind):
    integer_min = -(2**31)
    integer_max = 2**31 - 1

    for table_name, column_name, _ in PROJECT_CODE_COLUMNS:
        values = bind.execute(
            sa.text(
                f'SELECT DISTINCT "{column_name}" FROM "{table_name}" '
                f'WHERE "{column_name}" IS NOT NULL'
            )
        ).scalars()

        for value in values:
            text_value = str(value)
            try:
                integer_value = int(text_value)
            except (TypeError, ValueError):
                integer_value = None

            if (
                integer_value is None
                or not integer_min <= integer_value <= integer_max
                or str(integer_value) != text_value
            ):
                raise RuntimeError(
                    "No se puede revertir codigo_proyecto a INTEGER: "
                    "existen códigos no numéricos, fuera de rango o cuya "
                    "representación cambiaría."
                )


def upgrade():
    for table_name, column_name, nullable in PROJECT_CODE_COLUMNS:
        _alter_column(
            table_name,
            column_name,
            sa.Integer(),
            sa.String(length=50),
            nullable,
        )


def downgrade():
    _assert_safe_integer_downgrade(op.get_bind())

    for table_name, column_name, nullable in reversed(PROJECT_CODE_COLUMNS):
        _alter_column(
            table_name,
            column_name,
            sa.String(length=50),
            sa.Integer(),
            nullable,
        )
