interface LoadingStateProps {
  label?: string;
}

/** Estado de carga compartido: toda vista con datos async lo usa mientras espera la respuesta. */
export function LoadingState({ label = 'Cargando...' }: LoadingStateProps) {
  return (
    <div role="status" aria-live="polite" className="flex items-center gap-3 py-6 text-sm text-muted">
      <span
        aria-hidden="true"
        className="h-4 w-4 animate-spin rounded-full border-2 border-border border-t-primary"
      />
      <span>{label}</span>
    </div>
  );
}
