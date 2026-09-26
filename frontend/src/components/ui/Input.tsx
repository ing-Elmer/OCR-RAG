import { useId, type InputHTMLAttributes } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  /** Mensaje de error del backend para este campo (via `toFormErrors`). */
  error?: string;
}

/** Input con label asociado y mensaje de error accesible. */
export function Input({ label, error, id, className = '', ...props }: InputProps) {
  const idGenerado = useId();
  const inputId = id ?? idGenerado;
  const errorId = `${inputId}-error`;

  return (
    <div className="mb-4">
      <label htmlFor={inputId} className="mb-1 block text-sm font-medium text-text">
        {label}
      </label>
      <input
        id={inputId}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? errorId : undefined}
        className={`w-full rounded-md border px-3 py-2 text-sm text-text focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary ${
          error ? 'border-danger' : 'border-border'
        } ${className}`.trim()}
        {...props}
      />
      {error && (
        <p id={errorId} role="alert" className="mt-1 text-sm text-danger">
          {error}
        </p>
      )}
    </div>
  );
}
