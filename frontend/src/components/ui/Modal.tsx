import { useEffect, useRef, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

interface ModalProps {
  isOpen: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
}

const SELECTOR_FOCUSABLES =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

/** Modal accesible: cierra con `Esc`, atrapa el foco y lo devuelve al cerrarse. */
export function Modal({ isOpen, title, onClose, children }: ModalProps) {
  const contenedorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const elementoPrevio = document.activeElement as HTMLElement | null;
    const primerFocuable = contenedorRef.current?.querySelector<HTMLElement>(SELECTOR_FOCUSABLES);
    primerFocuable?.focus();

    function alPresionarTecla(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        onClose();
        return;
      }

      if (event.key !== 'Tab' || !contenedorRef.current) {
        return;
      }

      const focuables = Array.from(contenedorRef.current.querySelectorAll<HTMLElement>(SELECTOR_FOCUSABLES));
      if (focuables.length === 0) {
        return;
      }

      const primero = focuables[0];
      const ultimo = focuables[focuables.length - 1];

      if (event.shiftKey && document.activeElement === primero) {
        event.preventDefault();
        ultimo.focus();
      } else if (!event.shiftKey && document.activeElement === ultimo) {
        event.preventDefault();
        primero.focus();
      }
    }

    document.addEventListener('keydown', alPresionarTecla);
    return () => {
      document.removeEventListener('keydown', alPresionarTecla);
      elementoPrevio?.focus();
    };
  }, [isOpen, onClose]);

  if (!isOpen) {
    return null;
  }

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div
        ref={contenedorRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-titulo"
        className="w-full max-w-md rounded-lg bg-white p-6 shadow-lg"
      >
        <h2 id="modal-titulo" className="mb-4 text-lg font-semibold text-text">
          {title}
        </h2>
        {children}
      </div>
    </div>,
    document.body,
  );
}
