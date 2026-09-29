import { flexRender, type RowData } from '@tanstack/react-table';
import { legacyCreateColumnHelper, useLegacyTable, type LegacyColumnDef } from '@tanstack/react-table/legacy';
import { EmptyState } from '@/components/ui/EmptyState';

/**
 * Definición de columna del `DataTable`. Se apoya en la capa de
 * compatibilidad v8 de `@tanstack/react-table` (`useLegacyTable`): la API
 * reactiva nueva de v9 (`useTable` + `features`) pide registrar a mano cada
 * feature (orden, sorting, paginación, etc.) y todavía no tenemos casos que
 * la necesiten. Si una feature futura la requiere, se migra esta pieza sola.
 */
export type DataTableColumn<TData extends RowData> = LegacyColumnDef<TData>;

export { legacyCreateColumnHelper as createDataTableColumnHelper };

interface DataTableProps<TData extends RowData> {
  data: TData[];
  columns: Array<DataTableColumn<TData>>;
  /** Identificador estable de cada fila (por defecto, el índice). */
  getRowId?: (row: TData, index: number) => string;
  emptyMessage?: string;
}

/**
 * Tabla compartida sobre `@tanstack/react-table`, con estado vacío incluido.
 * Ninguna feature arma su propia tabla a mano: extiende esta.
 */
export function DataTable<TData extends RowData>({
  data,
  columns,
  getRowId,
  emptyMessage = 'No hay datos para mostrar.',
}: DataTableProps<TData>) {
  const table = useLegacyTable({ data, columns, getRowId });

  if (data.length === 0) {
    return <EmptyState message={emptyMessage} />;
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-left text-sm">
        <thead className="bg-surface text-muted">
          {table.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <th key={header.id} scope="col" className="px-4 py-3 font-medium">
                  {header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody className="divide-y divide-border">
          {table.getRowModel().rows.map((row) => (
            <tr key={row.id}>
              {row.getVisibleCells().map((cell) => (
                <td key={cell.id} className="px-4 py-3 text-text">
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
