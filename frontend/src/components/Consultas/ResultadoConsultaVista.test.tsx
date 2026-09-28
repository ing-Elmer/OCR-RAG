import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { ResultadoConsultaVista } from '@/components/Consultas/ResultadoConsultaVista';
import type { FuenteConsulta, ResultadoConsulta } from '@/types/consulta';

function fuente(parcial: Partial<FuenteConsulta>): FuenteConsulta {
  return {
    documentoId: 1,
    nombreArchivo: 'cauca.pdf',
    fuenteUrl: null,
    orden: 1,
    pagina: null,
    norma: null,
    articulo: null,
    fragmento: 'texto',
    similitud: 0.8,
    tipoDocumento: 'otro',
    ...parcial,
  };
}

describe('ResultadoConsultaVista', () => {
  it('numera las fuentes según su posición, igual que las citas [n] de la respuesta', () => {
    // `orden` es la posición del fragmento dentro de su documento: no debe usarse como número de cita.
    const resultado: ResultadoConsulta = {
      respuesta: 'Según [1] y [2]…',
      fuentes: [
        fuente({ documentoId: 1, orden: 37, nombreArchivo: 'cauca.pdf' }),
        fuente({ documentoId: 2, orden: 5, nombreArchivo: 'convenio.pdf' }),
      ],
    };

    render(<ResultadoConsultaVista resultado={resultado} />);

    const items = screen.getAllByRole('listitem');
    expect(items[0]).toHaveTextContent('[1] cauca.pdf');
    expect(items[1]).toHaveTextContent('[2] convenio.pdf');
    expect(screen.queryByText(/\[37\]/)).not.toBeInTheDocument();
  });

  it('muestra el nombre como link a la fuente original cuando hay fuenteUrl', () => {
    const resultado: ResultadoConsulta = {
      respuesta: 'Según [1]…',
      fuentes: [fuente({ fuenteUrl: 'https://www.sieca.int/cauca.pdf' })],
    };

    render(<ResultadoConsultaVista resultado={resultado} />);

    const link = screen.getByRole('link', { name: 'cauca.pdf' });
    expect(link).toHaveAttribute('href', 'https://www.sieca.int/cauca.pdf');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');
  });

  it('muestra el nombre sin link cuando el documento se subió a mano', () => {
    const resultado: ResultadoConsulta = { respuesta: 'Según [1]…', fuentes: [fuente({})] };

    render(<ResultadoConsultaVista resultado={resultado} />);

    expect(screen.queryByRole('link')).not.toBeInTheDocument();
  });

  it('usa la norma en la cabecera, con artículo y página, cuando la fuente la tiene', () => {
    const resultado: ResultadoConsulta = {
      respuesta: 'Según [1]…',
      fuentes: [
        fuente({
          nombreArchivo: 'cauca.pdf',
          norma: 'CAUCA',
          articulo: '104',
          pagina: 12,
          tipoDocumento: 'normativa',
        }),
      ],
    };

    render(<ResultadoConsultaVista resultado={resultado} />);

    const items = screen.getAllByRole('listitem');
    expect(items[0]).toHaveTextContent('[1] CAUCA · Art. 104 · pág. 12');
    expect(items[0]).not.toHaveTextContent('cauca.pdf');
  });

  it('usa el nombre de archivo en la cabecera cuando la fuente no tiene norma', () => {
    const resultado: ResultadoConsulta = {
      respuesta: 'Según [1]…',
      fuentes: [fuente({ nombreArchivo: 'manifiesto.pdf', pagina: 3 })],
    };

    render(<ResultadoConsultaVista resultado={resultado} />);

    const items = screen.getAllByRole('listitem');
    expect(items[0]).toHaveTextContent('[1] manifiesto.pdf · pág. 3');
  });

  it('el link envuelve la norma cuando hay fuenteUrl y norma a la vez', () => {
    const resultado: ResultadoConsulta = {
      respuesta: 'Según [1]…',
      fuentes: [fuente({ norma: 'CAUCA', fuenteUrl: 'https://www.sieca.int/cauca.pdf' })],
    };

    render(<ResultadoConsultaVista resultado={resultado} />);

    const link = screen.getByRole('link', { name: 'CAUCA' });
    expect(link).toHaveAttribute('href', 'https://www.sieca.int/cauca.pdf');
  });
});
