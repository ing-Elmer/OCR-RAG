import { AppLayout } from '@/components/layout/AppLayout';
import { FormularioCargaDocumento } from '@/components/Documentos/FormularioCargaDocumento';
import { TablaDocumentos } from '@/components/Documentos/TablaDocumentos';
import { Button } from '@/components/ui/Button';
import { ErrorState } from '@/components/ui/ErrorState';
import { LoadingState } from '@/components/ui/LoadingState';
import { useUser } from '@/context/UserContext';
import { useDocumentos } from '@/hooks/useDocumentos';

/** Pantalla de Documentos: carga (si hay permiso) y listado paginado con estado en vivo. */
export function DocumentosPage() {
  const { hasPermission } = useUser();
  const {
    data,
    isLoading,
    error,
    reload,
    limite,
    offset,
    puedeIrAnterior,
    puedeIrSiguiente,
    irAPaginaAnterior,
    irAPaginaSiguiente,
  } = useDocumentos();

  const total = data?.meta.total ?? 0;
  const desde = total === 0 ? 0 : offset + 1;
  const hasta = Math.min(offset + limite, total);

  return (
    <AppLayout>
      <h1 className="mb-6 text-xl font-semibold text-text">Documentos</h1>

      {hasPermission('DOCUMENTOS_CARGAR') && <FormularioCargaDocumento onCargado={reload} />}

      <section aria-labelledby="listado-documentos-titulo" className="rounded-lg border border-border bg-white p-6">
        <h2 id="listado-documentos-titulo" className="mb-4 text-lg font-medium text-text">
          Documentos cargados
        </h2>

        {isLoading && !data && <LoadingState label="Cargando documentos..." />}
        {!isLoading && error && <ErrorState message={error} onRetry={reload} />}
        {!error && data && (
          <>
            <TablaDocumentos documentos={data.documentos} />
            {total > 0 && (
              <div className="mt-4 flex items-center justify-between text-sm text-muted">
                <span>
                  {desde}–{hasta} de {total}
                </span>
                <div className="flex gap-2">
                  <Button variant="secondary" onClick={irAPaginaAnterior} disabled={!puedeIrAnterior}>
                    Anterior
                  </Button>
                  <Button variant="secondary" onClick={irAPaginaSiguiente} disabled={!puedeIrSiguiente}>
                    Siguiente
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </section>
    </AppLayout>
  );
}
