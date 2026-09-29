"""Comando `crear-admin`: crea el primer usuario con rol ADMIN.

Arma sus propias dependencias (repositorio, validador, hasher) porque no hay un proceso ASGI
que las arme por él, y abre/cierra la `ConnectionFactory` él mismo.
"""

import asyncio
import getpass

from ocr_rag.application.validators.crear_admin_validator import CrearAdminValidator
from ocr_rag.core.exceptions import DomainError, NotFoundError, ValidationError
from ocr_rag.core.settings import get_settings
from ocr_rag.infrastructure.db import ConnectionFactory
from ocr_rag.infrastructure.repositories.usuario_repository import PostgresUsuarioRepository
from ocr_rag.infrastructure.security.bcrypt_password_hasher import BcryptPasswordHasher

_ROL_ADMIN = "ADMIN"


def _pedir_credenciales() -> tuple[str, str, str]:
    """Pide username, nombre completo y contraseña por teclado.

    La contraseña se pide dos veces con `getpass` (nunca queda en el historial de la
    terminal ni se imprime en pantalla) y ambas deben coincidir.
    """
    username = input("Username: ").strip()
    nombre_completo = input("Nombre completo: ").strip()
    password = getpass.getpass("Contraseña (mínimo 12 caracteres): ")
    confirmacion = getpass.getpass("Confirmar contraseña: ")

    if password != confirmacion:
        # Única capa donde el estándar permite escritura directa a consola: es un comando de
        # terminal, no hay cliente HTTP ni handler de errores que traduzca esta salida.
        print("Las contraseñas no coinciden.")
        raise SystemExit(1)

    return username, nombre_completo, password


async def _crear_admin() -> None:
    """Crea el usuario administrador contra la base configurada en `Settings`."""
    username, nombre_completo, password = _pedir_credenciales()

    settings = get_settings()
    connection_factory = ConnectionFactory()
    await connection_factory.abrir("MAIN", settings.db_main_dsn.get_secret_value())
    try:
        repositorio = PostgresUsuarioRepository(connection_factory)
        validador = CrearAdminValidator(repositorio)
        hasher = BcryptPasswordHasher()

        await validador.validar(username, password)

        password_hash = await hasher.hashear(password)
        usuario_id = await repositorio.crear(username, password_hash, nombre_completo)

        try:
            await repositorio.asignar_rol(usuario_id, _ROL_ADMIN)
        except NotFoundError as error:
            raise DomainError(
                "No existe el rol ADMIN: ¿se ejecutó 'db/002_seed_roles_permisos.sql'?"
            ) from error
    finally:
        await connection_factory.cerrar_todos()

    print(f"Usuario administrador '{username}' creado correctamente.")


def main() -> None:
    """Punto de entrada síncrono del comando.

    En Windows, `psycopg` async requiere un `SelectorEventLoop`: el `ProactorEventLoop` (el
    default) no soporta los sockets que usa `psycopg_pool`.
    """
    try:
        asyncio.run(_crear_admin(), loop_factory=asyncio.SelectorEventLoop)
    except ValidationError as error:
        print("Error: los datos ingresados no son válidos.")
        for campo, mensajes in (error.errors or {}).items():
            for mensaje in mensajes:
                print(f"  - {campo}: {mensaje}")
        raise SystemExit(1) from error
    except DomainError as error:
        print(f"Error: {error.message}")
        raise SystemExit(1) from error
