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

// Admin Components - Lazy load with named exports
const AdminLayout = lazy(() => import('./pages/AdminLayout').then(m => ({ default: m.AdminLayout })));
const AdminDashboard = lazy(() => import('./pages/AdminDashboard').then(m => ({ default: m.AdminDashboard })));
const AdminUsers = lazy(() => import('./pages/AdminUsers').then(m => ({ default: m.AdminUsers })));
const AdminAnalytics = lazy(() => import('./pages/AdminAnalytics').then(m => ({ default: m.AdminAnalytics })));
const AdminRecords = lazy(() => import('./pages/AdminRecords').then(m => ({ default: m.AdminRecords })));
const AdminAuditLogs = lazy(() => import('./pages/AdminAuditLogs').then(m => ({ default: m.AdminAuditLogs })));
const AdminSettings = lazy(() => import('./pages/AdminSettings').then(m => ({ default: m.AdminSettings })));
const AdminHospitals = lazy(() => import('./pages/AdminHospitals').then(m => ({ default: m.AdminHospitals })));
const AdminFederated = lazy(() => import('./pages/AdminFederated').then(m => ({ default: m.AdminFederated })));

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

  if (role === 'SUPER_ADMIN' || role === 'HOSPITAL_ADMIN') {
    return <Navigate to="/admin/dashboard" replace />;
  }

  // Redirect non-matching clinical roles to dashboard
  return <Navigate to="/dashboard" replace />;
}

const router = createBrowserRouter([
  { path: '/', element: <LandingPage /> },
  { path: '/login', element: <LoginPage /> },
  { path: '/signup', element: <SignupPage /> },
  { path: '/forgot-password', element: <ForgotPasswordPage /> },
  { path: '/verify-email', element: <VerifyEmailPage /> },
  { path: '/dashboard', element: <ProtectedRoute element={<DashboardPage />} /> },
  {
    path: '/diagnosis',
    element: (
      <RoleProtectedRoute
        element={<DiagnosisCatalogPage />}
        allowedRoles={['DOCTOR', 'PATIENT']}
      />
    ),
  },
  {
    path: '/diagnosis/:diseaseKey',
    element: (
      <RoleProtectedRoute
        element={<DiseaseDiagnosisPage />}
        allowedRoles={['DOCTOR', 'PATIENT']}
      />
    ),
  },
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
  // Admin Routes
  {
    path: '/admin',
    element: (
      <RoleProtectedRoute
        element={<AdminLayout />}
        allowedRoles={['SUPER_ADMIN', 'HOSPITAL_ADMIN']}
      />
    ),
    children: [
      {
        path: 'dashboard',
        element: (
          <RoleProtectedRoute
            element={<AdminDashboard />}
            allowedRoles={['SUPER_ADMIN', 'HOSPITAL_ADMIN']}
          />
        ),
      },
      {
        path: 'users',
        element: (
          <RoleProtectedRoute
            element={<AdminUsers />}
            allowedRoles={['SUPER_ADMIN', 'HOSPITAL_ADMIN']}
          />
        ),
      },
      {
        path: 'analytics',
        element: (
          <RoleProtectedRoute
            element={<AdminAnalytics />}
            allowedRoles={['SUPER_ADMIN', 'HOSPITAL_ADMIN']}
          />
        ),
      },
      {
        path: 'records',
        element: (
          <RoleProtectedRoute
            element={<AdminRecords />}
            allowedRoles={['SUPER_ADMIN', 'HOSPITAL_ADMIN']}
          />
        ),
      },
      {
        path: 'audit-logs',
        element: (
          <RoleProtectedRoute
            element={<AdminAuditLogs />}
            allowedRoles={['SUPER_ADMIN', 'HOSPITAL_ADMIN']}
          />
        ),
      },
      {
        path: 'hospitals',
        element: (
          <RoleProtectedRoute
            element={<AdminHospitals />}
            allowedRoles={['SUPER_ADMIN', 'HOSPITAL_ADMIN']}
          />
        ),
      },
      {
        path: 'federated',
        element: (
          <RoleProtectedRoute
            element={<AdminFederated />}
            allowedRoles={['SUPER_ADMIN', 'HOSPITAL_ADMIN']}
          />
        ),
      },
      {
        path: 'settings',
        element: (
          <RoleProtectedRoute
            element={<AdminSettings />}
            allowedRoles={['SUPER_ADMIN', 'HOSPITAL_ADMIN']}
          />
        ),
      },
      {
        index: true,
        element: <Navigate to="dashboard" replace />,
      },
    ],
  },
]);

export default function App() {
  return (
    <Suspense fallback={<div className="grid min-h-screen place-items-center text-slate-600">Loading TrustMedAI…</div>}>
      <RouterProvider router={router} />
    </Suspense>
  );
}
