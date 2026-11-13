"""Normaliza exclusivamente el conjunto ficticio revisado de ISS-34.

Revision ID: d3f5a7c9e1b2
Revises: c2e4a6b8d0f1
"""
from datetime import datetime

from alembic import op
import sqlalchemy as sa

revision = "d3f5a7c9e1b2"
down_revision = "c2e4a6b8d0f1"
branch_labels = None
depends_on = None

TABLAS = ("personal", "becario", "investigador")

# Correspondencias revisadas del dataset ficticio, sin inferir apellidos
# para registros desconocidos. Los casos incompletos usan identidades ficticias.
NOMBRES = {
    "Valentina Noemi": ("Valentina Noemí", "López"),
    "Benjamin S": ("Benjamin", "Suárez"),
    "Carla Ruiz": ("Carla", "Ruiz"),
    "Sebastian Barragan": ("Sebastian", "Barragan"),
    "Catalina Leonidas": ("Catalina", "Leonidas"),
    "Briones": ("Luciana", "Briones"),
    "Mateo Ariel": ("Mateo Ariel", "Molina"),
    "Evangelina Briones": ("Evangelina", "Briones"),
    "Lic. Bruno Gomez": ("Bruno", "Gomez"),
    "Lucas": ("Lucas", "Medina"),
    "Martin Keee": ("Martín", "Pereyra"),
    "Cali Falco": ("Cali", "Falco"),
    "Tiago Almada": ("Tiago", "Almada"),
    "Juan Manuel": ("Juan Manuel", "Fernández"),
    "Melina Alzo": ("Melina", "Alzo"),
    "Dra. Ana Perez": ("Ana", "Perez"),
    "Benjamin": ("Benjamin", "Torres"),
    "Lautaro Di Lollo": ("Lautaro", "Di Lollo"),
}

for nombre in ("María Elena", "Pablo Esteban", "Lucía Valentina", "Martín Andrés",
               "Camila Soledad", "Federico Nicolás", "Julieta Gabriela"):
    for apellido in ("Herrera", "Quiroga", "Benítez", "Acosta", "Romero"):
        NOMBRES[f"{nombre} {apellido}"] = (nombre, apellido)

for nombre in ("Sofía", "Tomás", "Valentina", "Santiago", "Catalina", "Joaquín"):
    for segundo, apellido in (("Victoria", "Herrera"), ("Manuel", "Quiroga"),
                              ("Lucía", "Benítez"), ("Andrés", "Acosta"), ("Paula", "Romero")):
        variantes = ({"Manuel": "Manuela", "Andrés": "Andrea"} if nombre in ("Sofía", "Valentina", "Catalina")
                     else {"Victoria": "Víctor", "Lucía": "Luciano", "Paula": "Pablo"})
        NOMBRES[f"{nombre} {segundo} {apellido}"] = (f"{nombre} {variantes.get(segundo, segundo)}", apellido)

for prefijo, nombres in (
    ("Tecnico Administrativo", ("Tomás", "Diego", "Nicolás", "Ramiro", "Pablo", "Andrés", "Sergio", "Martín", "Julián", "Marcos", "Pedro", "Gabriel")),
    ("Profesional", ("Paula", "Carolina", "Luciana", "Mariana", "Natalia", "Cecilia", "Florencia", "Daniela", "Laura", "Romina", "Verónica", "Alejandra")),
    ("Becario", ("Bruno", "Agustina", "Valentín", "Camila", "Franco", "Julieta", "Matías", "Clara", "Emiliano", "Lucía", "Ignacio", "Sofía")),
    ("Investigador", ("Inés", "Esteban", "Elena", "Ricardo", "Adriana", "Gustavo", "Beatriz", "Eduardo", "Silvia", "Fernando", "Teresa", "Alberto")),
):
    for numero, (nombre, apellido) in enumerate(zip(nombres, ("García", "López", "Fernández", "González", "Rodríguez", "Martínez",
                                                            "Pérez", "Sánchez", "Romero", "Díaz", "Álvarez", "Torres")), 1):
        NOMBRES[f"{prefijo} {numero:02d} TEST"] = (nombre, apellido)


def _tabla(nombre):
    return sa.table(nombre, sa.column("id", sa.Integer), sa.column("nombre_apellido", sa.String),
                    sa.column("nombre", sa.String), sa.column("apellido", sa.String))


def planificar(connection):
    plan = []
    for nombre_tabla in TABLAS:
        tabla = _tabla(nombre_tabla)
        for registro in connection.execute(sa.select(tabla).order_by(tabla.c.id)).mappings():
            if registro["nombre"] and registro["apellido"]:
                continue
            original = registro["nombre_apellido"]
            if original not in NOMBRES:
                raise RuntimeError(f"ISS-34: revisar correspondencia de {nombre_tabla} #{registro['id']}; migracion cancelada.")
            nombre, apellido = NOMBRES[original]
            for campo, valor in (("nombre", nombre), ("apellido", apellido)):
                if registro[campo] not in (None, "", valor):
                    raise RuntimeError(f"ISS-34: valor parcial incompatible en {nombre_tabla} #{registro['id']}.")
                if len(valor) > 60 or not all(parte.isalpha() for parte in valor.split()):
                    raise RuntimeError("ISS-34: correspondencia invalida.")
            compuesto = f"{nombre} {apellido}"
            if len(compuesto) > 120:
                raise RuntimeError("ISS-34: nombre completo demasiado extenso.")
            plan.append((nombre_tabla, dict(registro), {"nombre": nombre, "apellido": apellido, "nombre_apellido": compuesto}))
    return plan


def upgrade():
    connection = op.get_bind()
    # Planificar todo antes de escribir evita aplicar correspondencias parciales.
    plan = planificar(connection)
    auditoria = sa.table("auditoria_campo", sa.column("entidad", sa.String), sa.column("registro_id", sa.Integer),
                         sa.column("campo", sa.String), sa.column("valor_anterior", sa.JSON),
                         sa.column("valor_nuevo", sa.JSON), sa.column("fecha_cambio", sa.DateTime))
    fecha = datetime.utcnow()
    for nombre_tabla, anterior, nuevo in plan:
        tabla = _tabla(nombre_tabla)
        connection.execute(tabla.update().where(tabla.c.id == anterior["id"]).values(**nuevo))
        for campo, valor in nuevo.items():
            if anterior[campo] != valor:
                connection.execute(auditoria.insert().values(entidad=nombre_tabla, registro_id=anterior["id"],
                    campo=campo, valor_anterior=anterior[campo], valor_nuevo=valor, fecha_cambio=fecha))


def downgrade():
    # Las correcciones de datos no deben deshacerse sobre ediciones posteriores.
    # Los originales permanecen consultables en auditoria_campo.
    raise RuntimeError("ISS-34: normalizacion de datos irreversible automaticamente; recuperar desde auditoria o respaldo revisado.")
