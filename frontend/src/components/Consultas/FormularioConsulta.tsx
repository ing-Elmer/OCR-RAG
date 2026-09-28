import { useId, useState, type FormEvent } from 'react';
import { ApiError } from '@/services/ApiClient';
import { realizarConsulta } from '@/services/ConsultaService';
import { Button } from '@/components/ui/Button';
import { OPCIONES_TIPO_DOCUMENTO } from '@/utils/tipoDocumento';
import type { Documento, TipoDocumento } from '@/types/documento';
import type { ResultadoConsulta } from '@/types/consulta';

const MENSAJE_ERROR_GENERICO = 'No se pudo responder la consulta. Intentá de nuevo.';
const LONGITUD_MINIMA_PREGUNTA = 3;
const LONGITUD_MAXIMA_PREGUNTA = 2000;

interface FormularioConsultaProps {
  /** Documentos procesados disponibles para filtrar; lista vacía oculta el filtro. */
  documentosDisponibles: Documento[];
  onResultado: (resultado: ResultadoConsulta) => void;
}

/** Formulario de consulta en lenguaje natural sobre el corpus, con filtro opcional de documentos. */
export function FormularioConsulta({ documentosDisponibles, onResultado }: FormularioConsultaProps) {
  const idPregunta = useId();

  const [pregunta, setPregunta] = useState('');
  const [documentoIdsSeleccionados, setDocumentoIdsSeleccionados] = useState<number[]>([]);
  const [tiposSeleccionados, setTiposSeleccionados] = useState<TipoDocumento[]>([]);
  const [mensajeError, setMensajeError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const longitudPregunta = pregunta.trim().length;
  const preguntaValida = longitudPregunta >= LONGITUD_MINIMA_PREGUNTA && pregunta.length <= LONGITUD_MAXIMA_PREGUNTA;

  function alternarDocumento(id: number) {
    setDocumentoIdsSeleccionados((actual) => (actual.includes(id) ? actual.filter((valor) => valor !== id) : [...actual, id]));
  }

  function alternarTipo(tipo: TipoDocumento) {
    setTiposSeleccionados((actual) => (actual.includes(tipo) ? actual.filter((valor) => valor !== tipo) : [...actual, tipo]));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!preguntaValida) {
      setMensajeError(`La pregunta debe tener entre ${LONGITUD_MINIMA_PREGUNTA} y ${LONGITUD_MAXIMA_PREGUNTA} caracteres.`);
      return;
    }

    setMensajeError(null);
    setIsSubmitting(true);
    try {
      const resultado = await realizarConsulta({
        pregunta: pregunta.trim(),
        documentoIds: documentoIdsSeleccionados.length > 0 ? documentoIdsSeleccionados : undefined,
        tiposDocumento: tiposSeleccionados.length > 0 ? tiposSeleccionados : undefined,
      });
      onResultado(resultado);
    } catch (error) {
      setMensajeError(error instanceof ApiError ? error.message : MENSAJE_ERROR_GENERICO);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={(event) => {
        void handleSubmit(event);
      }}
      noValidate
      className="rounded-lg border border-border bg-white p-6"
    >
      {mensajeError && (
        <p role="alert" className="mb-4 rounded-md bg-danger-surface px-3 py-2 text-sm text-danger">
          {mensajeError}
        </p>
      )}

      <div className="mb-4">
        <label htmlFor={idPregunta} className="mb-1 block text-sm font-medium text-text">
          Tu pregunta
        </label>
        <textarea
          id={idPregunta}
          name="pregunta"
          rows={4}
          value={pregunta}
          onChange={(event) => setPregunta(event.target.value)}
          maxLength={LONGITUD_MAXIMA_PREGUNTA}
          disabled={isSubmitting}
          aria-describedby={`${idPregunta}-contador`}
          className="w-full rounded-md border border-border px-3 py-2 text-sm text-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
        />
        <p id={`${idPregunta}-contador`} className="mt-1 text-xs text-muted">
          {pregunta.length}/{LONGITUD_MAXIMA_PREGUNTA} caracteres
        </p>
      </div>

      <fieldset className="mb-4">
        <legend className="mb-2 text-sm font-medium text-text">Filtrar por tipo de documento (opcional)</legend>
        <div className="flex flex-wrap gap-3">
          {OPCIONES_TIPO_DOCUMENTO.map((opcion) => (
            <label key={opcion.valor} className="flex items-center gap-2 text-sm text-text">
              <input
                type="checkbox"
                checked={tiposSeleccionados.includes(opcion.valor)}
                onChange={() => alternarTipo(opcion.valor)}
                disabled={isSubmitting}
                className="focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
              />
              {opcion.etiqueta}
            </label>
          ))}
        </div>
      </fieldset>

      {documentosDisponibles.length > 0 && (
        <fieldset className="mb-4">
          <legend className="mb-2 text-sm font-medium text-text">Limitar a documentos (opcional)</legend>
          <div className="flex max-h-48 flex-col gap-2 overflow-y-auto">
            {documentosDisponibles.map((documento) => (
              <label key={documento.id} className="flex items-center gap-2 text-sm text-text">
                <input
                  type="checkbox"
                  checked={documentoIdsSeleccionados.includes(documento.id)}
                  onChange={() => alternarDocumento(documento.id)}
                  disabled={isSubmitting}
                  className="focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
                />
                {documento.nombreArchivo}
              </label>
            ))}
          </div>
        </fieldset>
      )}

      <Button type="submit" isLoading={isSubmitting} disabled={!preguntaValida || isSubmitting}>
        Consultar
      </Button>
    </form>
  );
}
