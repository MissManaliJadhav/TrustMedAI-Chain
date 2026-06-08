import { Navigate, RouterProvider, createBrowserRouter } from 'react-router-dom';
import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import VerifyEmailPage from './pages/VerifyEmailPage';
import DashboardPage from './pages/DashboardPage';
import { useAppSelector } from './store';

function ProtectedRoute() {
  const token = useAppSelector((state) => state.auth.accessToken);
  return token ? <DashboardPage /> : <Navigate to="/login" replace />;
}

const router = createBrowserRouter([
  { path: '/', element: <LandingPage /> },
  { path: '/login', element: <LoginPage /> },
  { path: '/signup', element: <SignupPage /> },
  { path: '/forgot-password', element: <ForgotPasswordPage /> },
  { path: '/verify-email', element: <VerifyEmailPage /> },
  { path: '/dashboard', element: <ProtectedRoute /> },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
