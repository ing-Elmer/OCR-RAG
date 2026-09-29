"""Entrada del CLI: `uv run python -m ocr_rag.cli <comando>`."""

import sys

from ocr_rag.cli.crear_admin import main as crear_admin_main

_COMANDOS = {"crear-admin": crear_admin_main}


def main() -> None:
    """Despacha el subcomando pedido por línea de comandos."""
    if len(sys.argv) != 2 or sys.argv[1] not in _COMANDOS:
        comandos = ", ".join(_COMANDOS)
        # CLI: la salida por consola es la única interfaz de este comando.
        print(f"Uso: python -m ocr_rag.cli <comando>. Comandos disponibles: {comandos}")
        raise SystemExit(1)

    _COMANDOS[sys.argv[1]]()


if __name__ == "__main__":
    main()
