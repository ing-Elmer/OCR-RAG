import { Button } from '@/components/ui/Button';

interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

/** Estado de error compartido, con reintento opcional. */
export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div
      role="alert"
      className="flex flex-col items-center gap-3 rounded-md bg-danger-surface px-4 py-6 text-center text-sm text-danger"
    >
      <p>{message}</p>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry}>
          Reintentar
        </Button>
      )}
    </div>
  );
}
