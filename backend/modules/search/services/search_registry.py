from modules.personal.models.personal import Personal, Becario, Investigador
from modules.transferencia.models.transferencia_socio import TransferenciaSocioProductiva
from modules.proyectos.models.proyecto_investigacion import ProyectoInvestigacion
from modules.produccion.models.documentacion_autores import DocumentacionBibliografica, Autor
from modules.produccion.models.articulo_divulgacion import ArticuloDivulgacion
from modules.produccion.models.trabajo_reunion import TrabajoReunionCientifica
from modules.recursos.models.equipamiento import Equipamiento
from modules.grupo.models.visita_grupo import VisitaAcademica
from modules.produccion.models.trabajo_revista import TrabajosRevistasReferato
from modules.proyectos.models.participacion_relevante import ParticipacionRelevante
from modules.recursos.models.movimiento_financiero import MovimientoFinanciero
from modules.recursos.models.becas import Beca




# =====================================================
# Registry de entidades buscables en el sistema
# =====================================================
# Cada entrada define:
# - el modelo
# - los campos donde buscar
# - cómo serializar el resultado
# =====================================================

SEARCH_ENTITIES = [

    # =========================
    # PERSONAL
    # =========================
    {
        "type": "persona",
        "subtype": "personal",
        "model": Personal,
        "fields": ["nombre_apellido"],
        "serializer": lambda p: {
            "type": "persona",
            "subtype": "personal",
            "id": p.id,
            "title": p.nombre_apellido,
            "description": f"{p.tipo_personal.nombre} – {p.horas_semanales} hs",
            "extra": {
                "grupo": p.grupo_utn.nombre_sigla_grupo if p.grupo_utn else None
            },
            "url": f"/personal/{p.id}"
        }
    },
    
    {
        "type": "erogacion",
        "model": MovimientoFinanciero,
        "fields": ["numero_movimiento", "tipo_movimiento", "monto", "fuente_financiamiento.nombre", "categoria_erogacion.nombre"],
        "serializer": lambda e: {
            "type": "erogacion",
            "id": e.id,
            "title": f"Movimiento {e.numero_movimiento}",
            "description": f"{e.tipo_movimiento}: {e.monto} {e.moneda}",
            "extra": {
                "grupo": e.grupo_utn.nombre_sigla_grupo if e.grupo_utn else None
            },
            "url": f"/movimientos/{e.id}"
        }
    },

    # =========================
    # BECARIOS
    # =========================
    {
        "type": "persona",
        "subtype": "becario",
        "model": Becario,
        "fields": ["nombre_apellido"],
        "serializer": lambda b: {
            "type": "persona",
            "subtype": "becario",
            "id": b.id,
            "title": b.nombre_apellido,
            "description": f"Becario – {b.tipo_formacion.nombre}",
            "extra": {
                "grupo": b.grupo_utn.nombre_sigla_grupo if b.grupo_utn else None,
                "proyectos": [
                    p.proyecto.nombre_proyecto
                    for p in b.participaciones_proyecto
                    if p.proyecto
                ]
            },
            "url": f"/becarios/{b.id}"
        }
    },

    {
        "type": "beca",
        "model": Beca,
        "fields": ["nombre_beca", "descripcion"],
        "serializer": lambda b: {
            "type": "beca",
            "id": b.id,
            "title": b.nombre_beca,
            "description": b.descripcion,
            "extra": {
                "fuente_financiamiento": (
                    b.fuente_financiamiento.nombre
                    if b.fuente_financiamiento else None
                ),
                "becarios": [
                    {
                        "id": rel.becario.id,
                        "nombre_apellido": rel.becario.nombre_apellido
                    }
                    for rel in b.becarios
                    if rel.becario
                ]
            },
            "url": f"/becas/{b.id}"
        }
    },

    # =========================
    # INVESTIGADORES
    # =========================
    {
        "type": "persona",
        "subtype": "investigador",
        "model": Investigador,
        "fields": ["nombre_apellido"],
        "serializer": lambda i: {
            "type": "persona",
            "subtype": "investigador",
            "id": i.id,
            "title": i.nombre_apellido,
            "description": f"Investigador – {i.tipo_dedicacion.nombre}",
            "extra": {
                "categoria": i.categoria_utn.nombre if i.categoria_utn else None,
                "grupo": i.grupo_utn.nombre_sigla_grupo if i.grupo_utn else None
            },
            "url": f"/investigadores/{i.id}"
        }
    },
    
    # =========================
    # TRANSFERENCIAS SOCIO PRODUCTIVAS
    # =========================
    
    {
        "type": "transferencia",
        "model": TransferenciaSocioProductiva,
        "fields": [
            "adoptante",
            "demandante",
            "descripcion_actividad"
        ],
        "serializer": lambda t: {
            "type": "transferencia",
            "id": t.id,
            "title": f"{t.adoptante} ↔ {t.demandante}",
            "description": (
                t.descripcion_actividad[:80] + "..."
                if len(t.descripcion_actividad) > 80
                else t.descripcion_actividad
            ),
            "extra": {
                "tipo_contrato": (
                    t.tipo_contrato_transferencia.nombre
                    if t.tipo_contrato_transferencia else None
                ),
                "monto": t.monto,
                "grupo": (
                    t.grupo_utn.nombre_sigla_grupo
                    if t.grupo_utn else None
                )
            },
            "url": f"/transferencias/{t.id}"
        }
    },
    
    # =========================
    # PROYECTOS DE INVESTIGACIÓN
    # ========================
    {
        "type": "proyecto",
        "model": ProyectoInvestigacion,
        "fields": [
            "nombre_proyecto",
            "descripcion_proyecto",
            "codigo_proyecto"
        ],
        "serializer": lambda p: {
            "type": "proyecto",
            "id": p.id,
            "title": p.nombre_proyecto,
            "description": (
                p.descripcion_proyecto[:90] + "..."
                if len(p.descripcion_proyecto) > 90
                else p.descripcion_proyecto
            ),
            "extra": {
                "codigo": p.codigo_proyecto,
                "tipo": p.tipo_proyecto.nombre if p.tipo_proyecto else None,
                "grupo": p.grupo_utn.nombre_sigla_grupo if p.grupo_utn else None,
                "becarios": len([
                    rel for rel in p.participaciones_becario
                    if rel.becario
                ]),
                "investigadores": len([
                    rel for rel in p.participaciones_investigador
                    if rel.investigador
                ]),
                "distinciones": [
                    {
                        "fecha": d.fecha.isoformat(),
                        "descripcion": d.descripcion
                    }
                    for d in p.distinciones
                ] if p.distinciones else []
            },
            "url": f"/proyectos/{p.id}"
        }
    },
    
    # =========================
    # DOCUMENTACIÓN BIBLIOGRÁFICA
    # =========================
    {
        "type": "documentacion",
        "model": DocumentacionBibliografica,
        "fields": ["titulo", "editorial"],
        "serializer": lambda d: {
            "type": "documentacion",
            "id": d.id,
            "title": d.titulo,
            "description": f"{d.editorial} – {d.anio}",
            "extra": {
                "autores": [a.nombre_apellido for a in d.autores],
                "grupo": (
                    d.grupo_utn.nombre_sigla_grupo
                    if d.grupo_utn else None
                )
            },
            "url": f"/documentacion-bibliografica/{d.id}"
        }
    },
    # =========================
    # AUTORES
    # =========================
    {
        "type": "autor",
        "model": Autor,
        "fields": ["nombre_apellido"],
        "serializer": lambda a: {
            "type": "autor",
            "id": a.id,
            "title": a.nombre_apellido,
            "description": f"{len(a.libros)} libros asociados",
            "extra": {
                "libros": [
                    {"id": l.id, "titulo": l.titulo}
                    for l in a.libros[:3]  # 👈 resumen
                ]
            },
            "url": f"/autores/{a.id}"
        }
    },
    
    # =========================
    # ARTÍCULOS DE DIVULGACIÓN
    # =========================
    {
        "type": "articulo_divulgacion",
        "model": ArticuloDivulgacion,
        "fields": ["titulo", "descripcion"],
        "serializer": lambda a: {
            "type": "articulo_divulgacion",
            "id": a.id,
            "title": a.titulo,
            "description": (
                a.descripcion[:90] + "..."
                if len(a.descripcion) > 90
                else a.descripcion
            ),
            "extra": {
                "fecha_publicacion": (
                    a.fecha_publicacion.isoformat()
                    if a.fecha_publicacion else None
                ),
                "grupo": (
                    a.grupo_utn.nombre_sigla_grupo
                    if a.grupo_utn else None
                )
            },
            "url": f"/articulos-divulgacion/{a.id}"
        }
    },
    # =========================
    # TRABAJOS EN REUNIONES CIENTÍFICAS
    # =========================
    {
        "type": "trabajo_reunion_cientifica",
        "model": TrabajoReunionCientifica,
        "fields": [
            "titulo_trabajo",
            "nombre_reunion",
            "procedencia"
        ],
        "serializer": lambda t: {
            "type": "trabajo_reunion_cientifica",
            "id": t.id,
            "title": t.titulo_trabajo,
            "description": f"{t.nombre_reunion} – {t.tipo_reunion_cientifica}",
            "extra": {
                "autores": [a.serialize() for a in t.autorias],
                "procedencia": t.procedencia,
                "fecha": (
                    t.fecha_presentacion.isoformat()
                    if t.fecha_presentacion else None
                ),
                "grupo": (
                    t.grupo_utn.nombre_sigla_grupo
                    if t.grupo_utn else None
                )
            },
            "url": f"/trabajos-reunion-cientifica/{t.id}"
        }
    },
    # =========================
    # EQUIPAMIENTO
    # =========================
    {
        "type": "equipamiento",
        "model": Equipamiento,
        "fields": [
            "denominacion",
            "descripcion_breve"
        ],
        "serializer": lambda e: {
            "type": "equipamiento",
            "id": e.id,
            "title": e.denominacion,
            "description": e.descripcion_breve,
            "extra": {
                "fecha_incorporacion": (
                    e.fecha_incorporacion.isoformat()
                    if e.fecha_incorporacion else None
                ),
                "grupo": (
                    e.grupo_utn.nombre_sigla_grupo
                    if e.grupo_utn else None
                )
            },
            "url": f"/equipamiento/{e.id}"
        }
    },
    # =========================
    # VISITAS ACADÉMICAS
    # =========================
    {
        "type": "visita_academica",
        "model": VisitaAcademica,
        "fields": [
            "razon",
            "procedencia"
        ],
        "serializer": lambda v: {
            "type": "visita_academica",
            "id": v.id,
            "title": (
                f"Visita {v.tipo_visita.nombre if v.tipo_visita else ''}"
            ).strip(),
            "description": f"{v.procedencia} – {v.razon}",
            "extra": {
                "fecha": (
                    v.fecha.isoformat()
                    if v.fecha else None
                ),
                "grupo": (
                    v.grupo_utn.nombre_sigla_grupo
                    if v.grupo_utn else None
                )
            },
            "url": f"/visitas-academicas/{v.id}"
        }
    },
    # =========================
    # TRABAJOS EN REVISTAS CON REFERATO
    # =========================
    {
        "type": "trabajo_revista",
        "model": TrabajosRevistasReferato,
        "fields": [
            "titulo_trabajo",
            "nombre_revista",
            "editorial",
            "issn",
            "pais"
        ],
        "serializer": lambda t: {
            "type": "trabajo_revista",
            "id": t.id,
            "title": t.titulo_trabajo,
            "description": f"{t.nombre_revista} – {t.editorial}",
            "extra": {
                "issn": t.issn,
                "pais": t.pais,
                "grupo": (
                    t.grupo_utn.nombre_sigla_grupo
                    if t.grupo_utn else None
                ),
                "tipo_revista": (
                    t.tipo_revista.nombre
                    if t.tipo_revista else None
                ),
                "autores": [a.serialize() for a in t.autorias]
            },
            "url": f"/trabajos-revistas/{t.id}"
        }
    },
    
    # =========================
    # PARTICIPACIONES RELEVANTES
    # =========================
    {
        "type": "participacion_relevante",
        "model": ParticipacionRelevante,
        "fields": [
            "nombre_evento",
            "forma_participacion"
        ],
        "serializer": lambda p: {
            "type": "participacion_relevante",
            "id": p.id,
            "title": p.nombre_evento,
            "description": f"Participación como {p.forma_participacion}",
            "extra": {
                "participante": p.participante.nombre_apellido if p.participante else None,
                "categoria": (
                    "Investigador" if p.participante_rol == "investigador" else "Becario"
                ),
                "fecha": (
                    p.fecha.isoformat()
                    if p.fecha else None
                )
            },
            "url": f"/participaciones-relevantes/{p.id}"
        }
    }


    







]
