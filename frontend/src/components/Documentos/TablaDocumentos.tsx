import { BadgeEstadoDocumento } from '@/components/Documentos/BadgeEstadoDocumento';
import { createDataTableColumnHelper, DataTable, type DataTableColumn } from '@/components/ui/DataTable';
import { formatearTamanoArchivo } from '@/utils/formatoArchivo';
import type { Documento } from '@/types/documento';

interface TablaDocumentosProps {
  documentos: Documento[];
}

const columnHelper = createDataTableColumnHelper<Documento>();

const FORMATO_FECHA = new Intl.DateTimeFormat('es-AR', { dateStyle: 'short', timeStyle: 'short' });

// Se usan columnas "display" (en vez de `accessor`) y se lee `row.original`
// en cada `cell`: con `accessor` cada columna infiere un `TValue` distinto
// (string, number, EstadoDocumento...) y ese array deja de ser asignable al
// `TValue = unknown` que exige `DataTableColumn<TData>`, por la varianza de
// las funciones de columna de `@tanstack/react-table`.
const columnas: Array<DataTableColumn<Documento>> = [
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
    id: 'tipoContenido',
    header: 'Tipo',
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

/** Tabla de documentos cargados: estado con badge de color y detalle de error inline. */
export function TablaDocumentos({ documentos }: TablaDocumentosProps) {
  return (
    <DataTable
      data={documentos}
      columns={columnas}
      getRowId={(documento) => String(documento.id)}
      emptyMessage="Todavía no se cargó ningún documento."
    />
  );
}
