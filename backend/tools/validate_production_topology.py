"""Valida la topologia productiva renderizada sin imprimir secretos."""

import argparse
import ipaddress
import json
import os
import subprocess
from urllib.parse import urlsplit


PRIVATE_SERVICES = {"backend", "frontend", "db", "redis"}
PUBLIC_SERVICES = {"nginx"}


def _published_ports(service: dict) -> list:
    return service.get("ports") or []


def _database_username(database_url: str) -> str | None:
    if not database_url:
        return None
    return urlsplit(database_url).username


def validate_config(config: dict, allow_lan_bind: bool = False) -> list[str]:
    errors: list[str] = []
    services = config.get("services") or {}

    for service_name in PRIVATE_SERVICES:
        service = services.get(service_name)
        if service is None:
            errors.append(f"Falta el servicio obligatorio {service_name}")
        elif _published_ports(service):
            errors.append(f"{service_name} no debe publicar puertos")

    for service_name, service in services.items():
        if _published_ports(service) and service_name not in PUBLIC_SERVICES:
            errors.append(f"{service_name} publica puertos sin estar autorizado")

    proxy = services.get("nginx")
    if proxy is None:
        errors.append("Falta el servicio obligatorio nginx")
    else:
        proxy_ports = _published_ports(proxy)
        if len(proxy_ports) != 1:
            errors.append("nginx debe publicar exactamente un puerto")
        elif isinstance(proxy_ports[0], dict):
            published = proxy_ports[0]
            if int(published.get("target", 0)) != 8080:
                errors.append("nginx debe publicar el puerto interno 8080")
            host_ip = published.get("host_ip") or "0.0.0.0"
            try:
                bind_address = ipaddress.ip_address(host_ip)
            except ValueError:
                errors.append("NGINX_BIND_ADDRESS no es un binding soportado")
            else:
                if not bind_address.is_loopback and not allow_lan_bind:
                    errors.append(
                        "nginx debe publicar solo en loopback para el origen local "
                        "(GIDAS_ALLOW_LAN_BIND=1 habilita el acceso LAN de laboratorio)"
                    )

    backend_environment = (services.get("backend") or {}).get("environment") or {}
    migrate_environment = (services.get("migrate") or {}).get("environment") or {}
    runtime_user = _database_username(backend_environment.get("DATABASE_URL", ""))
    app_user = migrate_environment.get("POSTGRES_APP_USER")

    if not runtime_user:
        errors.append("DATABASE_URL del backend no define usuario runtime")
    if not app_user:
        errors.append("POSTGRES_APP_USER no esta definido en migrate")
    if runtime_user and app_user and runtime_user != app_user:
        errors.append("DATABASE_URL del backend no usa POSTGRES_APP_USER")

    migration_user = _database_username(
        migrate_environment.get("DATABASE_URL", "")
    )
    if runtime_user and migration_user and runtime_user == migration_user:
        errors.append("Runtime y migraciones no deben usar el mismo usuario")

    return errors


def render_compose(env_file: str) -> dict:
    command = [
        "docker",
        "compose",
        "--env-file",
        env_file,
        "config",
        "--format",
        "json",
    ]
    result = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(result.stdout)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=".env.production")
    args = parser.parse_args()

    # GIDAS_ALLOW_LAN_BIND=1: el laboratorio necesita publicar en 0.0.0.0 para
    # atender sgm.gidas.local:8080 desde la LAN. Es una excepcion explicita del
    # operador de infraestructura, no el valor por defecto.
    allow_lan_bind = os.environ.get("GIDAS_ALLOW_LAN_BIND") == "1"

    errors = validate_config(render_compose(args.env_file), allow_lan_bind)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    if allow_lan_bind:
        print(
            "Topologia productiva valida (GIDAS_ALLOW_LAN_BIND=1): proxy "
            "publicado en la LAN por decision del operador y roles separados."
        )
    else:
        print(
            "Topologia productiva valida: solo proxy publicado en loopback "
            "y roles separados."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
