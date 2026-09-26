import { NavLink } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { useUser } from '@/context/UserContext';
import { cumpleRequisitoAcceso, type RequisitoAcceso } from '@/routes/permissions';
import { Button } from '@/components/ui/Button';

interface EntradaNav extends RequisitoAcceso {
  to: string;
  label: string;
  /** Coincidencia exacta de ruta (evita que "/" quede activo en cualquier página). */
  end?: boolean;
}

const ENTRADAS: EntradaNav[] = [
  { to: '/', label: 'Inicio', end: true },
  { to: '/documentos', label: 'Documentos', permissionCode: 'DOCUMENTOS_VER' },
  { to: '/consultas', label: 'Consultas', permissionCode: 'CONSULTAS_REALIZAR' },
];

const ESTILO_LINK_BASE = 'rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-surface';

/**
 * Barra de navegación de las páginas autenticadas. Cada entrada se muestra
 * solo si el usuario cumple el requisito de acceso, con la misma función
 * (`cumpleRequisitoAcceso`) que usa `PrivateRoute`.
 */
export function NavBar() {
  const { logout } = useAuth();
  const { usuario } = useUser();

  const entradasVisibles = ENTRADAS.filter((entrada) =>
    cumpleRequisitoAcceso(usuario, { permissionCode: entrada.permissionCode, roles: entrada.roles }),
  );

  return (
    <header className="border-b border-border bg-white px-6 py-3">
      <nav className="flex items-center justify-between" aria-label="Navegación principal">
        <div className="flex items-center gap-1">
          <span className="mr-4 text-lg font-semibold text-text">OCR-RAG</span>
          {entradasVisibles.map((entrada) => (
            <NavLink
              key={entrada.to}
              to={entrada.to}
              end={entrada.end}
              className={({ isActive }) => `${ESTILO_LINK_BASE} ${isActive ? 'text-primary' : 'text-muted'}`}
            >
              {entrada.label}
            </NavLink>
          ))}
        </div>
        <Button variant="secondary" onClick={logout}>
          Cerrar sesión
        </Button>
      </nav>
    </header>
  );
}
