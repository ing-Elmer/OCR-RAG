"""Tests del `ProcesamientoDocumentoService` (worker de OCR + embeddings)."""

from ocr_rag.application.services.procesamiento_documento_service import (
    ProcesamientoDocumentoService,
)
from ocr_rag.core.schemas.documento import PaginaExtraida, TipoDocumento
from tests.conftest import (
    FakeClasificadorDocumento,
    FakeDocumentoRepository,
    FakeEmbeddingClient,
    FakeExtractorTexto,
)


async def _crear_documento_pendiente(repositorio: FakeDocumentoRepository) -> int:
    return await repositorio.crear(
        nombre_archivo="documento.pdf",
        tipo_contenido="application/pdf",
        tamano_bytes=100,
        idioma="spa",
        creado_por_id=1,
        contenido=b"%PDF-1.4 contenido de prueba",
        sha256="a" * 64,
    )


async def test_procesar_documento_ok_queda_procesado_con_chunks_en_orden() -> None:
    repositorio = FakeDocumentoRepository()
    documento_id = await _crear_documento_pendiente(repositorio)
    paginas = [
        PaginaExtraida(numero=1, texto="Primera oración de la página uno. " * 20),
        PaginaExtraida(numero=2, texto="Primera oración de la página dos. " * 20),
    ]
    service = ProcesamientoDocumentoService(
        repositorio,
        FakeExtractorTexto(paginas),
        FakeEmbeddingClient(),
        FakeClasificadorDocumento(),
    )

    await service.procesar(documento_id)

    documento = await repositorio.obtener(documento_id)
    assert documento is not None
    assert documento.estado == "procesado"
    assert documento.paginas == 2
    assert documento.cantidad_chunks > 0

    chunks = repositorio.chunks_de(documento_id)
    ordenes = [chunk.orden for chunk in chunks]
    assert ordenes == sorted(ordenes)
    assert ordenes == list(range(len(chunks)))
    for chunk in chunks:
        assert chunk.embedding


async def test_procesar_documento_sin_texto_extraible_queda_en_error() -> None:
    repositorio = FakeDocumentoRepository()
    documento_id = await _crear_documento_pendiente(repositorio)
    paginas_vacias = [PaginaExtraida(numero=1, texto="   ")]
    service = ProcesamientoDocumentoService(
        repositorio,
        FakeExtractorTexto(paginas_vacias),
        FakeEmbeddingClient(),
        FakeClasificadorDocumento(),
    )

    await service.procesar(documento_id)

    documento = await repositorio.obtener(documento_id)
    assert documento is not None
    assert documento.estado == "error"
    assert documento.error_detalle == "No se pudo extraer texto del documento"


async def test_procesar_documento_falla_de_embeddings_queda_en_error_generico() -> None:
    repositorio = FakeDocumentoRepository()
    documento_id = await _crear_documento_pendiente(repositorio)
    paginas = [PaginaExtraida(numero=1, texto="Texto suficiente para generar un chunk. " * 10)]
    service = ProcesamientoDocumentoService(
        repositorio,
        FakeExtractorTexto(paginas),
        FakeEmbeddingClient(falla=True),
        FakeClasificadorDocumento(),
    )

    await service.procesar(documento_id)

    documento = await repositorio.obtener(documento_id)
    assert documento is not None
    assert documento.estado == "error"
    assert documento.error_detalle == "No se pudo procesar el documento"
    # El mensaje expuesto es genérico: nunca el detalle técnico de la excepción real.
    assert "OpenAI" not in (documento.error_detalle or "")


async def test_procesar_documento_dos_veces_es_idempotente_no_duplica_chunks() -> None:
    repositorio = FakeDocumentoRepository()
    documento_id = await _crear_documento_pendiente(repositorio)
    paginas = [PaginaExtraida(numero=1, texto="Contenido de prueba para el chunking. " * 20)]
    service = ProcesamientoDocumentoService(
        repositorio,
        FakeExtractorTexto(paginas),
        FakeEmbeddingClient(),
        FakeClasificadorDocumento(),
    )

    await service.procesar(documento_id)
    cantidad_primera_vez = len(repositorio.chunks_de(documento_id))

    await service.procesar(documento_id)
    cantidad_segunda_vez = len(repositorio.chunks_de(documento_id))

    assert cantidad_primera_vez > 0
    assert cantidad_segunda_vez == cantidad_primera_vez


async def test_procesar_documento_inexistente_no_lanza() -> None:
    repositorio = FakeDocumentoRepository()
    service = ProcesamientoDocumentoService(
        repositorio, FakeExtractorTexto(), FakeEmbeddingClient(), FakeClasificadorDocumento()
    )

    # No debe lanzar ni intentar marcar estados sobre un documento que ya no existe.
    await service.procesar(999)


async def test_procesar_con_clasificacion_pendiente_clasifica_y_guarda_el_tipo() -> None:
    repositorio = FakeDocumentoRepository()
    documento_id = await repositorio.crear(
        nombre_archivo="documento.pdf",
        tipo_contenido="application/pdf",
        tamano_bytes=100,
        idioma="spa",
        creado_por_id=1,
        contenido=b"%PDF-1.4 contenido de prueba",
        sha256="a" * 64,
        clasificacion_pendiente=True,
    )
    paginas = [PaginaExtraida(numero=1, texto="Un contrato de compraventa internacional. " * 10)]
    clasificador = FakeClasificadorDocumento(tipo="contrato")
    service = ProcesamientoDocumentoService(
        repositorio, FakeExtractorTexto(paginas), FakeEmbeddingClient(), clasificador
    )

    await service.procesar(documento_id)

    documento = await repositorio.obtener(documento_id)
    assert documento is not None
    assert documento.estado == "procesado"
    assert documento.tipo_documento == "contrato"
    assert len(clasificador.llamadas) == 1
    assert repositorio.clasificacion_pendiente_de(documento_id) is False


async def test_procesar_sin_clasificacion_pendiente_no_llama_al_clasificador() -> None:
    repositorio = FakeDocumentoRepository()
    documento_id = await _crear_documento_pendiente(repositorio)
    paginas = [PaginaExtraida(numero=1, texto="Texto suficiente para procesar. " * 10)]
    clasificador = FakeClasificadorDocumento(tipo="contrato")
    service = ProcesamientoDocumentoService(
        repositorio, FakeExtractorTexto(paginas), FakeEmbeddingClient(), clasificador
    )

    await service.procesar(documento_id)

    documento = await repositorio.obtener(documento_id)
    assert documento is not None
    # Sin clasificación pendiente, el tipo queda en el valor por defecto de la carga.
    assert documento.tipo_documento == "otro"
    assert clasificador.llamadas == []


async def test_procesar_documento_normativa_asigna_articulo_a_los_chunks() -> None:
    repositorio = FakeDocumentoRepository()
    documento_id = await repositorio.crear(
        nombre_archivo="cauca.pdf",
        tipo_contenido="application/pdf",
        tamano_bytes=100,
        idioma="spa",
        creado_por_id=1,
        contenido=b"%PDF-1.4 contenido de prueba",
        sha256="b" * 64,
        tipo_documento="normativa",
    )
    texto = (
        "Artículo 94. Tránsito aduanero. "
        + "El régimen aplica a las mercancías. " * 30
        + "\n\nArtículo 95. Base de datos regional. "
        + "Los países comparten información. " * 10
    )
    paginas = [PaginaExtraida(numero=1, texto=texto)]
    service = ProcesamientoDocumentoService(
        repositorio,
        FakeExtractorTexto(paginas),
        FakeEmbeddingClient(),
        FakeClasificadorDocumento(),
    )

    await service.procesar(documento_id)

    chunks = repositorio.chunks_de(documento_id)
    assert {chunk.articulo for chunk in chunks} == {"94", "95"}
    # El artículo 94, más largo, se subdivide en varios fragmentos que comparten el número.
    chunks_94 = [chunk for chunk in chunks if chunk.articulo == "94"]
    assert len(chunks_94) >= 2


async def test_procesar_documento_limpia_encabezados_repetidos_antes_de_chunkear() -> None:
    repositorio = FakeDocumentoRepository()
    documento_id = await _crear_documento_pendiente(repositorio)
    marcas = ("alfa", "beta", "gamma", "delta")
    paginas = [
        PaginaExtraida(
            numero=i,
            texto=f"CAUCA IV\nPágina {i} de 4\nContenido único {marca} de la página.",
        )
        for i, marca in enumerate(marcas, start=1)
    ]
    service = ProcesamientoDocumentoService(
        repositorio,
        FakeExtractorTexto(paginas),
        FakeEmbeddingClient(),
        FakeClasificadorDocumento(),
    )

    await service.procesar(documento_id)

    contenido_total = " ".join(chunk.contenido for chunk in repositorio.chunks_de(documento_id))
    assert "CAUCA IV" not in contenido_total
    assert "Página" not in contenido_total
    assert "único alfa de la página" in contenido_total


async def test_procesar_con_clasificador_que_falla_queda_procesado_con_tipo_otro() -> None:
    repositorio = FakeDocumentoRepository()
    documento_id = await repositorio.crear(
        nombre_archivo="documento.pdf",
        tipo_contenido="application/pdf",
        tamano_bytes=100,
        idioma="spa",
        creado_por_id=1,
        contenido=b"%PDF-1.4 contenido de prueba",
        sha256="d" * 64,
        clasificacion_pendiente=True,
    )
    paginas = [PaginaExtraida(numero=1, texto="Texto suficiente para procesar. " * 10)]
    # La implementación real de `ClasificadorDocumento` nunca lanza: ante cualquier falla
    # resuelve a "otro". El fake reproduce ese contrato con su valor por defecto.
    clasificador_que_falla = FakeClasificadorDocumento()
    service = ProcesamientoDocumentoService(
        repositorio, FakeExtractorTexto(paginas), FakeEmbeddingClient(), clasificador_que_falla
    )

    await service.procesar(documento_id)

    documento = await repositorio.obtener(documento_id)
    assert documento is not None
    assert documento.estado == "procesado"
    assert documento.tipo_documento == "otro"


# --- toma exclusiva, versión y clasificación concurrente ------------------------------------


async def test_procesar_documento_ya_procesando_no_lo_toma_y_no_lo_modifica() -> None:
    repositorio = FakeDocumentoRepository()
    documento_id = await _crear_documento_pendiente(repositorio)
    tomado_por_otro_proceso = await repositorio.tomar_para_procesar(documento_id)
    assert tomado_por_otro_proceso is not None
    service = ProcesamientoDocumentoService(
        repositorio, FakeExtractorTexto(), FakeEmbeddingClient(), FakeClasificadorDocumento()
    )

    tomado = await service.procesar(documento_id)

    assert tomado is False
    documento = await repositorio.obtener(documento_id)
    assert documento is not None
    assert documento.estado == "procesando"
    assert documento.cantidad_chunks == 0


class _ExtractorQueIncrementaVersion:
    """Extractor fake que, al ser llamado, incrementa la versión del documento en el
    repositorio: simula que un reprocesamiento más nuevo se encoló (p. ej. un PATCH que cambió
    el tipo) justo mientras este procesamiento seguía en vuelo.
    """

    def __init__(
        self,
        repositorio: FakeDocumentoRepository,
        documento_id: int,
        paginas: list[PaginaExtraida],
    ) -> None:
        self._repositorio = repositorio
        self._documento_id = documento_id
        self._paginas = paginas

    async def extraer(
        self, contenido: bytes, tipo_contenido: str, idioma: str
    ) -> list[PaginaExtraida]:
        await self._repositorio.incrementar_version(self._documento_id)
        return self._paginas


async def test_procesar_version_superada_en_vuelo_no_guarda_ni_cambia_estado() -> None:
    repositorio = FakeDocumentoRepository()
    documento_id = await _crear_documento_pendiente(repositorio)
    paginas = [PaginaExtraida(numero=1, texto="Contenido de prueba para el chunking. " * 20)]
    extractor = _ExtractorQueIncrementaVersion(repositorio, documento_id, paginas)
    service = ProcesamientoDocumentoService(
        repositorio, extractor, FakeEmbeddingClient(), FakeClasificadorDocumento()
    )

    tomado = await service.procesar(documento_id)

    assert tomado is True
    documento = await repositorio.obtener(documento_id)
    assert documento is not None
    # La versión cambió mientras este procesamiento corría (ya hay uno más nuevo encolado): el
    # resultado se descarta sin tocar el estado ni guardar chunks.
    assert documento.estado == "procesando"
    assert documento.cantidad_chunks == 0


class _ClasificadorQueEditaManualmente:
    """Clasificador fake que, al clasificar, simula que un PATCH manual cambia el tipo del
    documento justo mientras la clasificación automática está en curso.
    """

    def __init__(
        self,
        repositorio: FakeDocumentoRepository,
        documento_id: int,
        tipo_clasificado: TipoDocumento,
    ) -> None:
        self._repositorio = repositorio
        self._documento_id = documento_id
        self._tipo_clasificado = tipo_clasificado
        self.llamadas: list[str] = []

    async def clasificar(self, texto: str) -> TipoDocumento:
        self.llamadas.append(texto)
        await self._repositorio.actualizar(
            self._documento_id, "contrato", None, actualizar_norma=False, reencolar=False
        )
        return self._tipo_clasificado


async def test_procesar_no_pisa_una_clasificacion_manual_hecha_durante_el_procesamiento() -> None:
    repositorio = FakeDocumentoRepository()
    documento_id = await repositorio.crear(
        nombre_archivo="doc.pdf",
        tipo_contenido="application/pdf",
        tamano_bytes=10,
        idioma="spa",
        creado_por_id=1,
        contenido=b"contenido",
        sha256="e" * 64,
        clasificacion_pendiente=True,
    )
    paginas = [PaginaExtraida(numero=1, texto="Texto suficiente para procesar. " * 10)]
    clasificador = _ClasificadorQueEditaManualmente(repositorio, documento_id, "aduanero")
    service = ProcesamientoDocumentoService(
        repositorio, FakeExtractorTexto(paginas), FakeEmbeddingClient(), clasificador
    )

    await service.procesar(documento_id)

    documento = await repositorio.obtener(documento_id)
    assert documento is not None
    assert documento.estado == "procesado"
    # La edición manual (a "contrato") gana sobre el resultado del clasificador ("aduanero").
    assert documento.tipo_documento == "contrato"
    assert len(clasificador.llamadas) == 1
