import React, { useEffect, useMemo, useState } from 'react';
import {
  Activity,
  Bell,
  Building2,
  Database,
  FileBarChart,
  HeartPulse,
  Hospital,
  Network,
  Settings,
  ShieldCheck,
  Stethoscope,
  UserCog,
  Users,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { API_BASE_URL } from '../config';

interface AnalyticsData {
  users: {
    total: number;
    active: number;
    verified: number;
    new_in_period: number;
    role_distribution: Record<string, number>;
  };
  diagnoses: {
    total: number;
    in_period: number;
    average_trust_score: number;
  };
  hospitals: {
    total: number;
    verified: number;
  };
  patients?: {
    total: number;
  };
  doctors?: {
    total: number;
  };
  blockchain?: {
    transactions: number;
  };
  ai?: {
    accuracy: number;
  };
  sessions?: {
    active: number;
  };
  period_days: number;
}

interface StatCardProps {
  title: string;
  value: number | string;
  icon: React.ReactNode;
  accent: string;
  detail: string;
}

const StatCard: React.FC<StatCardProps> = ({ title, value, icon, accent, detail }) => (
  <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
    <div className="flex items-start justify-between gap-4">
      <div>
        <p className="text-sm font-semibold text-gray-500">{title}</p>
        <p className="mt-2 text-3xl font-bold text-gray-950">{value}</p>
        <p className="mt-2 text-xs font-medium text-gray-500">{detail}</p>
      </div>
      <div className={`grid h-12 w-12 shrink-0 place-items-center rounded-lg ${accent}`}>{icon}</div>
    </div>
  </div>
);

const AdminDashboard: React.FC = () => {
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const token = localStorage.getItem('trustmedai_access');
        const response = await fetch(`${API_BASE_URL}/admin/analytics/overview?days=30`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (!response.ok) throw new Error('Failed to fetch analytics');
        setAnalytics(await response.json());
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchAnalytics();
  }, []);

  const roleRows = useMemo(() => Object.entries(analytics?.users.role_distribution ?? {}), [analytics]);

  if (loading) {
    return <div className="py-8 text-center">Loading...</div>;
  }

  if (error) {
    return <div className="py-8 text-center text-red-600">Error: {error}</div>;
  }

  if (!analytics) {
    return <div className="py-8 text-center">No data available</div>;
  }

  const activeRate = analytics.users.total
    ? `${((analytics.users.active / analytics.users.total) * 100).toFixed(1)}%`
    : '0.0%';

  const dashboardCards = [
    {
      title: 'Users',
      value: analytics.users.total,
      icon: <Users className="h-6 w-6 text-white" />,
      accent: 'bg-blue-600',
      detail: `${analytics.users.new_in_period} new in ${analytics.period_days} days`,
    },
    {
      title: 'Patients',
      value: analytics.patients?.total ?? analytics.users.role_distribution.PATIENT ?? 0,
      icon: <HeartPulse className="h-6 w-6 text-white" />,
      accent: 'bg-rose-600',
      detail: 'Registered patient accounts',
    },
    {
      title: 'Doctors',
      value: analytics.doctors?.total ?? analytics.users.role_distribution.DOCTOR ?? 0,
      icon: <Stethoscope className="h-6 w-6 text-white" />,
      accent: 'bg-teal-600',
      detail: 'Clinical reviewer accounts',
    },
    {
      title: 'Hospitals',
      value: analytics.hospitals.total,
      icon: <Hospital className="h-6 w-6 text-white" />,
      accent: 'bg-indigo-600',
      detail: `${analytics.hospitals.verified} verified`,
    },
    {
      title: 'Predictions',
      value: analytics.diagnoses.total,
      icon: <Database className="h-6 w-6 text-white" />,
      accent: 'bg-violet-600',
      detail: `${analytics.diagnoses.in_period} recent predictions`,
    },
    {
      title: 'Blockchain Transactions',
      value: analytics.blockchain?.transactions ?? analytics.diagnoses.total,
      icon: <ShieldCheck className="h-6 w-6 text-white" />,
      accent: 'bg-slate-700',
      detail: 'Anchored diagnosis records',
    },
    {
      title: 'AI Accuracy',
      value: `${((analytics.ai?.accuracy ?? analytics.diagnoses.average_trust_score) * 100).toFixed(1)}%`,
      icon: <Activity className="h-6 w-6 text-white" />,
      accent: 'bg-emerald-600',
      detail: 'Average model fidelity',
    },
    {
      title: 'Active Sessions',
      value: analytics.sessions?.active ?? analytics.users.active,
      icon: <UserCog className="h-6 w-6 text-white" />,
      accent: 'bg-orange-600',
      detail: `${activeRate} active user rate`,
    },
  ];

  const modules = [
    { title: 'User Management', description: 'Search, verify, block, and edit platform users.', icon: <Users />, to: '/admin/users' },
    { title: 'Hospital Management', description: 'Review hospitals, verification status, and network coverage.', icon: <Building2 />, to: '/admin/hospitals' },
    { title: 'Federated Learning', description: 'Coordinate hospital training rounds without sharing raw patient data.', icon: <Network />, to: '/admin/federated' },
    { title: 'Role Management Reports', description: 'Track role distribution and operational growth reports.', icon: <FileBarChart />, to: '/admin/analytics' },
    { title: 'Notifications', description: 'Send system announcements and review communication health.', icon: <Bell />, to: '/admin/settings' },
    { title: 'System Settings', description: 'Inspect security, blockchain, API, and environment settings.', icon: <Settings />, to: '/admin/settings' },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-gray-950">Super Admin Dashboard</h2>
        <p className="mt-1 text-gray-600">Platform control center for users, hospitals, AI trust, and blockchain activity.</p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        {dashboardCards.map((card) => (
          <StatCard key={card.title} {...card} />
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[1fr_360px]">
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <h3 className="text-xl font-bold text-gray-950">Management Modules</h3>
          <div className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2">
            {modules.map((module) => (
              <Link
                key={module.title}
                to={module.to}
                className="rounded-lg border border-gray-200 p-4 transition hover:border-blue-300 hover:bg-blue-50"
              >
                <div className="flex items-start gap-3">
                  <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-gray-100 text-gray-700">
                    {module.icon}
                  </span>
                  <div>
                    <h4 className="font-bold text-gray-950">{module.title}</h4>
                    <p className="mt-1 text-sm leading-6 text-gray-600">{module.description}</p>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>

        <aside className="space-y-6">
          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
            <h3 className="font-bold text-gray-950">Role Management Reports</h3>
            <div className="mt-4 space-y-3">
              {roleRows.map(([role, count]) => (
                <div key={role} className="flex items-center justify-between rounded-lg bg-gray-50 px-3 py-2 text-sm">
                  <span className="font-medium text-gray-600">{role.replace('_', ' ')}</span>
                  <span className="font-bold text-gray-950">{count}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
            <h3 className="font-bold text-gray-950">Notifications</h3>
            <p className="mt-2 text-sm leading-6 text-gray-600">
              {analytics.users.verified} verified users can receive announcements from System Settings.
            </p>
            <Link className="mt-4 inline-flex rounded-lg bg-orange-600 px-4 py-2 text-sm font-bold text-white" to="/admin/settings">
              Open Notifications
            </Link>
          </div>
        </aside>
      </div>
    </div>
  );
};

export { AdminDashboard };
