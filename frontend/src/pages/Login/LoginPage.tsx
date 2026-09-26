import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { iniciarSesion } from '@/services/AuthService';
import { ApiError } from '@/services/ApiClient';
import { toFormErrors, type FormErrors } from '@/components/ui/helpers/toFormErrors';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';

const MENSAJE_ERROR_GENERICO = 'No se pudo iniciar sesión. Intentá de nuevo.';

/**
 * Página de login. Llama a `POST /api/auth/login`, que todavía es un path
 * reservado: el backend no lo implementa. Queda lista para cuando exista.
 */
export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [fieldErrors, setFieldErrors] = useState<FormErrors>({});
  const [mensajeError, setMensajeError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setFieldErrors({});
    setMensajeError(null);

    try {
      const tokens = await iniciarSesion({ username, password });
      login(tokens);
      navigate('/', { replace: true });
    } catch (error) {
      if (error instanceof ApiError) {
        setFieldErrors(toFormErrors(error));
        setMensajeError(error.message);
      } else {
        setMensajeError(MENSAJE_ERROR_GENERICO);
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-surface px-4">
      <form
        onSubmit={(event) => {
          void handleSubmit(event);
        }}
        noValidate
        className="w-full max-w-sm rounded-lg border border-border bg-white p-8 shadow-sm"
      >
        <h1 className="mb-6 text-2xl font-semibold text-text">Iniciar sesión</h1>

        {mensajeError && (
          <p role="alert" className="mb-4 rounded-md bg-danger-surface px-3 py-2 text-sm text-danger">
            {mensajeError}
          </p>
        )}

        <Input
          label="Usuario"
          id="username"
          name="username"
          autoComplete="username"
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          error={fieldErrors.username}
          disabled={isSubmitting}
          required
        />

        <Input
          label="Contraseña"
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          error={fieldErrors.password}
          disabled={isSubmitting}
          required
        />

        <Button type="submit" isLoading={isSubmitting} className="mt-2 w-full">
          Ingresar
        </Button>
      </form>
    </main>
  );
}
