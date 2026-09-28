import { useId, useState, type FormEvent } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { toFormErrors, type FormErrors } from '@/components/ui/helpers/toFormErrors';
import { ApiError } from '@/services/ApiClient';
import { actualizarDocumento, type DatosActualizarDocumento } from '@/services/DocumentoService';
import { OPCIONES_TIPO_DOCUMENTO } from '@/utils/tipoDocumento';
import type { Documento, TipoDocumento } from '@/types/documento';

const MENSAJE_ERROR_GENERICO = 'No se pudo actualizar el documento. Intentá de nuevo.';

interface ModalEditarDocumentoProps {
  documento: Documento;
  isOpen: boolean;
  onClose: () => void;
  /** Se llama cuando la edición se guardó bien, para cerrar el modal y refrescar la tabla. */
  onGuardado: () => void;
}

/** Modal para editar el tipo y la norma de un documento ya cargado (`PATCH /api/documentos/{id}`). */
export function ModalEditarDocumento({ documento, isOpen, onClose, onGuardado }: ModalEditarDocumentoProps) {
  const idTipoDocumento = useId();

  const [tipoDocumento, setTipoDocumento] = useState<TipoDocumento>(documento.tipoDocumento);
  const [norma, setNorma] = useState(documento.norma ?? '');
  const [fieldErrors, setFieldErrors] = useState<FormErrors>({});
  const [mensajeError, setMensajeError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFieldErrors({});
    setMensajeError(null);

    const normaNormalizada = norma.trim();
    const datos: DatosActualizarDocumento = {};
    if (tipoDocumento !== documento.tipoDocumento) {
      datos.tipoDocumento = tipoDocumento;
    }
    if (normaNormalizada !== (documento.norma ?? '')) {
      // Vaciar el campo quita la norma: el backend no acepta texto vacío, sí `null`.
      datos.norma = normaNormalizada === '' ? null : normaNormalizada;
    }

    if (Object.keys(datos).length === 0) {
      onClose();
      return;
    }

    setIsSubmitting(true);
    try {
      await actualizarDocumento(documento.id, datos);
      onGuardado();
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
    <Modal isOpen={isOpen} title={`Editar ${documento.nombreArchivo}`} onClose={onClose}>
      <form
        onSubmit={(event) => {
          void handleSubmit(event);
        }}
        noValidate
      >
        {mensajeError && (
          <p role="alert" className="mb-4 rounded-md bg-danger-surface px-3 py-2 text-sm text-danger">
            {mensajeError}
          </p>
        )}

        <p className="mb-4 rounded-md bg-warning-surface px-3 py-2 text-sm text-warning">
          Cambiar a o desde Normativa vuelve a procesar el documento.
        </p>

        <div className="mb-4">
          <label htmlFor={idTipoDocumento} className="mb-1 block text-sm font-medium text-text">
            Tipo de documento
          </label>
          <select
            id={idTipoDocumento}
            name="tipoDocumento"
            value={tipoDocumento}
            onChange={(event) => setTipoDocumento(event.target.value as TipoDocumento)}
            disabled={isSubmitting}
            aria-invalid={Boolean(fieldErrors.tipoDocumento)}
            className="w-full rounded-md border border-border px-3 py-2 text-sm text-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary"
          >
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

        <Input
          label="Norma"
          name="norma"
          value={norma}
          onChange={(event) => setNorma(event.target.value)}
          disabled={isSubmitting}
          maxLength={100}
          error={fieldErrors.norma}
        />

        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose} disabled={isSubmitting}>
            Cancelar
          </Button>
          <Button type="submit" isLoading={isSubmitting}>
            Guardar
          </Button>
        </div>
      </form>
    </Modal>
  );
}
