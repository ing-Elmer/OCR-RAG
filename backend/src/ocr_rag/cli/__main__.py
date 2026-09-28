"""Entrada del CLI: `uv run python -m ocr_rag.cli <comando>`."""

import sys

from ocr_rag.cli.cargar_corpus import main as cargar_corpus_main
from ocr_rag.cli.crear_admin import main as crear_admin_main
from ocr_rag.cli.evaluar import main as evaluar_main
from ocr_rag.cli.reprocesar import main as reprocesar_main

_COMANDOS = {
    "crear-admin": crear_admin_main,
    "cargar-corpus": cargar_corpus_main,
    "reprocesar": reprocesar_main,
    "evaluar": evaluar_main,
}


def main() -> None:
    """Despacha el subcomando pedido por línea de comandos.

    Los argumentos posteriores al subcomando (por ejemplo, `cargar-corpus --usuario ana`) los
    parsea cada comando por su cuenta; acá solo se valida cuál correr.
    """
    if len(sys.argv) < 2 or sys.argv[1] not in _COMANDOS:
        comandos = ", ".join(_COMANDOS)
        # CLI: la salida por consola es la única interfaz de este comando.
        print(f"Uso: python -m ocr_rag.cli <comando> [opciones]. Comandos disponibles: {comandos}")
        raise SystemExit(1)

    _COMANDOS[sys.argv[1]]()


if __name__ == "__main__":
    main()
