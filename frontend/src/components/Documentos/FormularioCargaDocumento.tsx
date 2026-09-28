import { useId, useRef, useState, type FormEvent } from 'react';
import { ApiError } from '@/services/ApiClient';
import { cargarDocumento } from '@/services/DocumentoService';
import { toFormErrors, type FormErrors } from '@/components/ui/helpers/toFormErrors';
import { validarArchivoDocumento } from '@/utils/validarArchivoDocumento';
import { OPCIONES_TIPO_DOCUMENTO } from '@/utils/tipoDocumento';
import { Button } from '@/components/ui/Button';
import type { TipoDocumento } from '@/types/documento';

const MENSAJE_ERROR_GENERICO = 'No se pudo cargar el documento. Intentá de nuevo.';

const OPCIONES_IDIOMA = [
  { valor: 'spa+eng', etiqueta: 'Español + Inglés' },
  { valor: 'spa', etiqueta: 'Español' },
  { valor: 'eng', etiqueta: 'Inglés' },
];

/** Valor del select que indica que el tipo de documento no se envía: lo clasifica la IA al procesar. */
const DETECCION_AUTOMATICA = '';

interface FormularioCargaDocumentoProps {
  /** Se llama cuando la carga terminó bien, para refrescar el listado. */
  onCargado: () => void;
}

/** Formulario de carga de un documento (PDF o imagen) para procesar con OCR. */
export function FormularioCargaDocumento({ onCargado }: FormularioCargaDocumentoProps) {
  const idArchivo = useId();
  const idIdioma = useId();
  const idTipoDocumento = useId();
  const inputArchivoRef = useRef<HTMLInputElement>(null);

  const [idioma, setIdioma] = useState(OPCIONES_IDIOMA[0].valor);
  const [tipoDocumento, setTipoDocumento] = useState<TipoDocumento | typeof DETECCION_AUTOMATICA>(DETECCION_AUTOMATICA);
  const [fieldErrors, setFieldErrors] = useState<FormErrors>({});
  const [mensajeError, setMensajeError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFieldErrors({});
    setMensajeError(null);

    const archivo = inputArchivoRef.current?.files?.[0];
    if (!archivo) {
      setFieldErrors({ archivo: 'Elegí un archivo para cargar.' });
      return;
    }

    const validacion = validarArchivoDocumento(archivo);
    if (!validacion.esValido) {
      setFieldErrors({ archivo: validacion.mensaje ?? MENSAJE_ERROR_GENERICO });
      return;
    }

    setIsSubmitting(true);
    try {
      await cargarDocumento({
        archivo,
        idioma,
        tipoDocumento: tipoDocumento === DETECCION_AUTOMATICA ? undefined : tipoDocumento,
      });
      if (inputArchivoRef.current) {
        inputArchivoRef.current.value = '';
      }
      setTipoDocumento(DETECCION_AUTOMATICA);
      onCargado();
    } catch (error) {
      if (error instanceof ApiError) {
        setFieldErrors(toFormErrors(error));
        setMensajeError(error.message);
      } else {
        setMensajeError(MENSAJE_ERROR_GENERICO);
      }
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
      className="mb-8 rounded-lg border border-border bg-white p-6"
    >
      <h2 className="mb-4 text-lg font-medium text-text">Cargar documento</h2>

      {mensajeError && (
        <p role="alert" className="mb-4 rounded-md bg-danger-surface px-3 py-2 text-sm text-danger">
          {mensajeError}
        </p>
      )}

      <div className="mb-4">
        <label htmlFor={idArchivo} className="mb-1 block text-sm font-medium text-text">
          Archivo (PDF, PNG, JPG o TIFF, máx. 20 MB)
        </label>
        <input
          ref={inputArchivoRef}
          id={idArchivo}
          name="archivo"
          type="file"
          accept="application/pdf,image/png,image/jpeg,image/tiff"
          disabled={isSubmitting}
          aria-invalid={Boolean(fieldErrors.archivo)}
          aria-describedby={fieldErrors.archivo ? `${idArchivo}-error` : undefined}
          className="w-full rounded-md border border-border px-3 py-2 text-sm text-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
        />
        {fieldErrors.archivo && (
          <p id={`${idArchivo}-error`} role="alert" className="mt-1 text-sm text-danger">
            {fieldErrors.archivo}
          </p>
        )}
      </div>

      <div className="mb-4">
        <label htmlFor={idIdioma} className="mb-1 block text-sm font-medium text-text">
          Idioma del documento
        </label>
        <select
          id={idIdioma}
          name="idioma"
          value={idioma}
          onChange={(event) => setIdioma(event.target.value)}
          disabled={isSubmitting}
          className="w-full rounded-md border border-border px-3 py-2 text-sm text-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
        >
          {OPCIONES_IDIOMA.map((opcion) => (
            <option key={opcion.valor} value={opcion.valor}>
              {opcion.etiqueta}
            </option>
          ))}
        </select>
        {fieldErrors.idioma && (
          <p role="alert" className="mt-1 text-sm text-danger">
            {fieldErrors.idioma}
          </p>
        )}
      </div>

      <div className="mb-4">
        <label htmlFor={idTipoDocumento} className="mb-1 block text-sm font-medium text-text">
          Tipo de documento
        </label>
        <select
          id={idTipoDocumento}
          name="tipoDocumento"
          value={tipoDocumento}
          onChange={(event) => setTipoDocumento(event.target.value as TipoDocumento | typeof DETECCION_AUTOMATICA)}
          disabled={isSubmitting}
          className="w-full rounded-md border border-border px-3 py-2 text-sm text-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
        >
          <option value={DETECCION_AUTOMATICA}>Detectar automáticamente</option>
          {OPCIONES_TIPO_DOCUMENTO.map((opcion) => (
            <option key={opcion.valor} value={opcion.valor}>
              {opcion.etiqueta}
            </option>
          ))}
        </select>
        {fieldErrors.tipoDocumento && (
          <p role="alert" className="mt-1 text-sm text-danger">
            {fieldErrors.tipoDocumento}
          </p>
        )}
      </div>

      <Button type="submit" isLoading={isSubmitting}>
        Cargar documento
      </Button>
    </form>
  );
}
