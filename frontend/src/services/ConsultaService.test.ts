import MockAdapter from 'axios-mock-adapter';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { api } from '@/api/api';
import { endpoints } from '@/api/endpoints';
import { realizarConsulta } from '@/services/ConsultaService';
import type { ResultadoConsulta } from '@/types/consulta';

describe('ConsultaService', () => {
  let mock: MockAdapter;

  beforeEach(() => {
    mock = new MockAdapter(api);
  });

  afterEach(() => {
    mock.restore();
  });

  it('realizarConsulta envía la pregunta, los documentos y el topK en el body', async () => {
    const resultado: ResultadoConsulta = {
      respuesta: 'Respuesta generada [1]',
      fuentes: [{ documentoId: 1, nombreArchivo: 'a.pdf', fuenteUrl: null, orden: 1, pagina: 2, fragmento: 'texto relevante', similitud: 0.87 }],
    };
    mock.onPost(endpoints.consultas.crear).reply(200, { status: 'Success', message: 'ok', data: resultado, errors: null, meta: null });

    const respuesta = await realizarConsulta({ pregunta: '¿Qué dice el documento?', documentoIds: [1, 2], topK: 5 });

    expect(respuesta).toEqual(resultado);
    expect(JSON.parse(mock.history.post[0].data as string)).toEqual({
      pregunta: '¿Qué dice el documento?',
      documentoIds: [1, 2],
      topK: 5,
    });
  });

  it('realizarConsulta funciona sin filtro de documentos ni topK', async () => {
    const resultado: ResultadoConsulta = { respuesta: 'Sin fuentes', fuentes: [] };
    mock.onPost(endpoints.consultas.crear).reply(200, { status: 'Success', message: 'ok', data: resultado, errors: null, meta: null });

    const respuesta = await realizarConsulta({ pregunta: 'Pregunta mínima' });

    expect(respuesta).toEqual(resultado);
    expect(JSON.parse(mock.history.post[0].data as string)).toEqual({ pregunta: 'Pregunta mínima' });
  });
});
