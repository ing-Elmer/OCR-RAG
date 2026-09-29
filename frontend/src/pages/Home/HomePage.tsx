import { useAuth } from '@/context/AuthContext';
import { useUser } from '@/context/UserContext';
import { useHealth } from '@/hooks/useHealth';
import { Button } from '@/components/ui/Button';
import { LoadingState } from '@/components/ui/LoadingState';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';

/** Página principal: perfil del usuario (`/api/me`) y estado del sistema (`/health`). */
export function HomePage() {
  const { logout } = useAuth();
  const { usuario, isLoading: cargandoUsuario, error: errorUsuario, reload: recargarUsuario } = useUser();
  const { data: salud, isLoading: cargandoSalud, error: errorSalud, reload: recargarSalud } = useHealth();

  return (
    <main className="min-h-screen bg-surface px-6 py-8">
      <header className="mb-8 flex items-center justify-between">
        <h1 className="text-xl font-semibold text-text">OCR-RAG</h1>
        <Button variant="secondary" onClick={logout}>
          Cerrar sesión
        </Button>
      </header>

      <section aria-labelledby="perfil-titulo" className="mb-8 rounded-lg border border-border bg-white p-6">
        <h2 id="perfil-titulo" className="mb-4 text-lg font-medium text-text">
          Tu perfil
        </h2>

        {cargandoUsuario && <LoadingState label="Cargando perfil..." />}
        {!cargandoUsuario && errorUsuario && <ErrorState message={errorUsuario} onRetry={recargarUsuario} />}
        {!cargandoUsuario && !errorUsuario && !usuario && (
          <EmptyState message="No hay datos de perfil para mostrar." />
        )}
        {!cargandoUsuario && !errorUsuario && usuario && (
          <dl className="grid grid-cols-1 gap-4 text-sm text-text sm:grid-cols-3">
            <div>
              <dt className="text-muted">Usuario</dt>
              <dd>{usuario.username}</dd>
            </div>
            <div>
              <dt className="text-muted">Nombre completo</dt>
              <dd>{usuario.nombreCompleto}</dd>
            </div>
            <div>
              <dt className="text-muted">Roles</dt>
              <dd>{usuario.roles.length > 0 ? usuario.roles.join(', ') : 'Sin roles asignados'}</dd>
            </div>
          </dl>
        )}
      </section>

      <section aria-labelledby="salud-titulo" className="rounded-lg border border-border bg-white p-6">
        <h2 id="salud-titulo" className="mb-4 text-lg font-medium text-text">
          Estado del sistema
        </h2>

        {cargandoSalud && <LoadingState label="Consultando estado del sistema..." />}
        {!cargandoSalud && errorSalud && <ErrorState message={errorSalud} onRetry={recargarSalud} />}
        {!cargandoSalud && !errorSalud && !salud && (
          <EmptyState message="No hay información de estado disponible." />
        )}
        {!cargandoSalud && !errorSalud && salud && (
          <dl className="grid grid-cols-1 gap-4 text-sm text-text sm:grid-cols-3">
            <div>
              <dt className="text-muted">Estado</dt>
              <dd>{salud.status}</dd>
            </div>
            <div>
              <dt className="text-muted">Base de datos</dt>
              <dd>{salud.database}</dd>
            </div>
            <div>
              <dt className="text-muted">Versión</dt>
              <dd>{salud.version}</dd>
            </div>
          </dl>
        )}
      </section>
    </main>
  );
}
