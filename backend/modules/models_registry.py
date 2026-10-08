"""Importa modelos modulares para registrar metadata de SQLAlchemy."""

from modules.auth.models.persona import Persona  # noqa: F401
from modules.auth.models.login_attempt import LoginAttempt  # noqa: F401
from modules.auth.models.refresh_token_session import RefreshTokenSession  # noqa: F401
from modules.auth.models.usuario import RolUsuario, Usuario  # noqa: F401
from modules.auth.models.usuario_grupo_utn import UsuarioGrupoUtn  # noqa: F401
from modules.catalogos.models.categoria_utn import CategoriaUtn  # noqa: F401
from modules.catalogos.models.fuente_financiamiento import FuenteFinanciamiento  # noqa: F401
from modules.grupo.models.directivos import Cargo, Directivo, DirectivoGrupo  # noqa: F401
from modules.grupo.models.grupo import GrupoInvestigacionUtn  # noqa: F401
from modules.grupo.models.programa_actividades import PlanificacionGrupo  # noqa: F401
from modules.grupo.models.programa_incentivos import ProgramaIncentivos  # noqa: F401
from modules.grupo.models.visita_grupo import (  # noqa: F401
    TipoVisita,
    VisitaAcademica,
    VisitaAcademicaMemoriaVersion,
)
from modules.memorias.models.memorias import (  # noqa: F401
    EstadoMemoria,
    Memoria,
    MemoriaVersion,
)
from modules.personal.models.personal import (  # noqa: F401
    Becario,
    BecarioHorasHistorial,
    BecarioMemoriaVersion,
    Investigador,
    InvestigadorHorasHistorial,
    InvestigadorMemoriaVersion,
    Personal,
    PersonalMemoriaVersion,
    TipoDedicacion,
    TipoFormacion,
)
from modules.personal.models.tipo_personal import TipoPersonal  # noqa: F401
from modules.produccion.models.actividad_docencia import (  # noqa: F401
    ActividadDocencia,
    ActividadDocenciaGradoMemoriaVersion,
    ActividadDocenciaMemoriaVersion,
    GradoAcademico,
    InvestigadorActividadGrado,
    RolActividad,
)
from modules.produccion.models.articulo_divulgacion import (  # noqa: F401
    ArticuloDivulgacion,
    ArticuloDivulgacionMemoriaVersion,
)
from modules.produccion.models.distinciones import (  # noqa: F401
    DistincionRecibida,
    DistincionRecibidaMemoriaVersion,
)
from modules.produccion.models.documentacion_autores import (  # noqa: F401
    Autor,
    DocumentacionBibliografica,
    DocumentacionBibliograficaAutorMemoriaVersion,
    DocumentacionBibliograficaMemoriaVersion,
    autor_libro,
)
from modules.produccion.models.registro_patente import (  # noqa: F401
    RegistrosPropiedad,
    RegistrosPropiedadMemoriaVersion,
    TipoRegistroPropiedad,
)
from modules.produccion.models.trabajo_reunion import (  # noqa: F401
    TipoReunion,
    TrabajoReunionCientifica,
    TrabajoReunionCientificaMemoriaVersion,
)
from modules.produccion.models.trabajo_revista import (  # noqa: F401
    TipoRevista,
    TrabajosRevistasReferato,
    TrabajosRevistasReferatoMemoriaVersion,
)
from modules.informes.models.informe import Informe, InformeInvestigador, InformeProyecto  # noqa: F401
from modules.proyectos.models.participacion_relevante import (  # noqa: F401
    ParticipacionRelevante,
    ParticipacionRelevanteMemoriaVersion,
)
from modules.proyectos.models.proyecto_investigacion import (  # noqa: F401
    BecarioProyecto,
    InvestigadorProyecto,
    ProyectoInvestigacion,
    ProyectoInvestigacionMemoriaVersion,
    TipoProyecto,
)
from modules.recursos.models.becas import Beca, Beca_Becario  # noqa: F401
from modules.recursos.models.equipamiento import (  # noqa: F401
    Equipamiento,
    EquipamientoMemoriaVersion,
)
from modules.recursos.models.erogacion import (  # noqa: F401
    Erogacion,
    ErogacionMemoriaVersion,
    TipoErogacion,
)
from modules.recursos.models.tipo_cambio import TipoCambio  # noqa: F401
from modules.recursos.models.movimiento_financiero import (  # noqa: F401
    CategoriaErogacion,
    MovimientoFinanciero,
    MovimientoMemoriaVersion,
)
from modules.shared.models.auditoria_campo import AuditoriaCampo  # noqa: F401
from modules.shared.models.form_draft import FormDraft  # noqa: F401
from modules.shared.models.audit_mixin import AuditMixin  # noqa: F401
from modules.transferencia.models.transferencia_socio import (  # noqa: F401
    Adoptante,
    AdoptanteTransferencia,
    AdoptanteTransferenciaMemoriaVersion,
    TipoContrato,
    TransferenciaSocioProductiva,
    TransferenciaSocioProductivaMemoriaVersion,
)

from modules.produccion.models.trabajo_autor import TrabajoReunionAutor, TrabajoRevistaAutor  # noqa: F401
