import type { ButtonHTMLAttributes } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary';
  /** Deshabilita el botón y muestra un texto de progreso mientras dura la acción. */
  isLoading?: boolean;
}

const ESTILOS_BASE =
  'inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors ' +
  'disabled:cursor-not-allowed disabled:opacity-60 ' +
  'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-primary';

const ESTILOS_VARIANTE = {
  primary: 'bg-primary text-white hover:bg-primary-dark',
  secondary: 'border border-border bg-white text-text hover:bg-surface',
};

/** Botón compartido con estado de carga incluido. */
export function Button({
  variant = 'primary',
  isLoading = false,
  disabled,
  children,
  className = '',
  ...props
}: ButtonProps) {
  return (
    <button
      className={`${ESTILOS_BASE} ${ESTILOS_VARIANTE[variant]} ${className}`.trim()}
      disabled={disabled ?? isLoading}
      aria-busy={isLoading}
      {...props}
    >
      {isLoading ? 'Procesando...' : children}
    </button>
  );
}
