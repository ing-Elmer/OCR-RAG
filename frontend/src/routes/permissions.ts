import type { Usuario } from '@/types/usuario';

/**
 * Requisito de acceso a una ruta o acción: un código de permiso puntual y/o
 * una lista de roles habilitados. Si no se indica ninguno, cualquier usuario
 * autenticado cumple el requisito.
 */
export interface RequisitoAcceso {
  permissionCode?: string;
  roles?: string[];
}

/**
 * Única función de evaluación de permisos del frontend: la usan `PrivateRoute`
 * y cualquier otro componente que necesite decidir qué mostrar. Es solo UX;
 * el backend siempre revalida el permiso real.
 */
export function cumpleRequisitoAcceso(usuario: Usuario | null, requisito?: RequisitoAcceso): boolean {
  if (!requisito || (!requisito.permissionCode && !requisito.roles?.length)) {
    return true;
  }
  if (!usuario) {
    return false;
  }

  const cumplePermiso = !requisito.permissionCode || usuario.permisos.includes(requisito.permissionCode);
  const cumpleRol = !requisito.roles?.length || requisito.roles.some((rol) => usuario.roles.includes(rol));

  return cumplePermiso && cumpleRol;
}
