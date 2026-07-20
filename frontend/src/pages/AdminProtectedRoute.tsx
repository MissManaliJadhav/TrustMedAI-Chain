import React from 'react';
import { useAppSelector } from '../store';
import { Navigate } from 'react-router-dom';

interface AdminProtectedRouteProps {
  element: React.ReactNode;
}

export const AdminProtectedRoute: React.FC<AdminProtectedRouteProps> = ({ element }) => {
  const token = useAppSelector((state) => state.auth.accessToken);
  const role = useAppSelector((state) => state.auth.role);

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  // Only SUPER_ADMIN and HOSPITAL_ADMIN can access admin dashboard
  if (role && ['SUPER_ADMIN', 'HOSPITAL_ADMIN'].includes(role)) {
    return <>{element}</>;
  }

  // Redirect non-admin roles
  return <Navigate to="/dashboard" replace />;
};

export const AdminDashboardWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const handleLogout = () => {
    localStorage.removeItem('trustmedai_access');
    localStorage.removeItem('trustmedai_refresh');
    window.location.href = '/login';
  };

  return (
    <div>
      <button className="sr-only" onClick={handleLogout} type="button">Logout</button>
      {children}
    </div>
  );
};
