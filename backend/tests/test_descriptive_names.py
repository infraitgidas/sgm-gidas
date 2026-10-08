import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app import create_app  # noqa: F401 - registra modelos y servicios
from modules.shared.exceptions import ValidationError
from modules.personal.services.personal_service import _validar_nombre as validar_personal
from modules.personal.services.investigador_service import _validar_nombre as validar_investigador
from modules.personal.services.becario_service import _validar_nombre as validar_becario
from modules.grupo.services.directivo_service import DirectivoGrupoService
from modules.produccion.services.autores_service import AutorService
from modules.produccion.services.trabajo_revista_service import TrabajosRevistasReferatoService
from modules.produccion.services.trabajo_reunion_service import TrabajoReunionCientificaService
from modules.produccion.services.registro_propiedad_service import RegistrosPropiedadService
from modules.proyectos.services.participacion_relevante_service import ParticipacionRelevanteService
from modules.proyectos.services.proyecto_investigacion_service import ProyectoInvestigacionService
from modules.recursos.services.equipamiento_service import EquipamientoService
from modules.transferencia.services.transferencia_service import TransferenciaSocioProductivaService
from modules.transferencia.services.adoptante_service import AdoptanteService


class DescriptiveNamesTestCase(unittest.TestCase):
    def test_nombres_de_personas_y_adoptantes_solo_permiten_letras_y_espacios(self):
        names = (
            (validar_personal, "nombre_apellido"),
            (validar_investigador, "nombre_apellido"),
            (validar_becario, "nombre_apellido"),
            (AutorService._validar_nombre, "nombre_apellido"),
            (lambda value: DirectivoGrupoService.crear_directivo({"nombre_apellido": value}, 1), "nombre_apellido"),
            (lambda value: AdoptanteService.create({"nombre": value}, 1), "nombre"),
        )
        for validate, field in names:
            for invalid in ("22", "Ana 22", "Ana-María", "Ana!", "Ana\tMaría"):
                with self.subTest(field=field, value=invalid, validator=validate), self.assertRaises(ValidationError) as caught:
                    validate(invalid)
                self.assertIn(field, caught.exception.details["fields"])

        with patch.object(AdoptanteService, "_get_or_404", return_value=SimpleNamespace(nombre="Anterior")):
            with self.assertRaises(ValidationError) as caught:
                AdoptanteService.update(1, {"nombre": "Nuevo 22"})
            self.assertIn("nombre", caught.exception.details["fields"])

    def test_nombres_numericos_identifican_campo(self):
        cases = (
            (validar_personal, "nombre_apellido"),
            (validar_investigador, "nombre_apellido"),
            (validar_becario, "nombre_apellido"),
            (AutorService._validar_nombre, "nombre_apellido"),
            (lambda value: ProyectoInvestigacionService.create({"codigo_proyecto": "ABC1", "nombre_proyecto": value}, 1), "nombre_proyecto"),
            (lambda value: ParticipacionRelevanteService._validar_texto(value, "nombre_evento"), "nombre_evento"),
            (lambda value: TrabajosRevistasReferatoService._validar_texto(value, "nombre_revista"), "nombre_revista"),
            (lambda value: TrabajoReunionCientificaService._validar_texto(value, "nombre_reunion"), "nombre_reunion"),
            (lambda value: RegistrosPropiedadService._validar_texto(value, "nombre_articulo"), "nombre_articulo"),
            (lambda value: EquipamientoService._validar_texto(value, "La denominacion"), "denominacion"),
            (lambda value: TransferenciaSocioProductivaService._validar_texto(value, "demandante"), "demandante"),
        )
        for validate, field in cases:
            with self.subTest(field=field, validator=validate), self.assertRaises(ValidationError) as caught:
                validate("22")
            self.assertIn(field, caught.exception.details["fields"])
