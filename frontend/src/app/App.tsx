import { Route, Routes } from 'react-router-dom';
import { AuthProvider } from '@/context/AuthContext';
import { UserProvider } from '@/context/UserContext';
import { PrivateRoute } from '@/routes/PrivateRoute';
import { PublicRoute } from '@/routes/PublicRoute';
import { LoginPage } from '@/pages/Login/LoginPage';
import { HomePage } from '@/pages/Home/HomePage';
import { DocumentosPage } from '@/pages/Documentos/DocumentosPage';
import { ConsultasPage } from '@/pages/Consultas/ConsultasPage';

export function App() {
  return (
    <AuthProvider>
      <UserProvider>
        <Routes>
          <Route
            path="/login"
            element={
              <PublicRoute>
                <LoginPage />
              </PublicRoute>
            }
          />
          <Route
            path="/"
            element={
              <PrivateRoute>
                <HomePage />
              </PrivateRoute>
            }
          />
          <Route
            path="/documentos"
            element={
              <PrivateRoute permissionCode="DOCUMENTOS_VER">
                <DocumentosPage />
              </PrivateRoute>
            }
          />
          <Route
            path="/consultas"
            element={
              <PrivateRoute permissionCode="CONSULTAS_REALIZAR">
                <ConsultasPage />
              </PrivateRoute>
            }
          />
        </Routes>
      </UserProvider>
    </AuthProvider>
  );
}
