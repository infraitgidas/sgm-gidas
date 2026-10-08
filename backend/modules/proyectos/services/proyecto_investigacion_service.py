from modules.memorias.services.memoria_periodo_service import (
    consultar_entidades_memoria, fin_vigencia,
)
from datetime import datetime, date, timedelta
from calendar import monthrange
import builtins
import re

from extension import db
from modules.shared.services.text_validation import has_letter
from sqlalchemy import and_, case, false, func, or_
from sqlalchemy.orm import joinedload, selectinload
from modules.shared.exceptions import ConflictError, NotFoundError, ValidationError as ValueError

from modules.produccion.models.distinciones import DistincionRecibida
from modules.proyectos.models.proyecto_investigacion import (
    ProyectoInvestigacion,
    TipoProyecto,
    InvestigadorProyecto,
    BecarioProyecto,
    ProyectoInvestigacionMemoriaVersion
)
from modules.grupo.models.grupo import GrupoInvestigacionUtn
from modules.catalogos.models.fuente_financiamiento import FuenteFinanciamiento
from modules.personal.models.personal import Becario, Investigador
from modules.shared.services.auditoria_service import AuditoriaService
from modules.shared.services.date_time import validate_institutional_date
from modules.memorias.services.memoria_periodo_service import estuvo_activo_en_periodo_memoria
from modules.informes.services.cierre_proyecto import informe_de_cierre_predicate, tiene_informe_de_cierre


class ProyectoInvestigacionService:
    @staticmethod
    def _serializar_lista(items):
        if not items:
            return []
        ids = [item.id for item in items]
        closed_ids = {project_id for (project_id,) in db.session.query(ProyectoInvestigacion.id).filter(
            ProyectoInvestigacion.id.in_(ids),
            ProyectoInvestigacion.deleted_at.isnot(None),
            ProyectoInvestigacion.fecha_fin <= date.today(),
            informe_de_cierre_predicate(ProyectoInvestigacion.id, ProyectoInvestigacion.fecha_fin, ProyectoInvestigacion.grupo_utn_id),
        ).all()}
        return [item.serialize(cerrado_override=item.id in closed_ids) for item in items]


    @staticmethod
    def _sumar_meses(fecha: date, meses: int) -> date:
        indice = fecha.year * 12 + fecha.month - 1 + meses
        anio, mes = divmod(indice, 12)
        return date(anio, mes + 1, min(fecha.day, monthrange(anio, mes + 1)[1]))

    @staticmethod
    def _fin_inclusivo(fecha: date, meses: int) -> date:
        aniversario = ProyectoInvestigacionService._sumar_meses(fecha, meses)
        # El 29/02 conserva el último día de febrero al pasar a un año no bisiesto.
        if fecha.day > monthrange(aniversario.year, aniversario.month)[1]:
            return aniversario
        return aniversario - timedelta(days=1)

    @staticmethod
    def _validar_duracion(fecha_inicio: date, fecha_fin: date | None):
        mensaje = "La duración inicial debe ser de 12 a 36 meses inclusive."
        if fecha_fin is None or not (
            ProyectoInvestigacionService._fin_inclusivo(fecha_inicio, 12)
            <= fecha_fin <=
            ProyectoInvestigacionService._fin_inclusivo(fecha_inicio, 36)
        ):
            raise ValueError(mensaje, details={"fields": {"fecha_fin": mensaje}})

    CODIGO_PROYECTO_MAX_LENGTH = 50
    CODIGO_PROYECTO_PATTERN = re.compile(r"^[A-Za-z0-9]+$")
    LIST_SORTS = {
        "codigo": ProyectoInvestigacion.codigo_proyecto,
        "nombre": ProyectoInvestigacion.nombre_proyecto,
        "tipo": TipoProyecto.nombre,
        "fuente": FuenteFinanciamiento.nombre,
        "fecha_inicio": ProyectoInvestigacion.fecha_inicio,
        "fecha_fin": ProyectoInvestigacion.fecha_fin,
        "estado": case(
            (
                or_(
                    ProyectoInvestigacion.deleted_at.isnot(None),
                    ProyectoInvestigacion.activo.is_(False),
                ),
                1,
            ),
            else_=0,
        ),
    }

    @staticmethod
    def _validar_codigo_proyecto(valor):
        campo = "codigo_proyecto"

        if not isinstance(valor, str):
            mensaje = "El código del proyecto debe ser una cadena alfanumérica."
            raise ValueError(mensaje, details={"fields": {campo: mensaje}})

        codigo = valor.strip()
        if not codigo:
            mensaje = "El código del proyecto es obligatorio."
            raise ValueError(mensaje, details={"fields": {campo: mensaje}})

        if len(codigo) > ProyectoInvestigacionService.CODIGO_PROYECTO_MAX_LENGTH:
            mensaje = "El código del proyecto no puede superar los 50 caracteres."
            raise ValueError(mensaje, details={"fields": {campo: mensaje}})

        if not ProyectoInvestigacionService.CODIGO_PROYECTO_PATTERN.fullmatch(codigo):
            mensaje = "El código del proyecto solo puede contener letras y números."
            raise ValueError(mensaje, details={"fields": {campo: mensaje}})

        return codigo

    @staticmethod
    def _validar_id(valor, campo: str):
        if type(valor) is not int or valor <= 0:
            raise ValueError(f"El campo '{campo}' debe ser un entero positivo", details={"fields": {campo: "Seleccione una opción válida"}})
        return valor

    @staticmethod
    def _validar_fecha_proyecto(valor, campo: str):
        try:
            fecha = datetime.strptime(valor, "%Y-%m-%d").date()
        except (TypeError, builtins.ValueError) as error:
            raise ValueError("Ingrese una fecha válida.", details={"fields": {campo: "Ingrese una fecha válida en formato YYYY-MM-DD"}}) from error
        try:
            return validate_institutional_date(fecha, campo)
        except ValueError as error:
            raise ValueError(str(error), details={"fields": {campo: str(error)}}) from error

    @staticmethod
    def _validar_bool(valor, campo: str, default=False):
        if valor is None:
            return default
        if not isinstance(valor, bool):
            raise ValueError(f"El campo '{campo}' debe ser booleano")
        return valor

    @staticmethod
    def _normalizar_activos(activos):
        if activos is None:
            return "true"
        return str(activos).strip().lower()

    @staticmethod
    def _validar_fecha_participacion(fecha_str, campo: str, permitir_none=False):
        if fecha_str is None and permitir_none:
            return None

        try:
            fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except (TypeError, builtins.ValueError):
            raise ValueError(
                f"El campo '{campo}' debe tener formato YYYY-MM-DD",
                details={"fields": {campo: "Ingrese una fecha válida en formato YYYY-MM-DD"}},
            )
        try:
            return validate_institutional_date(fecha, campo)
        except ValueError as error:
            raise ValueError(str(error), details={"fields": {campo: str(error)}}) from error

    @staticmethod
    def _validar_investigador_activo(investigador_id):
        investigador_id = ProyectoInvestigacionService._validar_id(
            investigador_id, "id_investigador"
        )
        investigador = db.session.get(Investigador, investigador_id)
        if not investigador or investigador.deleted_at is not None or not investigador.activo:
            raise ValueError('Seleccione un investigador disponible e intente nuevamente.', details={"fields": {'id_investigador': 'Seleccione un investigador disponible e intente nuevamente.'}})
        return investigador_id

    @staticmethod
    def _query_proyecto_activo_bloqueado(proyecto_id: int):
        return ProyectoInvestigacion.query.filter_by(
            id=proyecto_id,
            deleted_at=None
        ).with_for_update(of=ProyectoInvestigacion)

    @staticmethod
    def _get_proyecto_activo_or_404(proyecto_id: int):
        proyecto = ProyectoInvestigacionService._query_proyecto_activo_bloqueado(
            proyecto_id
        ).first()

        if not proyecto:
            raise NotFoundError("Proyecto no encontrado.")

        return proyecto

    @staticmethod
    def _get_proyecto_or_404(proyecto_id: int):
        proyecto = db.session.get(
            ProyectoInvestigacion,
            ProyectoInvestigacionService._validar_id(proyecto_id, "proyecto_id")
        )

        if not proyecto:
            raise NotFoundError("Proyecto no encontrado.")

        return proyecto

    @staticmethod
    def _proyecto_esta_cerrado(proyecto: ProyectoInvestigacion):
        return bool(proyecto.deleted_at and proyecto.fecha_fin and proyecto.fecha_fin <= date.today() and tiene_informe_de_cierre(proyecto.id, proyecto.fecha_fin, grupo_utn_id=proyecto.grupo_utn_id))

    @staticmethod
    def _validar_proyecto_abierto(proyecto: ProyectoInvestigacion):
        if ProyectoInvestigacionService._proyecto_esta_cerrado(proyecto):
            raise ConflictError("El proyecto se encuentra cerrado.")

    @staticmethod
    def _validar_unico_coordinador_activo(
        proyecto_id: int,
        nuevas_participaciones: list[dict]
    ):
        coordinador_activo_existente = InvestigadorProyecto.query.filter(
            InvestigadorProyecto.id_proyecto == proyecto_id,
            InvestigadorProyecto.deleted_at.is_(None),
            InvestigadorProyecto.es_coordinador.is_(True)
        ).first()

        coordinadores_nuevos = [
            item for item in nuevas_participaciones
            if ProyectoInvestigacionService._validar_bool(
                item.get("es_coordinador"), "es_coordinador", default=False
            )
        ]

        if len(coordinadores_nuevos) > 1:
            raise ValueError(
                "Un proyecto solo puede tener un investigador coordinador activo"
            )

        if coordinador_activo_existente and coordinadores_nuevos:
            if (
                coordinadores_nuevos[0].get("id_investigador")
                == coordinador_activo_existente.id_investigador
            ):
                return
            raise ValueError(
                "El proyecto ya tiene un investigador coordinador activo"
            )

    @staticmethod
    def _participacion_investigador_es_igual(
        participacion: InvestigadorProyecto,
        es_coordinador: bool,
        fecha_inicio: date,
        fecha_fin: date | None
    ):
        return (
            participacion.es_coordinador == es_coordinador
            and participacion.fecha_inicio == fecha_inicio
            and participacion.fecha_fin == fecha_fin
        )

    # =========================
    # GET ALL
    # =========================
    @staticmethod
    def get_all(filters: dict = None):
        filters = filters or {}
        query = ProyectoInvestigacion.query

        activos = ProyectoInvestigacionService._normalizar_activos(
            filters.get("activos")
        )
        if activos == "true":
            query = query.filter(
                ProyectoInvestigacion.deleted_at.is_(None),
                ProyectoInvestigacion.activo.is_(True),
            )
        elif activos == "false":
            query = query.filter(
                or_(
                    ProyectoInvestigacion.deleted_at.isnot(None),
                    ProyectoInvestigacion.activo.is_(False),
                )
            )
        elif activos != "all":
            query = query.filter(
                ProyectoInvestigacion.deleted_at.is_(None),
                ProyectoInvestigacion.activo.is_(True)
            )

        if filters.get("tipo_proyecto_id"):
            query = query.filter(
                ProyectoInvestigacion.tipo_proyecto_id == filters["tipo_proyecto_id"]
            )

        if filters.get("grupo_utn_id"):
            query = query.filter(
                ProyectoInvestigacion.grupo_utn_id == filters["grupo_utn_id"]
            )

        if filters.get("tiene_distinciones"):
            query = query.filter(
                ProyectoInvestigacion.distinciones.any(
                    DistincionRecibida.deleted_at.is_(None)
                )
            )

        orden = filters.get("orden")

        if orden == "asc":
            query = query.order_by(ProyectoInvestigacion.fecha_inicio.asc())
        elif orden == "monto_asc":
            query = query.order_by(ProyectoInvestigacion.monto_destinado.asc())
        elif orden == "monto_desc":
            query = query.order_by(ProyectoInvestigacion.monto_destinado.desc())
        else:
            query = query.order_by(ProyectoInvestigacion.fecha_inicio.desc())

        return ProyectoInvestigacionService._serializar_lista(query.all())

    @staticmethod
    def get_page(
        *,
        activos="true",
        page=1,
        per_page=9,
        search=None,
        sort="fecha_inicio",
        direction="desc",
        tipo_proyecto_id=None,
        fuente_financiamiento_id=None,
        investigador_id=None,
        becario_id=None,
        ids=None,
    ):
        activos = ProyectoInvestigacionService._normalizar_activos(activos)
        sort = str(sort or "fecha_inicio").strip().lower()
        direction = str(direction or "desc").strip().lower()

        if activos not in {"true", "false", "all"}:
            raise ValueError("El filtro de estado no es válido.")
        if sort not in ProyectoInvestigacionService.LIST_SORTS:
            raise ValueError("El campo de ordenamiento no es válido.")
        if direction not in {"asc", "desc"}:
            raise ValueError("La dirección de ordenamiento no es válida.")
        if not isinstance(page, int) or page <= 0:
            raise ValueError("La página debe ser un entero positivo.")
        if not isinstance(per_page, int) or per_page <= 0 or per_page > 9:
            raise ValueError("La cantidad por página debe estar entre 1 y 9.")
        if ids is not None and (
            not isinstance(ids, list)
            or any(type(item) is not int or item <= 0 for item in ids)
        ):
            raise ValueError("Los IDs deben ser enteros positivos.")

        query = ProyectoInvestigacion.query.outerjoin(
            TipoProyecto,
            ProyectoInvestigacion.tipo_proyecto_id == TipoProyecto.id,
        ).outerjoin(
            FuenteFinanciamiento,
            ProyectoInvestigacion.fuente_financiamiento_id
            == FuenteFinanciamiento.id,
        ).options(
            joinedload(ProyectoInvestigacion.tipo_proyecto),
            joinedload(ProyectoInvestigacion.fuente_financiamiento),
            joinedload(ProyectoInvestigacion.grupo_utn),
            selectinload(
                ProyectoInvestigacion.participaciones_investigador
            ).lazyload("*"),
            selectinload(
                ProyectoInvestigacion.participaciones_investigador
            ).joinedload(InvestigadorProyecto.investigador).load_only(
                Investigador.id, Investigador.nombre_apellido,
                Investigador.activo, Investigador.deleted_at,
            ).lazyload("*"),
            selectinload(
                ProyectoInvestigacion.participaciones_becario
            ).lazyload("*"),
            selectinload(
                ProyectoInvestigacion.participaciones_becario
            ).joinedload(BecarioProyecto.becario).load_only(
                Becario.id, Becario.nombre_apellido,
            ).lazyload("*"),
            selectinload(ProyectoInvestigacion.distinciones),
        )

        if activos == "true":
            query = query.filter(
                ProyectoInvestigacion.deleted_at.is_(None),
                ProyectoInvestigacion.activo.is_(True),
            )
        elif activos == "false":
            query = query.filter(or_(
                ProyectoInvestigacion.deleted_at.isnot(None),
                ProyectoInvestigacion.activo.is_(False),
            ))

        term = str(search or "").strip().lower()
        if term:
            pattern = f"%{term}%"
            query = query.filter(or_(
                func.lower(ProyectoInvestigacion.codigo_proyecto).like(pattern),
                func.lower(ProyectoInvestigacion.nombre_proyecto).like(pattern),
                func.lower(ProyectoInvestigacion.descripcion_proyecto).like(pattern),
                func.lower(func.coalesce(TipoProyecto.nombre, "")).like(pattern),
                func.lower(func.coalesce(FuenteFinanciamiento.nombre, "")).like(pattern),
                ProyectoInvestigacion.participaciones_investigador.any(
                    and_(
                        InvestigadorProyecto.deleted_at.is_(None),
                        InvestigadorProyecto.investigador.has(
                            func.lower(Investigador.nombre_apellido).like(pattern)
                        ),
                    ),
                ),
                ProyectoInvestigacion.participaciones_becario.any(
                    and_(
                        BecarioProyecto.deleted_at.is_(None),
                        BecarioProyecto.becario.has(
                            func.lower(Becario.nombre_apellido).like(pattern)
                        ),
                    ),
                ),
            ))

        if tipo_proyecto_id:
            query = query.filter(
                ProyectoInvestigacion.tipo_proyecto_id == tipo_proyecto_id
            )
        if fuente_financiamiento_id:
            query = query.filter(
                ProyectoInvestigacion.fuente_financiamiento_id
                == fuente_financiamiento_id
            )
        if investigador_id:
            query = query.filter(
                ProyectoInvestigacion.participaciones_investigador.any(
                    and_(
                        InvestigadorProyecto.id_investigador == investigador_id,
                        InvestigadorProyecto.deleted_at.is_(None),
                    )
                )
            )
        if becario_id:
            query = query.filter(
                ProyectoInvestigacion.participaciones_becario.any(
                    and_(
                        BecarioProyecto.id_becario == becario_id,
                        BecarioProyecto.deleted_at.is_(None),
                    )
                )
            )
        if ids is not None:
            query = query.filter(
                ProyectoInvestigacion.id.in_(ids) if ids else false()
            )

        total = query.count()
        column = ProyectoInvestigacionService.LIST_SORTS[sort]
        order = column.asc() if direction == "asc" else column.desc()
        items = (
            query.order_by(order, ProyectoInvestigacion.id.asc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return {
            "data": ProyectoInvestigacionService._serializar_lista(items),
            "meta": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": (total + per_page - 1) // per_page,
            },
            "error": None,
        }

    # =========================
    # GET BY ID
    # =========================
    @staticmethod
    def get_by_id(proyecto_id: int):

        proyecto = ProyectoInvestigacion.query.get(proyecto_id)

        if not proyecto:
            raise NotFoundError("Proyecto de investigacion no encontrado")

        return proyecto.serialize()

    # =========================
    # CREATE
    # =========================
    @staticmethod
    def _validar_logros(value):
        if value is not None and (not isinstance(value, str) or len(value) > 20000):
            raise ValueError("Revise los campos indicados e intente nuevamente.", details={"fields": {
                "logros_obtenidos": "Ingrese un texto de hasta 20000 caracteres."
            }})
        return value.strip() or None if isinstance(value, str) else None

    @staticmethod
    def create(data: dict, user_id: int, *, commit=True):
        codigo_proyecto = ProyectoInvestigacionService._validar_codigo_proyecto(
            data.get("codigo_proyecto")
        )
        if not has_letter(data.get("nombre_proyecto")):
            raise ValueError("Revise los campos indicados e intente nuevamente.", details={"fields": {"nombre_proyecto": "El nombre del proyecto debe contener letras."}})

        fecha_inicio = ProyectoInvestigacionService._validar_fecha_proyecto(data.get("fecha_inicio"), "fecha_inicio")

        fecha_fin = ProyectoInvestigacionService._validar_fecha_proyecto(data.get("fecha_fin"), "fecha_fin") if data.get("fecha_fin") else None
        ProyectoInvestigacionService._validar_duracion(fecha_inicio, fecha_fin)

        if not TipoProyecto.query.get(data.get("tipo_proyecto_id")):
            raise ValueError('Seleccione un tipo de proyecto disponible e intente nuevamente.', details={"fields": {'tipo_proyecto_id': 'Seleccione un tipo de proyecto disponible e intente nuevamente.'}})
        
        if data.get("fuente_financiamiento_id"):
            fuente = FuenteFinanciamiento.query.get(data["fuente_financiamiento_id"])
            if not fuente:
                raise ValueError('Seleccione una fuente de financiamiento disponible e intente nuevamente.', details={"fields": {'fuente_financiamiento_id': 'Seleccione una fuente de financiamiento disponible e intente nuevamente.'}})
            
        if data.get("grupo_utn_id"):
            grupo = GrupoInvestigacionUtn.query.get(data["grupo_utn_id"])
            if not grupo:
                raise ValueError('Seleccione un grupo disponible e intente nuevamente.', details={"fields": {'grupo_utn_id': 'Seleccione un grupo disponible e intente nuevamente.'}})
            
        if data.get("tipo_proyecto_id"):
            tipo = TipoProyecto.query.get(data["tipo_proyecto_id"])
            if not tipo:
                raise ValueError('Seleccione un tipo de proyecto disponible e intente nuevamente.', details={"fields": {'tipo_proyecto_id': 'Seleccione un tipo de proyecto disponible e intente nuevamente.'}})

        proyecto = ProyectoInvestigacion(
            codigo_proyecto=codigo_proyecto,
            nombre_proyecto=data["nombre_proyecto"],
            descripcion_proyecto=data["descripcion_proyecto"],
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            fecha_fin_original=fecha_fin,
            logros_obtenidos=ProyectoInvestigacionService._validar_logros(data.get("logros_obtenidos")),
            dificultades_proyecto=data.get("dificultades_proyecto"),
            monto_destinado=data.get("monto_destinado"),
            tipo_proyecto_id=data["tipo_proyecto_id"],
            grupo_utn_id=data.get("grupo_utn_id"),
            fuente_financiamiento_id=data.get("fuente_financiamiento_id"),
            created_by=user_id
        )

        db.session.add(proyecto)
        if commit:
            db.session.commit()
        else:
            db.session.flush()

        return proyecto.serialize()

    # =========================
    # UPDATE
    # =========================
    @staticmethod
    def update(proyecto_id: int, data: dict, user_id: int = None, *, commit=True):

        proyecto = ProyectoInvestigacion.query.filter_by(
            id=proyecto_id,
            deleted_at=None
        ).first()

        if not proyecto:
            raise NotFoundError("Proyecto no encontrado")

        if user_id is not None:
            ProyectoInvestigacionService._validar_id(user_id, "user_id")
        if getattr(proyecto, "fecha_fin_prorrogada", None) and ({"fecha_inicio", "fecha_fin"} & data.keys()):
            raise ConflictError("No se pueden modificar las fechas de un proyecto prorrogado.")
        cambios = {}
        if "logros_obtenidos" in data:
            data = {**data, "logros_obtenidos": ProyectoInvestigacionService._validar_logros(data["logros_obtenidos"])}

        if "codigo_proyecto" in data:
            codigo_proyecto = ProyectoInvestigacionService._validar_codigo_proyecto(
                data["codigo_proyecto"]
            )
            cambio = AuditoriaService.construir_cambio(
                proyecto.codigo_proyecto,
                codigo_proyecto
            )
            if cambio:
                cambios["codigo_proyecto"] = cambio
                proyecto.codigo_proyecto = codigo_proyecto

        for field in [
            "nombre_proyecto",
            "descripcion_proyecto",
            "logros_obtenidos",
            "dificultades_proyecto",
            "monto_destinado"
        ]:
            if field in data:
                if field == "nombre_proyecto" and not has_letter(data[field]):
                    raise ValueError("Revise los campos indicados e intente nuevamente.", details={"fields": {"nombre_proyecto": "El nombre del proyecto debe contener letras."}})
                cambio = AuditoriaService.construir_cambio(
                    getattr(proyecto, field),
                    data[field]
                )
                if cambio:
                    cambios[field] = cambio
                    setattr(proyecto, field, data[field])

        if "tipo_proyecto_id" in data:
            tipo_proyecto_id = data["tipo_proyecto_id"]
            if not isinstance(tipo_proyecto_id, int) or tipo_proyecto_id <= 0:
                raise ValueError('Seleccione un tipo de proyecto disponible e intente nuevamente.', details={"fields": {'tipo_proyecto_id': 'Seleccione un tipo de proyecto disponible e intente nuevamente.'}})

            if not TipoProyecto.query.get(tipo_proyecto_id):
                raise ValueError('Seleccione un tipo de proyecto disponible e intente nuevamente.', details={"fields": {'tipo_proyecto_id': 'Seleccione un tipo de proyecto disponible e intente nuevamente.'}})

            cambio = AuditoriaService.construir_cambio(
                proyecto.tipo_proyecto_id,
                tipo_proyecto_id
            )
            if cambio:
                cambios["tipo_proyecto_id"] = cambio
                proyecto.tipo_proyecto_id = tipo_proyecto_id

        if "grupo_utn_id" in data:
            grupo_utn_id = data["grupo_utn_id"]
            if grupo_utn_id in (None, ""):
                cambio = AuditoriaService.construir_cambio(
                    proyecto.grupo_utn_id,
                    None
                )
                if cambio:
                    cambios["grupo_utn_id"] = cambio
                    proyecto.grupo_utn_id = None
            else:
                if not isinstance(grupo_utn_id, int) or grupo_utn_id <= 0:
                    raise ValueError('Seleccione un grupo disponible e intente nuevamente.', details={"fields": {'grupo_utn_id': 'Seleccione un grupo disponible e intente nuevamente.'}})

                if not GrupoInvestigacionUtn.query.get(grupo_utn_id):
                    raise ValueError('Seleccione un grupo disponible e intente nuevamente.', details={"fields": {'grupo_utn_id': 'Seleccione un grupo disponible e intente nuevamente.'}})

                cambio = AuditoriaService.construir_cambio(
                    proyecto.grupo_utn_id,
                    grupo_utn_id
                )
                if cambio:
                    cambios["grupo_utn_id"] = cambio
                    proyecto.grupo_utn_id = grupo_utn_id

        if "fuente_financiamiento_id" in data:
            fuente_financiamiento_id = data["fuente_financiamiento_id"]
            if fuente_financiamiento_id in (None, ""):
                cambio = AuditoriaService.construir_cambio(
                    proyecto.fuente_financiamiento_id,
                    None
                )
                if cambio:
                    cambios["fuente_financiamiento_id"] = cambio
                    proyecto.fuente_financiamiento_id = None
            else:
                if (
                    not isinstance(fuente_financiamiento_id, int)
                    or fuente_financiamiento_id <= 0
                ):
                    raise ValueError('Seleccione una fuente de financiamiento disponible e intente nuevamente.', details={"fields": {'fuente_financiamiento_id': 'Seleccione una fuente de financiamiento disponible e intente nuevamente.'}})

                if not FuenteFinanciamiento.query.get(fuente_financiamiento_id):
                    raise ValueError('Seleccione una fuente de financiamiento disponible e intente nuevamente.', details={"fields": {'fuente_financiamiento_id': 'Seleccione una fuente de financiamiento disponible e intente nuevamente.'}})

                cambio = AuditoriaService.construir_cambio(
                    proyecto.fuente_financiamiento_id,
                    fuente_financiamiento_id
                )
                if cambio:
                    cambios["fuente_financiamiento_id"] = cambio
                    proyecto.fuente_financiamiento_id = fuente_financiamiento_id

        if "fecha_inicio" in data:
            nueva_fecha = ProyectoInvestigacionService._validar_fecha_proyecto(data["fecha_inicio"], "fecha_inicio")
            cambio = AuditoriaService.construir_cambio(
                proyecto.fecha_inicio,
                nueva_fecha
            )
            if cambio:
                cambios["fecha_inicio"] = cambio
                proyecto.fecha_inicio = nueva_fecha

        if "fecha_fin" in data:
            nueva_fecha_fin = ProyectoInvestigacionService._validar_fecha_proyecto(data["fecha_fin"], "fecha_fin") if data["fecha_fin"] else None
            cambio = AuditoriaService.construir_cambio(
                proyecto.fecha_fin,
                nueva_fecha_fin
            )
            if cambio:
                cambios["fecha_fin"] = cambio
                proyecto.fecha_fin = nueva_fecha_fin

        if {"fecha_inicio", "fecha_fin"} & data.keys():
            ProyectoInvestigacionService._validar_duracion(proyecto.fecha_inicio, proyecto.fecha_fin)
            proyecto.fecha_fin_original = proyecto.fecha_fin

        if cambios and user_id is not None:
            proyecto.mark_updated(user_id)
            AuditoriaService.registrar_cambios(
                entidad="proyecto_investigacion",
                registro_id=proyecto.id,
                cambios=cambios,
                user_id=user_id
            )

        if commit:
            db.session.commit()
        else:
            db.session.flush()
        return proyecto.serialize()

    @staticmethod
    def prorrogar_proyecto(proyecto_id: int, data: dict, user_id: int):
        proyecto = ProyectoInvestigacionService._get_proyecto_activo_or_404(proyecto_id)
        ProyectoInvestigacionService._validar_id(user_id, "user_id")
        if not getattr(proyecto, "activo", True):
            raise ConflictError("No se puede prorrogar un proyecto inactivo.")
        if not isinstance(data, dict):
            raise ValueError("Envíe una justificación válida.", details={"fields": {"motivo": "La justificación es obligatoria."}})
        motivo = data.get("motivo")
        if not isinstance(motivo, str) or not motivo.strip():
            raise ValueError("La justificación es obligatoria.", details={"fields": {"motivo": "La justificación es obligatoria."}})
        motivo = " ".join(motivo.split())
        if len(motivo) < 10 or len(motivo) > 2000:
            raise ValueError("La justificación debe tener entre 10 y 2000 caracteres.", details={"fields": {"motivo": "Ingrese entre 10 y 2000 caracteres."}})
        if proyecto.fecha_fin_prorrogada:
            raise ConflictError("El proyecto ya tiene una prórroga.")
        original = proyecto.fecha_fin_original or proyecto.fecha_fin
        if not original:
            raise ConflictError("Defina primero la fecha de fin inicial del proyecto.")
        ProyectoInvestigacionService._validar_duracion(proyecto.fecha_inicio, original)
        nueva_fecha = ProyectoInvestigacionService._fin_inclusivo(original + timedelta(days=1), 12)
        proyecto.fecha_fin_original = original
        proyecto.fecha_fin_prorrogada = nueva_fecha
        proyecto.fecha_fin = nueva_fecha
        proyecto.prorroga_motivo = motivo
        proyecto.prorroga_by = user_id
        proyecto.prorroga_at = datetime.utcnow()
        proyecto.mark_updated(user_id)
        AuditoriaService.registrar_cambios("proyecto_investigacion", proyecto.id, {
            "prorroga": {"valor_anterior": {"fecha_fin": original.isoformat()}, "valor_nuevo": {
                "fecha_fin": nueva_fecha.isoformat(), "motivo": motivo,
            }}
        }, user_id)
        db.session.commit()
        return proyecto.serialize()

    # =========================
    # CERRAR PROYECTO
    # =========================
    @staticmethod
    def cerrar_proyecto(proyecto_id: int, user_id: int, fecha_fin=None):
        proyecto = ProyectoInvestigacionService._get_proyecto_activo_or_404(
            proyecto_id
        )
        ProyectoInvestigacionService._validar_id(user_id, "user_id")

        if ProyectoInvestigacionService._proyecto_esta_cerrado(proyecto):
            raise ConflictError("El proyecto ya se encuentra cerrado")

        cierre = ProyectoInvestigacionService._validar_fecha_proyecto(fecha_fin, "fecha_fin") if fecha_fin else date.today()
        if not tiene_informe_de_cierre(proyecto.id, cierre, grupo_utn_id=proyecto.grupo_utn_id):
            raise ConflictError("Debe registrar un informe PID del período de la Memoria que contiene la fecha de cierre.")
        if cierre > date.today() or cierre < proyecto.fecha_inicio:
            raise ValueError("Ingrese una fecha de cierre válida.", details={"fields": {"fecha_fin": "Elija una fecha entre el inicio y hoy."}})
        cambio = AuditoriaService.construir_cambio(proyecto.fecha_fin, cierre)
        proyecto.fecha_fin = cierre
        proyecto.soft_delete(user_id)
        if cambio:
            AuditoriaService.registrar_cambios("proyecto_investigacion", proyecto.id, {"fecha_fin": cambio}, user_id)
        db.session.commit()

        return {"message": "Proyecto cerrado correctamente"}

    # =========================
    # REABRIR PROYECTO
    # =========================
    @staticmethod
    def reabrir_proyecto(proyecto_id: int):
        proyecto = ProyectoInvestigacionService._get_proyecto_or_404(
            proyecto_id
        )
        if proyecto.deleted_at is None and not ProyectoInvestigacionService._proyecto_esta_cerrado(proyecto):
            raise ConflictError("El proyecto no se encuentra cerrado")

        if proyecto.fecha_fin_prorrogada and proyecto.fecha_fin_prorrogada <= date.today():
            raise ConflictError("No se puede reabrir un proyecto cuya prórroga ya venció.")

        proyecto.restore()
        proyecto.fecha_fin = proyecto.fecha_fin_prorrogada or None
        db.session.commit()

        return {"message": "Proyecto reabierto correctamente"}

    # =====================================================
    # VINCULAR / DESVINCULAR INVESTIGADORES
    # =====================================================

    @staticmethod
    def vincular_investigadores_a_proyecto(proyecto_id, participaciones):
        proyecto = ProyectoInvestigacionService._get_proyecto_activo_or_404(
            proyecto_id
        )
        ProyectoInvestigacionService._validar_proyecto_abierto(proyecto)

        if not isinstance(participaciones, list) or not participaciones:
            raise ValueError("Debe enviarse una lista de participaciones.")

        ProyectoInvestigacionService._validar_unico_coordinador_activo(
            proyecto_id,
            participaciones
        )

        for item in participaciones:

            investigador_id = ProyectoInvestigacionService._validar_investigador_activo(
                item.get("id_investigador")
            )
            es_coordinador = ProyectoInvestigacionService._validar_bool(
                item.get("es_coordinador"), "es_coordinador", default=False
            )
            fecha_inicio = ProyectoInvestigacionService._validar_fecha_participacion(
                item.get("fecha_inicio"), "fecha_inicio"
            )
            fecha_fin = ProyectoInvestigacionService._validar_fecha_participacion(
                item.get("fecha_fin"), "fecha_fin", permitir_none=True
            )

            if fecha_fin and fecha_fin < fecha_inicio:
                raise ValueError(
                    "La fecha_fin no puede ser anterior a la fecha_inicio."
                )

            existente = InvestigadorProyecto.query.filter_by(
                id_proyecto=proyecto_id,
                id_investigador=investigador_id,
                deleted_at=None
            ).first()

            if existente:
                if ProyectoInvestigacionService._participacion_investigador_es_igual(
                    existente,
                    es_coordinador,
                    fecha_inicio,
                    fecha_fin
                ):
                    continue

                raise ConflictError("Ya existe una participación activa.")

            nueva = InvestigadorProyecto(
                id_investigador=investigador_id,
                id_proyecto=proyecto_id,
                es_coordinador=es_coordinador,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin
            )

            db.session.add(nueva)

        db.session.commit()
        return proyecto.serialize()



    @staticmethod
    def desvincular_investigadores_de_proyecto(proyecto_id, participaciones, user_id):
        proyecto = ProyectoInvestigacionService._get_proyecto_activo_or_404(
            proyecto_id
        )
        ProyectoInvestigacionService._validar_proyecto_abierto(proyecto)

        if not isinstance(participaciones, list) or not participaciones:
            raise ValueError("Debe enviarse una lista de participaciones.")

        for item in participaciones:
            investigador_id = ProyectoInvestigacionService._validar_investigador_activo(
                item.get("id_investigador")
            )

            participacion = InvestigadorProyecto.query.filter_by(
                id_proyecto=proyecto_id,
                id_investigador=investigador_id,
                deleted_at=None
            ).first()

            if not participacion:
                raise NotFoundError("Participación activa no encontrada.")

            # Lógica de negocio
            participacion.fecha_fin = date.today()

            # Lógica de auditoría
            participacion.soft_delete(user_id=user_id)

        db.session.commit()
        return proyecto.serialize()

    # =====================================================
    # VINCULAR / DESVINCULAR BECARIOS
    # =====================================================

    @staticmethod
    def vincular_becarios_a_proyecto(proyecto_id, participaciones):
        proyecto = ProyectoInvestigacionService._get_proyecto_activo_or_404(
            proyecto_id
        )
        ProyectoInvestigacionService._validar_proyecto_abierto(proyecto)

        for item in participaciones:

            becario_id = item.get("id_becario")
            fecha_inicio = ProyectoInvestigacionService._validar_fecha_participacion(
                item.get("fecha_inicio"), "fecha_inicio"
            )
            fecha_fin = ProyectoInvestigacionService._validar_fecha_participacion(
                item.get("fecha_fin"), "fecha_fin", permitir_none=True
            )
            if fecha_fin and fecha_fin < fecha_inicio:
                raise ValueError(
                    "La fecha fin no puede ser anterior a la fecha inicio"
                )

            existente = BecarioProyecto.query.filter_by(
                id_proyecto=proyecto_id,
                id_becario=becario_id,
                deleted_at=None
            ).first()

            if existente:
                raise ConflictError("Ya existe participación activa.")

            nueva = BecarioProyecto(
                id_becario=becario_id,
                id_proyecto=proyecto_id,
                fecha_inicio=fecha_inicio,
                fecha_fin=fecha_fin,
            )

            db.session.add(nueva)

        db.session.commit()
        return proyecto.serialize()

    @staticmethod
    def desvincular_becarios_de_proyecto(proyecto_id, participaciones, user_id):
        proyecto = ProyectoInvestigacionService._get_proyecto_activo_or_404(
            proyecto_id
        )
        ProyectoInvestigacionService._validar_proyecto_abierto(proyecto)

        for item in participaciones:

            participacion = BecarioProyecto.query.filter_by(
                id_proyecto=proyecto_id,
                id_becario=item.get("id_becario"),
                deleted_at=None
            ).first()

            if not participacion:
                raise NotFoundError("Participación activa no encontrada.")

            participacion.fecha_fin = date.today()
            participacion.soft_delete(user_id=user_id)

        db.session.commit()
        return proyecto.serialize()

    @staticmethod
    def obtener_historial(proyecto_id: int):
        ProyectoInvestigacionService._get_proyecto_or_404(proyecto_id)
        return AuditoriaService.obtener_historial_entidad(
            "proyecto_investigacion",
            proyecto_id
        )

    @staticmethod
    def snapshot_para_memoria_version(memoria_version, user_id):
        proyectos = consultar_entidades_memoria(ProyectoInvestigacion, memoria_version)

        snapshots = []
        for proyecto in proyectos:
            if not estuvo_activo_en_periodo_memoria(
                memoria_version,
                proyecto.fecha_inicio,
                fin_vigencia(proyecto)
            ):
                continue

            snapshot = ProyectoInvestigacionMemoriaVersion(
                memoria_version_id=memoria_version.id,
                proyecto_investigacion_id=proyecto.id,
                codigo_proyecto=proyecto.codigo_proyecto,
                nombre_proyecto=proyecto.nombre_proyecto,
                descripcion_proyecto=proyecto.descripcion_proyecto,
                fecha_inicio=proyecto.fecha_inicio,
                fecha_fin=proyecto.fecha_fin,
                logros_obtenidos=proyecto.logros_obtenidos,
                dificultades_proyecto=proyecto.dificultades_proyecto,
                monto_destinado=proyecto.monto_destinado,
                tipo_proyecto_id=proyecto.tipo_proyecto_id,
                tipo_proyecto_nombre=(
                    proyecto.tipo_proyecto.nombre
                    if proyecto.tipo_proyecto else None
                ),
                grupo_utn_id=proyecto.grupo_utn_id,
                grupo_utn_nombre=(
                    proyecto.grupo_utn.nombre_sigla_grupo
                    if proyecto.grupo_utn else None
                ),
                fuente_financiamiento_id=proyecto.fuente_financiamiento_id,
                fuente_financiamiento_nombre=(
                    proyecto.fuente_financiamiento.nombre
                    if proyecto.fuente_financiamiento else None
                ),
                created_by=user_id
            )
            db.session.add(snapshot)
            snapshots.append(snapshot)

        return snapshots

    @staticmethod
    def obtener_snapshots_por_memoria_version(memoria_version_id: int):
        snapshots = (
            ProyectoInvestigacionMemoriaVersion.query
            .filter(
                ProyectoInvestigacionMemoriaVersion.memoria_version_id == memoria_version_id,
                ProyectoInvestigacionMemoriaVersion.deleted_at.is_(None)
            )
            .order_by(ProyectoInvestigacionMemoriaVersion.nombre_proyecto.asc())
            .all()
        )

        return [snapshot.serialize() for snapshot in snapshots]


