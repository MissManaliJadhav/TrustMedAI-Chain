import { Navigate } from 'react-router-dom';
import { useAppSelector } from '../store';
import AdminDashboardPage from './AdminDashboardPage';
import DashboardPage from './DashboardPage';
import PatientDashboardPage from './PatientDashboardPage';

export default function RoleBasedDashboard() {
  const role = useAppSelector((state) => state.auth.role);

  if (role === 'DOCTOR') {
    return <DashboardPage />;
  }
  if (role === 'PATIENT') {
    return <PatientDashboardPage />;
  }
  if (role === 'SUPER_ADMIN' || role === 'HOSPITAL_ADMIN') {
    return <AdminDashboardPage />;
  }

  return <Navigate to="/login" replace />;
}
