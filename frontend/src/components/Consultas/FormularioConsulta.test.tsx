import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { FormularioConsulta } from '@/components/Consultas/FormularioConsulta';
import * as ConsultaService from '@/services/ConsultaService';
import type { ResultadoConsulta } from '@/types/consulta';

const RESULTADO_VACIO: ResultadoConsulta = { respuesta: 'ok', fuentes: [] };

describe('FormularioConsulta', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('no envía tiposDocumento cuando no se marca ningún checkbox', async () => {
    const usuario = userEvent.setup();
    const realizarConsultaMock = vi.spyOn(ConsultaService, 'realizarConsulta').mockResolvedValue(RESULTADO_VACIO);

    render(<FormularioConsulta documentosDisponibles={[]} onResultado={vi.fn()} />);

    await usuario.type(screen.getByLabelText('Tu pregunta'), '¿Qué exige el CAUCA?');
    await usuario.click(screen.getByRole('button', { name: 'Consultar' }));

    await waitFor(() => expect(realizarConsultaMock).toHaveBeenCalledTimes(1));
    expect(realizarConsultaMock.mock.calls[0][0].tiposDocumento).toBeUndefined();
  });

  it('envía los tipos de documento marcados en el filtro', async () => {
    const usuario = userEvent.setup();
    const realizarConsultaMock = vi.spyOn(ConsultaService, 'realizarConsulta').mockResolvedValue(RESULTADO_VACIO);
    const onResultado = vi.fn();

    render(<FormularioConsulta documentosDisponibles={[]} onResultado={onResultado} />);

    await usuario.type(screen.getByLabelText('Tu pregunta'), '¿Qué exige el CAUCA?');
    await usuario.click(screen.getByLabelText('Normativa'));
    await usuario.click(screen.getByLabelText('Documento aduanero'));
    await usuario.click(screen.getByRole('button', { name: 'Consultar' }));

    await waitFor(() => expect(onResultado).toHaveBeenCalledWith(RESULTADO_VACIO));
    expect(realizarConsultaMock).toHaveBeenCalledWith(
      expect.objectContaining({ tiposDocumento: ['normativa', 'aduanero'] }),
    );
  });

  it('desmarcar un tipo ya seleccionado lo saca del filtro', async () => {
    const usuario = userEvent.setup();
    const realizarConsultaMock = vi.spyOn(ConsultaService, 'realizarConsulta').mockResolvedValue(RESULTADO_VACIO);

    render(<FormularioConsulta documentosDisponibles={[]} onResultado={vi.fn()} />);

    await usuario.type(screen.getByLabelText('Tu pregunta'), '¿Qué exige el CAUCA?');
    await usuario.click(screen.getByLabelText('Normativa'));
    await usuario.click(screen.getByLabelText('Normativa'));
    await usuario.click(screen.getByRole('button', { name: 'Consultar' }));

    await waitFor(() => expect(realizarConsultaMock).toHaveBeenCalledTimes(1));
    expect(realizarConsultaMock.mock.calls[0][0].tiposDocumento).toBeUndefined();
  });
});
