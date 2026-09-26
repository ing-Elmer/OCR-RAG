import { useCallback, useEffect, useRef, useState } from 'react';

export interface AsyncResourceState<T> {
  data: T | null;
  isLoading: boolean;
  error: string | null;
  reload: () => void;
}

/**
 * Hook compartido para cargar un recurso asíncrono. Los hooks de cada
 * feature lo usan en vez de repetir `isLoading`/`error`/`reload` a mano.
 *
 * `isLoading` se deriva comparando el pedido en curso (`reloadToken`) contra
 * el último que terminó (`resolvedToken`), en vez de setearlo a mano al
 * arrancar el efecto: así ningún `setState` corre en el cuerpo síncrono del
 * efecto, todos quedan dentro de los callbacks de la promesa.
 *
 * @param loader función que trae el recurso; se vuelve a crear en cada
 *   render donde cambien sus dependencias (pasalas memoizadas con
 *   `useCallback` desde el hook que lo consume).
 */
export function useAsyncResource<T>(loader: () => Promise<T>): AsyncResourceState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);
  const [resolvedToken, setResolvedToken] = useState(-1);

  const loaderRef = useRef(loader);
  useEffect(() => {
    loaderRef.current = loader;
  }, [loader]);

  useEffect(() => {
    let cancelado = false;

    loaderRef
      .current()
      .then((resultado) => {
        if (cancelado) {
          return;
        }
        setData(resultado);
        setError(null);
      })
      .catch((err: unknown) => {
        if (cancelado) {
          return;
        }
        setError(err instanceof Error ? err.message : 'Ocurrió un error inesperado.');
      })
      .finally(() => {
        if (!cancelado) {
          setResolvedToken(reloadToken);
        }
      });

    return () => {
      cancelado = true;
    };
  }, [reloadToken]);

  const reload = useCallback(() => {
    setReloadToken((valorActual) => valorActual + 1);
  }, []);

  return { data, error, isLoading: resolvedToken !== reloadToken, reload };
}
