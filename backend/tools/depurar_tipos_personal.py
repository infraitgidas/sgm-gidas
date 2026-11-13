"""Depuración explícita y auditada del catálogo, conservando personas y fotos."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from extension import db
from modules.personal.models.tipo_personal import TipoPersonal
from modules.personal.models.personal import Personal, PersonalMemoriaVersion
from modules.personal.services.tipo_personal_service import normalizar_nombre_tipo, _bloquear_catalogo
from modules.shared.services.catalogo_auditoria_service import CatalogoAuditoriaService


def planificar(tipos, nombres):
    etiquetas = {normalizar_nombre_tipo(nombre): nombre for nombre in nombres}
    if not etiquetas or len(etiquetas) != len(nombres) or "" in etiquetas:
        raise ValueError("Indique nombres válidos, sin duplicados.")
    activos = [tipo for tipo in tipos if tipo.activo and tipo.deleted_at is None]
    elegidos = {}
    for clave, nombre in etiquetas.items():
        candidatos = [tipo for tipo in activos if normalizar_nombre_tipo(tipo.nombre) == clave]
        if not candidatos:
            raise ValueError(f"No hay una opción activa para {nombre}. Revise el catálogo antes de aplicar.")
        elegidos[clave] = min(candidatos, key=lambda tipo: (tipo.nombre != nombre, tipo.id))
    plan = []
    for tipo in sorted(activos, key=lambda tipo: tipo.id):
        clave = normalizar_nombre_tipo(tipo.nombre)
        if clave not in elegidos or elegidos[clave].id != tipo.id:
            plan.append({"id": tipo.id, "nombre": tipo.nombre, "accion": "inactivar"})
        elif tipo.nombre != etiquetas[clave]:
            plan.append({"id": tipo.id, "nombre": tipo.nombre, "accion": "normalizar", "nuevo_nombre": etiquetas[clave]})
    return plan


def huella_referencias():
    resultado = {}
    for modelo in (Personal, PersonalMemoriaVersion):
        filas = db.session.execute(db.select(modelo.__table__).order_by(modelo.id)).mappings().all()
        contenido = json.dumps([dict(fila) for fila in filas], ensure_ascii=False, sort_keys=True, default=str)
        resultado[modelo.__tablename__] = (len(filas), hashlib.sha256(contenido.encode("utf-8")).hexdigest())
    return resultado


def depurar(nombres, *, aplicar=False, esperados=None, user_id=None):
    try:
        if aplicar:
            _bloquear_catalogo()
        tipos = TipoPersonal.query.order_by(TipoPersonal.id).with_for_update(of=TipoPersonal).populate_existing().all() if aplicar else TipoPersonal.query.all()
        plan = planificar(tipos, nombres)
        if not aplicar:
            return plan
        if esperados is None or sorted(item["id"] for item in plan) != sorted(esperados):
            raise ValueError("El plan cambió o no fue confirmado. Ejecute primero la vista previa y confirme sus IDs.")
        antes = huella_referencias()
        por_id = {tipo.id: tipo for tipo in tipos}
        for cambio in plan:
            tipo = por_id[cambio["id"]]
            if cambio["accion"] == "inactivar":
                CatalogoAuditoriaService.marcar_baja(tipo, user_id)
            else:
                cambios = CatalogoAuditoriaService.construir_cambios(tipo, {"nombre": cambio["nuevo_nombre"]})
                tipo.nombre = cambio["nuevo_nombre"]
                CatalogoAuditoriaService.marcar_actualizacion(tipo, cambios, user_id)
            CatalogoAuditoriaService.registrar_accion(tipo, "depurar_catalogo", user_id,
                detalle={"nombre_anterior": cambio["nombre"], "opciones_conservadas": nombres})
        db.session.flush()
        if huella_referencias() != antes:
            raise RuntimeError("Se alteraron referencias o datos de Personal. La operación se revierte.")
        db.session.commit()
        return plan
    except Exception:
        db.session.rollback()
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--conservar", action="append", required=True, help="Nombre activo que se conservará; repetir por opción.")
    parser.add_argument("--aplicar", action="store_true")
    parser.add_argument("--ids-esperados", help="IDs del plan de vista previa, separados por comas.")
    parser.add_argument("--usuario-id", type=int)
    args = parser.parse_args()
    esperados = [int(valor) for valor in args.ids_esperados.split(",") if valor] if args.ids_esperados is not None else None
    from app import app
    with app.app_context():
        plan = depurar(args.conservar, aplicar=args.aplicar, esperados=esperados, user_id=args.usuario_id)
        print(json.dumps({"aplicado": args.aplicar, "plan": plan}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
