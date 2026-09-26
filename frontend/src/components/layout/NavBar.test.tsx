import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { NavBar } from '@/components/layout/NavBar';
import { useAuth } from '@/context/AuthContext';
import { useUser } from '@/context/UserContext';

vi.mock('@/context/AuthContext', () => ({
  useAuth: vi.fn(),
}));

vi.mock('@/context/UserContext', () => ({
  useUser: vi.fn(),
}));

function configurarUsuario(permisos: string[]) {
  vi.mocked(useAuth).mockReturnValue({ isAuthenticated: true, login: vi.fn(), logout: vi.fn() });
  vi.mocked(useUser).mockReturnValue({
    usuario: { id: 1, username: 'ana', nombreCompleto: 'Ana', roles: [], permisos },
    isLoading: false,
    error: null,
    reload: vi.fn(),
    hasPermission: (codigo: string) => permisos.includes(codigo),
    hasRole: () => false,
  });
}

describe('NavBar', () => {
  it('no muestra las entradas cuyo permiso no tiene el usuario', () => {
    configurarUsuario([]);

    render(
      <MemoryRouter>
        <NavBar />
      </MemoryRouter>,
    );

    expect(screen.getByRole('link', { name: 'Inicio' })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Documentos' })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Consultas' })).not.toBeInTheDocument();
  });

  it('muestra Documentos cuando el usuario tiene DOCUMENTOS_VER, pero no Consultas', () => {
    configurarUsuario(['DOCUMENTOS_VER']);

    render(
      <MemoryRouter>
        <NavBar />
      </MemoryRouter>,
    );

    expect(screen.getByRole('link', { name: 'Documentos' })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Consultas' })).not.toBeInTheDocument();
  });

  it('muestra todas las entradas cuando el usuario tiene ambos permisos', () => {
    configurarUsuario(['DOCUMENTOS_VER', 'CONSULTAS_REALIZAR']);

    render(
      <MemoryRouter>
        <NavBar />
      </MemoryRouter>,
    );

    expect(screen.getByRole('link', { name: 'Documentos' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Consultas' })).toBeInTheDocument();
  });
});
