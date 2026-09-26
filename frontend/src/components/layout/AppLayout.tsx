import type { ReactNode } from 'react';
import { NavBar } from '@/components/layout/NavBar';

interface AppLayoutProps {
  children: ReactNode;
}

/** Layout compartido por las páginas autenticadas: barra de navegación + contenido. */
export function AppLayout({ children }: AppLayoutProps) {
  return (
    <div className="min-h-screen bg-surface">
      <NavBar />
      <main className="px-6 py-8">{children}</main>
    </div>
  );
}
