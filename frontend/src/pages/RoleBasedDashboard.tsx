import { Navigate } from 'react-router-dom';
import { useAppSelector } from '../store';
import DoctorDashboardPage from './DoctorDashboardPage';
import PatientDashboardPage from './PatientDashboardPage';

export default function RoleBasedDashboard() {
  const role = useAppSelector((state) => state.auth.role);

  if (role === 'DOCTOR') {
    return <DoctorDashboardPage />;
  }
  if (role === 'PATIENT') {
    return <PatientDashboardPage />;
  }
  if (role === 'SUPER_ADMIN' || role === 'HOSPITAL_ADMIN') {
    return <Navigate to="/admin/dashboard" replace />;
  }

  return <Navigate to="/login" replace />;
}
