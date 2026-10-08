"""Ejecutable independiente para sincronizar cotizaciones BCRA."""

from app import create_app
from modules.recursos.services.tipo_cambio_service import TipoCambioService


def main():
    app = create_app()
    with app.app_context():
        TipoCambioService.sincronizar()


if __name__ == "__main__":
    main()
