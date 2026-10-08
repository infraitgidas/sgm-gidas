from modules.shared.services.catalog_name_validation import validar_nombre_descriptivo
import builtins
from datetime import date, datetime, timedelta
from sqlalchemy import func
from sqlalchemy import extract, or_
from sqlalchemy.orm import joinedload, selectinload
from extension import db
from modules.recursos.models.becas import (
    Beca,
    Beca_Becario,
)
from modules.personal.models.personal import Becario
from modules.catalogos.models.fuente_financiamiento import FuenteFinanciamiento
from modules.shared.services.auditoria_service import AuditoriaService
from modules.shared.services.date_time import validate_institutional_date
from modules.memorias.services.memoria_periodo_service import validar_fecha_alta_grupo
from modules.shared.exceptions import ConflictError, NotFoundError, ValidationError as ValueError


# =====================================================
# HELPERS
# =====================================================

def _get_beca_activa_or_404(beca_id: int):
    beca = db.session.get(Beca, beca_id)
    if not beca or beca.deleted_at is not None:
        raise NotFoundError("Beca no encontrada.")
    return beca


def _get_beca_or_404(beca_id: int):
    beca = db.session.get(Beca, beca_id)
    if not beca:
        raise NotFoundError("Beca no encontrada.")
    return beca


def _get_relacion_activa(beca_id: int, becario_id: int):
    return Beca_Becario.query.filter(
        Beca_Becario.id_beca == beca_id,
        Beca_Becario.id_becario == becario_id,
        Beca_Becario.deleted_at.is_(None)
    ).first()


def _validar_nombre_beca(nombre):
    if not isinstance(nombre, str):
        raise ValueError("El nombre de la beca es obligatorio.")

    nombre = " ".join(nombre.strip().split())
    validar_nombre_descriptivo(nombre, "nombre_beca")
    if not nombre:
        raise ValueError("El nombre de la beca es obligatorio.")

    return nombre


def _validar_descripcion_beca(descripcion):
    if descripcion in (None, ""):
        return None
    if not isinstance(descripcion, str):
        raise ValueError("La descripción de la beca debe ser texto.")
    descripcion = descripcion.strip()
    if len(descripcion) > 2000:
        raise ValueError("La descripción de la beca no puede superar 2000 caracteres.")
    return descripcion or None


def _validar_fuente_financiamiento(fuente_financiamiento_id):
    if fuente_financiamiento_id is None:
        return None

    fuente = db.session.get(FuenteFinanciamiento, fuente_financiamiento_id)
    if not fuente:
        raise ValueError("Fuente de financiamiento invalida.")

    return fuente.id


def _parsear_fecha(valor, campo):
    try:
        return validate_institutional_date(
            datetime.strptime(valor, "%Y-%m-%d").date(), campo
        )
    except (TypeError, builtins.ValueError):
        raise ValueError(f"Formato de {campo} invalido.")


def _validar_beca_unica(nombre_beca, fuente_financiamiento_id, beca_id=None):
    query = Beca.query.filter(
        func.lower(Beca.nombre_beca) == nombre_beca.lower(),
        Beca.deleted_at.is_(None)
    )

    if fuente_financiamiento_id is None:
        query = query.filter(Beca.fuente_financiamiento_id.is_(None))
    else:
        query = query.filter(
            Beca.fuente_financiamiento_id == fuente_financiamiento_id
        )

    if beca_id is not None:
        query = query.filter(Beca.id != beca_id)

    if query.first():
        raise ValueError(
            "Ya existe una beca con ese nombre para la misma fuente de financiamiento."
        )


# =====================================================
# CRUD BECA
# =====================================================

class BecaService:

    @staticmethod
    def proximas_a_vencer(hoy: date | None = None):
        """Vínculos vigentes que finalizan en los próximos 29 días civiles."""
        hoy = hoy or date.today()
        filas = (
            db.session.query(Beca_Becario, Beca, Becario)
            .join(Beca, Beca.id == Beca_Becario.id_beca)
            .join(Becario, Becario.id == Beca_Becario.id_becario)
            .filter(
                Beca.deleted_at.is_(None),
                Becario.deleted_at.is_(None),
                Beca_Becario.deleted_at.is_(None),
                Beca_Becario.fecha_inicio <= hoy,
                Beca_Becario.fecha_fin >= hoy,
                Beca_Becario.fecha_fin < hoy + timedelta(days=30),
            )
            .order_by(Beca_Becario.fecha_fin.asc(), Becario.id.asc(), Beca.id.asc())
            .all()
        )
        return [
            {
                "vinculacion_id": relacion.id,
                "becario_id": becario.id,
                "becario": becario.nombre_apellido,
                "beca_id": beca.id,
                "beca": beca.nombre_beca,
                "fecha_fin": relacion.fecha_fin.isoformat(),
                "dias_restantes": (relacion.fecha_fin - hoy).days,
            }
            for relacion, beca, becario in filas
        ]

    @staticmethod
    def _becas_activas_query(anio: int):
        if anio is None or not 1 <= anio <= 9999:
            raise ValueError("Debe proporcionar un año válido.")

        inicio = date(anio, 1, 1)
        fin = date(anio, 12, 31)
        return (
            Beca.query.options(
                joinedload(Beca.fuente_financiamiento),
                selectinload(Beca.becarios).joinedload(Beca_Becario.becario)
                .load_only(Becario.id, Becario.nombre_apellido, Becario.deleted_at).lazyload("*"),
            )
            .join(Beca_Becario, Beca_Becario.id_beca == Beca.id)
            .join(Becario, Becario.id == Beca_Becario.id_becario)
            .filter(
                Beca.deleted_at.is_(None),
                Becario.deleted_at.is_(None),
                Beca_Becario.deleted_at.is_(None),
                Beca_Becario.fecha_inicio <= fin,
                or_(Beca_Becario.fecha_fin.is_(None), Beca_Becario.fecha_fin >= inicio),
            )
            .distinct()
            .order_by(Beca.nombre_beca.asc(), Beca.id.asc())
        )

    @staticmethod
    def get_becas_activas_en_anio(anio: int, page: int | None = None, per_page: int | None = None):
        query = BecaService._becas_activas_query(anio)
        total = query.count() if page is not None else None
        becas = (query.offset((page - 1) * per_page).limit(per_page).all()
                 if page is not None else query.all())
        data = [beca.serialize() for beca in becas]
        return (data, total) if page is not None else data

    @staticmethod
    def _list_query(activos="true", orden="asc"):
        query = Beca.query.options(
            joinedload(Beca.fuente_financiamiento),
            selectinload(Beca.becarios).joinedload(Beca_Becario.becario)
            .load_only(Becario.id, Becario.nombre_apellido, Becario.deleted_at).lazyload("*"),
        )
        if activos == "true":
            query = query.filter(Beca.deleted_at.is_(None))
        elif activos == "false":
            query = query.filter(Beca.deleted_at.isnot(None))
        nombre = Beca.nombre_beca.desc() if orden == "desc" else Beca.nombre_beca.asc()
        id_ = Beca.id.desc() if orden == "desc" else Beca.id.asc()
        return query.order_by(nombre, id_)

    @staticmethod
    def get_all(activos="true"):
        return [b.serialize() for b in BecaService._list_query(activos).all()]

    @staticmethod
    def get_page(page, per_page, activos="true", orden="asc", q=""):
        query = BecaService._list_query(activos, orden)
        term = q.strip()[:100]
        if term:
            escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            query = query.filter(or_(
                Beca.nombre_beca.ilike(f"%{escaped}%", escape="\\"),
                Beca.descripcion.ilike(f"%{escaped}%", escape="\\"),
            ))
        total = query.count()
        rows = query.offset((page - 1) * per_page).limit(per_page).all()
        return [b.serialize() for b in rows], total

    @staticmethod
    def get_by_id(beca_id):
        return _get_beca_or_404(beca_id).serialize()

    @staticmethod
    def get_historial(beca_id):
        beca = _get_beca_or_404(beca_id)
        return AuditoriaService.obtener_historial_entidad(
            entidad="beca",
            registro_id=beca.id
        )

    @staticmethod
    def create(data, user_id):
        if not data:
            raise ValueError("Los datos no pueden estar vacios.")

        nombre_beca = _validar_nombre_beca(data.get("nombre_beca"))
        fuente_financiamiento_id = _validar_fuente_financiamiento(
            data.get("fuente_financiamiento_id")
        )
        _validar_beca_unica(nombre_beca, fuente_financiamiento_id)

        nueva_beca = Beca(
            nombre_beca=nombre_beca,
            descripcion=_validar_descripcion_beca(data.get("descripcion")),
            fecha_alta_grupo=validar_fecha_alta_grupo(
                data.get("fecha_alta_grupo")
            ),
            fuente_financiamiento_id=fuente_financiamiento_id,
            created_by=user_id
        )

        db.session.add(nueva_beca)
        db.session.commit()

        return nueva_beca.serialize()

    @staticmethod
    def update(beca_id, data, user_id):
        if not data:
            raise ValueError("Los datos no pueden estar vacios.")

        beca = _get_beca_activa_or_404(beca_id)
        cambios = {}

        nombre_beca = beca.nombre_beca
        if "nombre_beca" in data:
            nombre_beca = _validar_nombre_beca(data["nombre_beca"])

        descripcion = beca.descripcion
        if "descripcion" in data:
            descripcion = _validar_descripcion_beca(data["descripcion"])

        fuente_financiamiento_id = beca.fuente_financiamiento_id
        if "fuente_financiamiento_id" in data:
            fuente_financiamiento_id = _validar_fuente_financiamiento(
                data["fuente_financiamiento_id"]
            )

        _validar_beca_unica(
            nombre_beca,
            fuente_financiamiento_id,
            beca_id=beca.id
        )

        cambio = AuditoriaService.construir_cambio(beca.nombre_beca, nombre_beca)
        if cambio:
            cambios["nombre_beca"] = cambio
            beca.nombre_beca = nombre_beca

        cambio = AuditoriaService.construir_cambio(beca.descripcion, descripcion)
        if cambio:
            cambios["descripcion"] = cambio
            beca.descripcion = descripcion

        cambio = AuditoriaService.construir_cambio(
            beca.fuente_financiamiento_id,
            fuente_financiamiento_id
        )
        if cambio:
            cambios["fuente_financiamiento_id"] = cambio
            beca.fuente_financiamiento_id = fuente_financiamiento_id

        if "fecha_alta_grupo" in data:
            nuevo_valor = validar_fecha_alta_grupo(data["fecha_alta_grupo"])
            cambio = AuditoriaService.construir_cambio(
                beca.fecha_alta_grupo,
                nuevo_valor
            )
            if cambio:
                cambios["fecha_alta_grupo"] = cambio
                beca.fecha_alta_grupo = nuevo_valor

        if cambios:
            beca.mark_updated(user_id)
            AuditoriaService.registrar_cambios(
                entidad="beca",
                registro_id=beca.id,
                cambios=cambios,
                user_id=user_id
            )

        db.session.commit()
        return beca.serialize()

    @staticmethod
    def delete(beca_id, user_id):
        beca = _get_beca_activa_or_404(beca_id)

        beca.soft_delete(user_id)
        db.session.commit()

        return {"message": "Beca eliminada correctamente."}


# =====================================================
# VINCULAR BECARIO
# =====================================================

    @staticmethod
    def vincular_becario(beca_id, data, user_id):
        if not data:
            raise ValueError("Los datos no pueden estar vacios.")

        beca = _get_beca_activa_or_404(beca_id)

        becario = db.session.get(Becario, data.get("id_becario"))
        if not becario or becario.deleted_at is not None:
            raise NotFoundError("Becario no encontrado.")

        fecha_inicio = _parsear_fecha(data.get("fecha_inicio"), "fecha_inicio")

        fecha_fin = None
        if data.get("fecha_fin"):
            fecha_fin = _parsear_fecha(data["fecha_fin"], "fecha_fin")
            if fecha_fin < fecha_inicio:
                raise ValueError(
                    "La fecha_fin no puede ser anterior a la fecha_inicio."
                )
        else:
            raise ValueError("La fecha_fin es obligatoria para registrar el plazo de la beca.")

        monto_percibido = data.get("monto_percibido")
        if monto_percibido is not None:
            try:
                monto_percibido = float(monto_percibido)
            except (TypeError, builtins.ValueError):
                raise ValueError("El monto_percibido debe ser numerico.")

            if monto_percibido < 0:
                raise ValueError("El monto_percibido no puede ser negativo.")

        existe = _get_relacion_activa(beca.id, becario.id)
        if existe:
            raise ConflictError("El becario ya está vinculado a esta beca.")

        relacion = Beca_Becario(
            id_beca=beca.id,
            id_becario=becario.id,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            monto_percibido=monto_percibido,
            created_by=user_id
        )

        db.session.add(relacion)
        beca.mark_updated(user_id)
        AuditoriaService.registrar_evento_relacion(
            entidad="beca",
            registro_id=beca.id,
            relacion="becarios",
            accion="vincular",
            detalle={
                "becario_id": becario.id,
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "monto_percibido": monto_percibido
            },
            user_id=user_id
        )
        db.session.commit()

        return {"message": "Becario vinculado correctamente."}


# =====================================================
# DESVINCULAR (SOFT DELETE)
# =====================================================

    @staticmethod
    def desvincular_becario(beca_id, becario_id, user_id):

        relacion = _get_relacion_activa(beca_id, becario_id)

        if not relacion:
            raise NotFoundError("La relación no existe.")

        relacion.soft_delete(user_id)
        beca = _get_beca_activa_or_404(beca_id)
        beca.mark_updated(user_id)
        AuditoriaService.registrar_evento_relacion(
            entidad="beca",
            registro_id=beca_id,
            relacion="becarios",
            accion="desvincular",
            detalle={
                "becario_id": becario_id,
                "fecha_inicio": relacion.fecha_inicio,
                "fecha_fin": relacion.fecha_fin,
                "monto_percibido": relacion.monto_percibido
            },
            user_id=user_id
        )
        db.session.commit()

        return {"message": "Becario desvinculado correctamente."}


# =====================================================
# LISTAR BECARIOS DE UNA BECA
# =====================================================

    @staticmethod
    def get_becarios_de_beca(beca_id, page: int | None = None, per_page: int | None = None):

        beca = _get_beca_activa_or_404(beca_id)

        query = Beca_Becario.query.filter(
            Beca_Becario.id_beca == beca.id, Beca_Becario.deleted_at.is_(None)
        ).options(
            joinedload(Beca_Becario.becario)
            .load_only(Becario.id, Becario.nombre_apellido).lazyload("*"),
        ).order_by(Beca_Becario.id.asc())
        total = query.count() if page is not None else None
        relaciones = (query.offset((page - 1) * per_page).limit(per_page).all()
                      if page is not None else query.all())
        resultado = []
        for r in relaciones:
            if r.deleted_at is None:
                resultado.append({
                    "id_becario": r.becario.id,
                    "nombre": r.becario.nombre_apellido,
                    "fecha_inicio": r.fecha_inicio,
                    "fecha_fin": r.fecha_fin,
                    "monto_percibido": r.monto_percibido
                })

        return (resultado, total) if page is not None else resultado
    
    
    # =========================
    # DASHBOARD POR AÑO (AUDITORÍA)
    # =========================
    @staticmethod
    def dashboard_por_anio(anio: int):

        if not anio:
            raise ValueError("Debe proporcionar un año.")

        relaciones = (
            Beca_Becario.query.options(
                joinedload(Beca_Becario.becario).lazyload("*"),
                joinedload(Beca_Becario.becario).joinedload(Becario.tipo_formacion),
                joinedload(Beca_Becario.becario).joinedload(Becario.grupo_utn).lazyload("*"),
            )
            .join(Beca, Beca.id == Beca_Becario.id_beca)
            .join(Becario, Becario.id == Beca_Becario.id_becario)
            .filter(
                # SOLO registros activos
                Beca.deleted_at.is_(None),
                Becario.deleted_at.is_(None),
                Beca_Becario.deleted_at.is_(None),

                # Rango temporal
                extract("year", Beca_Becario.fecha_inicio) <= anio,
                or_(
                    Beca_Becario.fecha_fin == None,
                    extract("year", Beca_Becario.fecha_fin) >= anio
                )
            )
            .all()
        )

        if not relaciones:
            return {
                "anio": anio,
                "total_becarios_activos": 0,
                "monto_total_invertido": 0,
                "promedio_monto": 0,
                "por_tipo_formacion": {},
                "por_grupo": {}
            }

        total_becarios = len(relaciones)

        monto_total = sum(
            r.monto_percibido or 0
            for r in relaciones
        )

        promedio = monto_total / total_becarios if total_becarios else 0

        # Agrupar por tipo de formación
        por_tipo = {}
        for r in relaciones:
            tipo = r.becario.tipo_formacion.nombre
            por_tipo[tipo] = por_tipo.get(tipo, 0) + 1

        # Agrupar por grupo
        por_grupo = {}
        for r in relaciones:
            grupo = r.becario.grupo_utn.nombre_sigla_grupo
            por_grupo[grupo] = por_grupo.get(grupo, 0) + 1

        return {
            "anio": anio,
            "total_becarios_activos": total_becarios,
            "monto_total_invertido": monto_total,
            "promedio_monto": round(promedio, 2),
            "por_tipo_formacion": por_tipo,
            "por_grupo": por_grupo
        }
