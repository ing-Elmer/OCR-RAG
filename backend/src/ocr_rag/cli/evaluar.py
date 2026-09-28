"""Comando `evaluar`: corre el dataset de evaluación del RAG contra `ConsultaService` real
(OpenAI y base reales) y mide cuánto recupera y cita cada respuesta.

No es un test de CI (no hace assertions sobre el resultado): imprime una tabla por caso y un
resumen agregado (hit@k, MRR, % de casos con todas las citas), y opcionalmente vuelca el detalle
completo a JSON para comparar corridas. Exit 0 si corrió (haya o no casos con mala recuperación),
exit 1 solo por un error de uso (usuario inexistente, dataset inválido).

Arma sus propias dependencias, igual que `cargar_corpus.py` y `reprocesar.py`.
"""

import argparse
import asyncio
import importlib.resources
import json
import sys
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI
from pydantic import ValidationError as PydanticValidationError

from ocr_rag.application.evaluacion_metricas import (
    ResultadoRecuperacion,
    ResumenEvaluacion,
    calcular_resumen,
    contar_citas,
    evaluar_recuperacion,
)
from ocr_rag.application.services.consulta_service import ConsultaService
from ocr_rag.application.validators.consulta_validator import ConsultaValidator
from ocr_rag.cli.cargar_corpus import resolver_usuario
from ocr_rag.core.schemas.documento import TOP_K_POR_DEFECTO
from ocr_rag.core.schemas.evaluacion import CasoEvaluacion, DatasetEvaluacion
from ocr_rag.core.settings import get_settings
from ocr_rag.infrastructure.clients.openai_chat_client import OpenAiChatClient
from ocr_rag.infrastructure.clients.openai_embedding_client import OpenAiEmbeddingClient
from ocr_rag.infrastructure.db import ConnectionFactory
from ocr_rag.infrastructure.repositories.documento_repository import PostgresDocumentoRepository
from ocr_rag.infrastructure.repositories.usuario_repository import PostgresUsuarioRepository

# Timeout explícito para las llamadas a OpenAI (chat y embeddings), igual que en `cargar_corpus.py`.
_TIMEOUT_OPENAI_SEGUNDOS = 60.0

_NOMBRE_DATASET_POR_DEFECTO = "normativa_ca.toml"


def _parsear_argumentos(argv: list[str]) -> argparse.Namespace:
    """Define y parsea los argumentos del comando `evaluar`."""
    parser = argparse.ArgumentParser(
        prog="python -m ocr_rag.cli evaluar",
        description=(
            "Corre el dataset de evaluación contra el RAG real (OpenAI y base reales) y mide "
            "cuánto recupera y cita cada respuesta: hit@k, MRR y % de casos con todas las citas. "
            "No es un test de CI: exit 0 si corrió, exit 1 solo por un error de uso."
        ),
    )
    parser.add_argument(
        "--usuario",
        required=True,
        help="Username de un usuario existente y activo.",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=None,
        help="Ruta a un dataset TOML alternativo. Por defecto usa el dataset empaquetado "
        f"'{_NOMBRE_DATASET_POR_DEFECTO}'.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=TOP_K_POR_DEFECTO,
        help=f"Cantidad de fuentes a pedirle a cada consulta (por defecto {TOP_K_POR_DEFECTO}).",
    )
    parser.add_argument(
        "--salida-json",
        type=Path,
        default=None,
        help="Si se indica, además vuelca a esta ruta el detalle completo (pregunta, respuesta, "
        "fuentes y métricas) de cada caso, para comparar corridas.",
    )
    return parser.parse_args(argv)


def _leer_dataset_por_defecto() -> str:
    """Texto del dataset empaquetado dentro de `ocr_rag.cli.evaluacion`."""
    recurso = importlib.resources.files("ocr_rag.cli.evaluacion").joinpath(
        _NOMBRE_DATASET_POR_DEFECTO
    )
    return recurso.read_text(encoding="utf-8")


def cargar_dataset(ruta: Path | None) -> DatasetEvaluacion:
    """Lee y valida el dataset de `ruta`, o el empaquetado por defecto si `ruta` es `None`.

    Lanza `OSError` si `ruta` no se puede leer, `tomllib.TOMLDecodeError` si no es TOML válido, o
    `pydantic.ValidationError` si no cumple el esquema (`DatasetEvaluacion`).
    """
    texto = _leer_dataset_por_defecto() if ruta is None else ruta.read_text(encoding="utf-8")
    datos = tomllib.loads(texto)
    return DatasetEvaluacion.model_validate(datos)


@dataclass(frozen=True, slots=True)
class ResultadoCasoEvaluado:
    """Resultado completo de correr un caso: lo que se imprime en la tabla y se vuelca a JSON."""

    id: str
    pregunta: str
    respuesta: str
    fuentes: list[dict[str, Any]]
    recuperacion: ResultadoRecuperacion
    citas_logradas: int
    citas_totales: int


async def evaluar_caso(
    caso: CasoEvaluacion, consulta_service: ConsultaService, top_k: int
) -> ResultadoCasoEvaluado:
    """Corre `caso` contra `consulta_service` y calcula sus métricas de recuperación y citación."""
    resultado_consulta = await consulta_service.consultar(caso.pregunta, None, top_k)
    recuperacion = evaluar_recuperacion(
        caso.esperados, resultado_consulta.fuentes, resultado_consulta.respuesta
    )
    citas_logradas, citas_totales = contar_citas(
        caso.esperados, resultado_consulta.respuesta, resultado_consulta.fuentes
    )
    return ResultadoCasoEvaluado(
        id=caso.id,
        pregunta=caso.pregunta,
        respuesta=resultado_consulta.respuesta,
        fuentes=[fuente.model_dump(mode="json") for fuente in resultado_consulta.fuentes],
        recuperacion=recuperacion,
        citas_logradas=citas_logradas,
        citas_totales=citas_totales,
    )


async def evaluar_dataset(
    dataset: DatasetEvaluacion, consulta_service: ConsultaService, top_k: int
) -> list[ResultadoCasoEvaluado]:
    """Corre todos los casos del dataset, de a uno, imprimiendo el progreso."""
    total = len(dataset.caso)
    resultados: list[ResultadoCasoEvaluado] = []
    for indice, caso in enumerate(dataset.caso, start=1):
        print(f"[{indice}/{total}] {caso.id} … consultando", flush=True)
        resultados.append(await evaluar_caso(caso, consulta_service, top_k))
    return resultados


def imprimir_tabla(resultados: list[ResultadoCasoEvaluado]) -> None:
    """Imprime, por caso, si se recuperó (y en qué posición) y cuántas citas logró."""
    print()
    print(f"{'id':<32} {'recuperado':<16} {'citas':<10}")
    for resultado in resultados:
        if resultado.recuperacion.acierto:
            posicion = resultado.recuperacion.posicion
            recuperado = f"sí (#{posicion})" if posicion else "sí"
        else:
            recuperado = "no"
        citas = f"{resultado.citas_logradas}/{resultado.citas_totales}"
        print(f"{resultado.id:<32} {recuperado:<16} {citas:<10}")


def imprimir_resumen(resumen: ResumenEvaluacion) -> None:
    """Imprime el resumen agregado de la corrida."""
    print()
    print(
        f"Resumen: hit@k={resumen.hit_at_k:.2f} · MRR={resumen.mrr:.2f} · "
        f"citas completas={resumen.porcentaje_citas_completas:.0%}"
    )


def calcular_resumen_de(resultados: list[ResultadoCasoEvaluado]) -> ResumenEvaluacion:
    """Arma los argumentos de `calcular_resumen` a partir de `resultados`."""
    return calcular_resumen(
        [resultado.recuperacion for resultado in resultados],
        [(resultado.citas_logradas, resultado.citas_totales) for resultado in resultados],
    )


def guardar_json(
    ruta: Path, resultados: list[ResultadoCasoEvaluado], resumen: ResumenEvaluacion
) -> None:
    """Vuelca a `ruta` el detalle completo por caso (pregunta, respuesta, fuentes y métricas) y
    el resumen agregado, para comparar corridas.
    """
    datos = {
        "resumen": asdict(resumen),
        "casos": [
            {
                "id": resultado.id,
                "pregunta": resultado.pregunta,
                "respuesta": resultado.respuesta,
                "fuentes": resultado.fuentes,
                "recuperado": resultado.recuperacion.acierto,
                "posicionRecuperado": resultado.recuperacion.posicion,
                "citasLogradas": resultado.citas_logradas,
                "citasTotales": resultado.citas_totales,
            }
            for resultado in resultados
        ],
    }
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")


async def _evaluar(argv: list[str]) -> int:
    """Arma las dependencias contra la base configurada en `Settings` y corre la evaluación."""
    args = _parsear_argumentos(argv)

    try:
        dataset = cargar_dataset(args.dataset)
    except (OSError, tomllib.TOMLDecodeError, PydanticValidationError) as error:
        print(f"Error: el dataset no es válido: {error}")
        return 1

    settings = get_settings()
    connection_factory = ConnectionFactory()
    await connection_factory.abrir("MAIN", settings.db_main_dsn.get_secret_value())
    openai_client = AsyncOpenAI(
        api_key=settings.openai_api_key.get_secret_value(), timeout=_TIMEOUT_OPENAI_SEGUNDOS
    )
    try:
        usuario_repositorio = PostgresUsuarioRepository(connection_factory)
        credenciales = await resolver_usuario(args.usuario, usuario_repositorio)
        if credenciales is None:
            return 1

        documento_repositorio = PostgresDocumentoRepository(connection_factory)
        consulta_service = ConsultaService(
            documento_repositorio,
            ConsultaValidator(documento_repositorio),
            OpenAiEmbeddingClient(openai_client, settings.openai_embedding_model),
            OpenAiChatClient(openai_client, settings.openai_chat_model),
            settings,
        )

        resultados = await evaluar_dataset(dataset, consulta_service, args.top_k)
    finally:
        await connection_factory.cerrar_todos()

    imprimir_tabla(resultados)
    resumen = calcular_resumen_de(resultados)
    imprimir_resumen(resumen)

    if args.salida_json is not None:
        guardar_json(args.salida_json, resultados, resumen)
        print(f"Detalle completo guardado en {args.salida_json}")

    return 0


def main() -> None:
    """Punto de entrada síncrono del comando.

    En Windows, `psycopg` async requiere un `SelectorEventLoop`: el `ProactorEventLoop` (el
    default) no soporta los sockets que usa `psycopg_pool`.
    """
    codigo = asyncio.run(_evaluar(sys.argv[2:]), loop_factory=asyncio.SelectorEventLoop)
    raise SystemExit(codigo)
