from app import app
from extension import db
from modules.auth.models.usuario import RolUsuario
from modules.grupo.models.directivos import Cargo
from sqlalchemy import func


def seed_roles():
    roles = ["ADMIN", "GESTOR", "LECTURA"]

    for nombre in roles:
        existe = RolUsuario.query.filter_by(nombre=nombre).first()
        if not existe:
            db.session.add(RolUsuario(nombre=nombre))



def seed_cargos_directivos():
    cargos = ["Director", "Vicedirector"]

    for nombre in cargos:
        existente = Cargo.query.filter(
            func.lower(Cargo.nombre) == nombre.lower()
        ).first()

        if existente:
            if existente.deleted_at is not None:
                existente.restore()
            continue

        db.session.add(Cargo(nombre=nombre))


def seed_initial_data():
    try:
        seed_roles()
        seed_cargos_directivos()
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    print("Roles y cargos iniciales verificados/cargados correctamente")


if __name__ == "__main__":
    with app.app_context():
        seed_initial_data()
