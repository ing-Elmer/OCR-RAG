import type { TipoDocumento } from '@/types/documento';

/** Etiqueta legible de cada categoría de documento, para selects, badges y filtros. */
export const ETIQUETAS_TIPO_DOCUMENTO: Record<TipoDocumento, string> = {
  normativa: 'Normativa',
  embarque: 'Documento de embarque',
  aduanero: 'Documento aduanero',
  contrato: 'Contrato / tarifa',
  otro: 'Otro',
};

/** Opciones de tipo de documento en el orden en que se muestran en la UI. */
export const OPCIONES_TIPO_DOCUMENTO: Array<{ valor: TipoDocumento; etiqueta: string }> = [
  { valor: 'normativa', etiqueta: ETIQUETAS_TIPO_DOCUMENTO.normativa },
  { valor: 'embarque', etiqueta: ETIQUETAS_TIPO_DOCUMENTO.embarque },
  { valor: 'aduanero', etiqueta: ETIQUETAS_TIPO_DOCUMENTO.aduanero },
  { valor: 'contrato', etiqueta: ETIQUETAS_TIPO_DOCUMENTO.contrato },
  { valor: 'otro', etiqueta: ETIQUETAS_TIPO_DOCUMENTO.otro },
];
