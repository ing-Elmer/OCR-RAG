import { ETIQUETAS_TIPO_DOCUMENTO } from '@/utils/tipoDocumento';
import type { TipoDocumento } from '@/types/documento';

const ESTILOS_TIPO: Record<TipoDocumento, string> = {
  normativa: 'bg-primary/10 text-primary',
  embarque: 'bg-success-surface text-success',
  aduanero: 'bg-warning-surface text-warning',
  contrato: 'bg-accent-surface text-accent',
  otro: 'bg-surface text-muted',
};

interface BadgeTipoDocumentoProps {
  tipo: TipoDocumento;
}

/** Distintivo de color por categoría del documento, con los tokens `@theme` del proyecto. */
export function BadgeTipoDocumento({ tipo }: BadgeTipoDocumentoProps) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${ESTILOS_TIPO[tipo]}`}>
      {ETIQUETAS_TIPO_DOCUMENTO[tipo]}
    </span>
  );
}
