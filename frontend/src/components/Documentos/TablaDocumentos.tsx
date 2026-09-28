import { useState } from 'react';
import { BadgeEstadoDocumento } from '@/components/Documentos/BadgeEstadoDocumento';
import { BadgeTipoDocumento } from '@/components/Documentos/BadgeTipoDocumento';
import { ModalEditarDocumento } from '@/components/Documentos/ModalEditarDocumento';
import { createDataTableColumnHelper, DataTable, type DataTableColumn } from '@/components/ui/DataTable';
import { Button } from '@/components/ui/Button';
import { formatearTamanoArchivo } from '@/utils/formatoArchivo';
import type { Documento } from '@/types/documento';

interface TablaDocumentosProps {
  documentos: Documento[];
  /** Si puede editar (permiso DOCUMENTOS_CARGAR), se agrega la columna Acciones con Editar. */
  puedeEditar: boolean;
  /** Se llama cuando una edición se guardó bien, para refrescar el listado. */
  onActualizado: () => void;
}

const columnHelper = createDataTableColumnHelper<Documento>();

const FORMATO_FECHA = new Intl.DateTimeFormat('es-AR', { dateStyle: 'short', timeStyle: 'short' });

// Se usan columnas "display" (en vez de `accessor`) y se lee `row.original`
// en cada `cell`: con `accessor` cada columna infiere un `TValue` distinto
// (string, number, EstadoDocumento...) y ese array deja de ser asignable al
// `TValue = unknown` que exige `DataTableColumn<TData>`, por la varianza de
// las funciones de columna de `@tanstack/react-table`.
const COLUMNAS_BASE: Array<DataTableColumn<Documento>> = [
  columnHelper.display({
    id: 'nombreArchivo',
    header: 'Nombre',
    cell: (info) => {
      const documento = info.row.original;
      return (
        <div>
          <p className="font-medium text-text">{documento.nombreArchivo}</p>
          {documento.fuenteUrl && (
            <a
              href={documento.fuenteUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-muted underline decoration-dotted underline-offset-2 hover:text-primary"
            >
              Ver fuente original
            </a>
          )}
          {documento.estado === 'error' && documento.errorDetalle && (
            <p className="mt-0.5 text-xs text-danger">{documento.errorDetalle}</p>
          )}
        </div>
      );
    },
  }),
  columnHelper.display({
    id: 'tipoDocumento',
    header: 'Tipo',
    cell: (info) => <BadgeTipoDocumento tipo={info.row.original.tipoDocumento} />,
  }),
  columnHelper.display({
    id: 'norma',
    header: 'Norma',
    cell: (info) => info.row.original.norma ?? '—',
  }),
  columnHelper.display({
    id: 'tipoContenido',
    header: 'Formato',
    cell: (info) => info.row.original.tipoContenido,
  }),
  columnHelper.display({
    id: 'tamanoBytes',
    header: 'Tamaño',
    cell: (info) => formatearTamanoArchivo(info.row.original.tamanoBytes),
  }),
  columnHelper.display({
    id: 'estado',
    header: 'Estado',
    cell: (info) => <BadgeEstadoDocumento estado={info.row.original.estado} />,
  }),
  columnHelper.display({
    id: 'paginas',
    header: 'Páginas',
    cell: (info) => info.row.original.paginas ?? '—',
  }),
  columnHelper.display({
    id: 'cantidadChunks',
    header: 'Fragmentos',
    cell: (info) => info.row.original.cantidadChunks,
  }),
  columnHelper.display({
    id: 'createdAt',
    header: 'Fecha',
    cell: (info) => FORMATO_FECHA.format(new Date(info.row.original.createdAt)),
  }),
];

function construirColumnas(
  puedeEditar: boolean,
  onEditar: (documento: Documento) => void,
): Array<DataTableColumn<Documento>> {
  if (!puedeEditar) {
    return COLUMNAS_BASE;
  }

  return [
    ...COLUMNAS_BASE,
    columnHelper.display({
      id: 'acciones',
      header: 'Acciones',
      cell: (info) => (
        <Button
          variant="secondary"
          onClick={() => onEditar(info.row.original)}
          aria-label={`Editar ${info.row.original.nombreArchivo}`}
        >
          Editar
        </Button>
      ),
    }),
  ];
}

/** Tabla de documentos cargados: estado con badge de color, tipo/norma y detalle de error inline. */
export function TablaDocumentos({ documentos, puedeEditar, onActualizado }: TablaDocumentosProps) {
  const [documentoEditando, setDocumentoEditando] = useState<Documento | null>(null);

  const columnas = construirColumnas(puedeEditar, setDocumentoEditando);

  return (
    <>
      <DataTable
        data={documentos}
        columns={columnas}
        getRowId={(documento) => String(documento.id)}
        emptyMessage="Todavía no se cargó ningún documento."
      />
      {documentoEditando && (
        <ModalEditarDocumento
          documento={documentoEditando}
          isOpen={true}
          onClose={() => setDocumentoEditando(null)}
          onGuardado={() => {
            setDocumentoEditando(null);
            onActualizado();
          }}
        />
      )}
    </>
  );
}
