import type { EstadoDocumento } from '@/types/documento';

const ESTILOS_ESTADO: Record<EstadoDocumento, string> = {
  pendiente: 'bg-warning-surface text-warning',
  procesando: 'bg-primary/10 text-primary',
  procesado: 'bg-success-surface text-success',
  error: 'bg-danger-surface text-danger',
};

const ETIQUETAS_ESTADO: Record<EstadoDocumento, string> = {
  pendiente: 'Pendiente',
  procesando: 'Procesando',
  procesado: 'Procesado',
  error: 'Error',
};

interface BadgeEstadoDocumentoProps {
  estado: EstadoDocumento;
}

/** Distintivo de color por estado del documento, con los tokens `@theme` del proyecto. */
export function BadgeEstadoDocumento({ estado }: BadgeEstadoDocumentoProps) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${ESTILOS_ESTADO[estado]}`}>
      {ETIQUETAS_ESTADO[estado]}
    </span>
  );
}
