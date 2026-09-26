import { Route, Routes } from 'react-router-dom';
import { AuthProvider } from '@/context/AuthContext';
import { UserProvider } from '@/context/UserContext';
import { PrivateRoute } from '@/routes/PrivateRoute';
import { PublicRoute } from '@/routes/PublicRoute';
import { LoginPage } from '@/pages/Login/LoginPage';
import { HomePage } from '@/pages/Home/HomePage';

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
        </Routes>
      </UserProvider>
    </AuthProvider>
  );
}
