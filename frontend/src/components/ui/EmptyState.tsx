import type { ReactNode } from 'react';

interface EmptyStateProps {
  message: string;
  action?: ReactNode;
}

/** Estado vacío compartido: se usa cuando una lista o dato no tiene contenido. */
export function EmptyState({ message, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-3 py-8 text-center text-sm text-muted">
      <p>{message}</p>
      {action}
    </div>
  );
}
