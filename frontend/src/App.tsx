import { lazy, Suspense } from 'react';
import { Navigate, RouterProvider, createBrowserRouter } from 'react-router-dom';
import { useAppSelector } from './store';

const LandingPage = lazy(() => import('./pages/LandingPage'));
const LoginPage = lazy(() => import('./pages/LoginPage'));
const SignupPage = lazy(() => import('./pages/SignupPage'));
const ForgotPasswordPage = lazy(() => import('./pages/ForgotPasswordPage'));
const VerifyEmailPage = lazy(() => import('./pages/VerifyEmailPage'));
const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const DiagnosisCatalogPage = lazy(() => import('./pages/DiagnosisCatalogPage'));
const DiseaseDiagnosisPage = lazy(() => import('./pages/DiseaseDiagnosisPage'));
const RoleBasedDashboard = lazy(() => import('./pages/RoleBasedDashboard'));
const ChatPage = lazy(() => import('./pages/ChatPage'));

function ProtectedRoute({ element }: { element: React.ReactNode }) {
  const token = useAppSelector((state) => state.auth.accessToken);
  return token ? element : <Navigate to="/login" replace />;
}

function RoleProtectedRoute({ element, allowedRoles }: { element: React.ReactNode; allowedRoles: string[] }) {
  const token = useAppSelector((state) => state.auth.accessToken);
  const role = useAppSelector((state) => state.auth.role);

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  if (role && allowedRoles.includes(role)) {
    return element;
  }

  // Redirect non-matching roles to dashboard
  return <Navigate to="/dashboard" replace />;
}

const router = createBrowserRouter([
  { path: '/', element: <LandingPage /> },
  { path: '/login', element: <LoginPage /> },
  { path: '/signup', element: <SignupPage /> },
  { path: '/forgot-password', element: <ForgotPasswordPage /> },
  { path: '/verify-email', element: <VerifyEmailPage /> },
  { path: '/dashboard', element: <ProtectedRoute element={<DashboardPage />} /> },
  { path: '/diagnosis', element: <ProtectedRoute element={<DiagnosisCatalogPage />} /> },
  { path: '/diagnosis/:diseaseKey', element: <ProtectedRoute element={<DiseaseDiagnosisPage />} /> },
  {
    path: '/role-dashboard',
    element: (
      <RoleProtectedRoute
        element={<RoleBasedDashboard />}
        allowedRoles={['DOCTOR', 'PATIENT', 'SUPER_ADMIN', 'HOSPITAL_ADMIN']}
      />
    ),
  },
  { path: '/chat', element: <ProtectedRoute element={<ChatPage />} /> },
]);

export default function App() {
  return (
    <Suspense fallback={<div className="grid min-h-screen place-items-center text-slate-600">Loading TrustMedAI…</div>}>
      <RouterProvider router={router} />
    </Suspense>
  );
}
