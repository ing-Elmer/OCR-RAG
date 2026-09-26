import { describe, expect, it } from 'vitest';
import { validarArchivoDocumento } from '@/utils/validarArchivoDocumento';

function crearArchivo(nombre: string, tipo: string, tamanoBytes: number): File {
  const archivo = new File([''], nombre, { type: tipo });
  Object.defineProperty(archivo, 'size', { value: tamanoBytes });
  return archivo;
}

describe('validarArchivoDocumento', () => {
  it('acepta un PDF dentro del límite de tamaño', () => {
    const archivo = crearArchivo('doc.pdf', 'application/pdf', 1024);
    expect(validarArchivoDocumento(archivo)).toEqual({ esValido: true, mensaje: null });
  });

  it('acepta una imagen TIFF dentro del límite de tamaño', () => {
    const archivo = crearArchivo('doc.tiff', 'image/tiff', 1024);
    expect(validarArchivoDocumento(archivo).esValido).toBe(true);
  });

  it('rechaza un tipo de archivo no soportado', () => {
    const archivo = crearArchivo('doc.txt', 'text/plain', 1024);
    const resultado = validarArchivoDocumento(archivo);
    expect(resultado.esValido).toBe(false);
    expect(resultado.mensaje).toMatch(/PDF/);
  });

  it('rechaza un archivo que supera los 20 MB', () => {
    const archivo = crearArchivo('doc.pdf', 'application/pdf', 21 * 1024 * 1024);
    const resultado = validarArchivoDocumento(archivo);
    expect(resultado.esValido).toBe(false);
    expect(resultado.mensaje).toMatch(/20 MB/);
  });

  it('acepta un archivo exactamente en el límite de 20 MB', () => {
    const archivo = crearArchivo('doc.pdf', 'application/pdf', 20 * 1024 * 1024);
    expect(validarArchivoDocumento(archivo).esValido).toBe(true);
  });
});
