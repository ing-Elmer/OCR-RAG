import type { ResultadoConsulta } from '@/types/consulta';

interface ResultadoConsultaVistaProps {
  resultado: ResultadoConsulta;
}

/** Muestra la respuesta de una consulta y, si las hay, sus fuentes numeradas. */
export function ResultadoConsultaVista({ resultado }: ResultadoConsultaVistaProps) {
  if (resultado.fuentes.length === 0) {
    return (
      <div role="status" className="rounded-lg border border-border bg-white p-6">
        <p className="whitespace-pre-line text-sm text-text">{resultado.respuesta}</p>
        <p className="mt-4 text-sm text-muted">No se encontraron fuentes para esta respuesta.</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border bg-white p-6">
      <p className="whitespace-pre-line text-sm text-text">{resultado.respuesta}</p>

      <h3 className="mb-2 mt-6 text-sm font-medium text-text">Fuentes</h3>
      <ol className="flex flex-col gap-3">
        {/* El número de cita es la posición en esta lista: el backend numera los contextos
            [1..n] en el mismo orden en que devuelve las fuentes. `orden` es otra cosa. */}
        {resultado.fuentes.map((fuente, indice) => (
          <li key={`${fuente.documentoId}-${fuente.orden}`} className="rounded-md border border-border p-3 text-sm">
            <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
              <p className="font-medium text-text">
                [{indice + 1}]{' '}
                {fuente.fuenteUrl ? (
                  <a
                    href={fuente.fuenteUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="underline decoration-dotted underline-offset-2 hover:text-primary"
                  >
                    {fuente.nombreArchivo}
                  </a>
                ) : (
                  fuente.nombreArchivo
                )}
              </p>
              <p className="text-xs text-muted">
                {fuente.pagina !== null && `Página ${fuente.pagina} · `}
                {(fuente.similitud * 100).toFixed(0)}% de similitud
              </p>
            </div>
            <p className="mt-1 text-text">{fuente.fragmento}</p>
          </li>
        ))}
      </ol>
    </div>
  );
}
