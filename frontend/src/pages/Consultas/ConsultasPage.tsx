import { useState } from 'react';
import { AppLayout } from '@/components/layout/AppLayout';
import { FormularioConsulta } from '@/components/Consultas/FormularioConsulta';
import { ResultadoConsultaVista } from '@/components/Consultas/ResultadoConsultaVista';
import { useUser } from '@/context/UserContext';
import { useDocumentosProcesados } from '@/hooks/useDocumentosProcesados';
import type { ResultadoConsulta } from '@/types/consulta';

/** Pantalla de Consultas: preguntas en lenguaje natural sobre el corpus procesado. */
export function ConsultasPage() {
  const { hasPermission } = useUser();
  const puedeFiltrarPorDocumento = hasPermission('DOCUMENTOS_VER');
  const { data: documentosProcesados } = useDocumentosProcesados(puedeFiltrarPorDocumento);
  const [resultado, setResultado] = useState<ResultadoConsulta | null>(null);

  return (
    <AppLayout>
      <h1 className="mb-6 text-xl font-semibold text-text">Consultas</h1>

      <FormularioConsulta documentosDisponibles={documentosProcesados ?? []} onResultado={setResultado} />

      {resultado && (
        <div className="mt-6">
          <ResultadoConsultaVista resultado={resultado} />
        </div>
      )}
    </AppLayout>
  );
}
