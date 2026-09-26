"""Validaciones de negocio sobre consultas (RAG): documentos filtrados válidos."""

from ocr_rag.core.exceptions import ValidationError
from ocr_rag.core.repositories import DocumentoRepository


class ConsultaValidator:
    """Valida que los documentos indicados en un filtro de consulta existan y estén procesados."""

    def __init__(self, repositorio: DocumentoRepository) -> None:
        self._repositorio = repositorio

    async def validar_documentos(self, documento_ids: list[int] | None) -> None:
        """Si se filtra por `documento_ids`, verifica que todos existan y estén `procesado`.

        Lanza `ValidationError` si alguno no existe o no está procesado.
        """
        if not documento_ids:
            return

        ids_procesados = await self._repositorio.obtener_ids_procesados(documento_ids)
        ids_invalidos = set(documento_ids) - ids_procesados
        if ids_invalidos:
            ids_ordenados = ", ".join(str(id_) for id_ in sorted(ids_invalidos))
            raise ValidationError(
                "Uno o más documentos no existen o todavía no están procesados",
                {"documentoIds": [f"Documentos inválidos: {ids_ordenados}"]},
            )
