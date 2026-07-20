import React, { useEffect, useState } from 'react';
import { Save, Lock, Bell, Shield, Server } from 'lucide-react';
import { API_BASE_URL } from '../config';

interface SystemSettings {
  project_name: string;
  environment: string;
  api_port: number;
  jwt_algorithm: string;
  access_token_expire_minutes: number;
  refresh_token_expire_days: number;
  blockchain: {
    ethereum_enabled: boolean;
    fabric_enabled: boolean;
  };
}

interface MFAStatus {
  total_users: number;
  admin_users: number;
  mfa_enabled: number;
  mfa_adoption_rate: string;
}

export const AdminSettings: React.FC = () => {
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [mfaStatus, setMFAStatus] = useState<MFAStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [announcement, setAnnouncement] = useState('');
  const [announcementTitle, setAnnouncementTitle] = useState('');

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('trustmedai_access');

      // Fetch system settings
      const settingsResponse = await fetch(`${API_BASE_URL}/admin/settings/system`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!settingsResponse.ok) throw new Error('Failed to fetch settings');
      const settingsData: SystemSettings = await settingsResponse.json();
      setSettings(settingsData);

      // Fetch MFA status
      const mfaResponse = await fetch(`${API_BASE_URL}/admin/settings/mfa-status`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!mfaResponse.ok) throw new Error('Failed to fetch MFA status');
      const mfaData: MFAStatus = await mfaResponse.json();
      setMFAStatus(mfaData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const handleSendAnnouncement = async () => {
    if (!announcementTitle.trim() || !announcement.trim()) {
      setError('Please fill in both title and message');
      return;
    }

    try {
      const token = localStorage.getItem('trustmedai_access');
      const response = await fetch(`${API_BASE_URL}/admin/settings/send-announcement`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: announcementTitle,
          message: announcement,
        }),
      });

      if (!response.ok) throw new Error('Failed to send announcement');

      setSuccess('Announcement sent successfully');
      setAnnouncementTitle('');
      setAnnouncement('');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send announcement');
    }
  };

  if (loading) {
    return <div className="text-center py-8">Loading...</div>;
  }

  if (!settings || !mfaStatus) {
    return <div className="text-center py-8 text-red-600">Failed to load settings</div>;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Settings & Configuration</h2>
        <p className="text-gray-600 mt-1">Manage system settings and security</p>
      </div>

      {/* Error/Success Messages */}
      {error && <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">{error}</div>}
      {success && <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded">{success}</div>}

      {/* System Settings */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center gap-3 mb-6">
          <Server className="text-blue-600" size={24} />
          <h3 className="text-xl font-semibold text-gray-900">System Settings</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Project Name</label>
            <input
              type="text"
              value={settings.project_name}
              disabled
              className="w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-600"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Environment</label>
            <input
              type="text"
              value={settings.environment}
              disabled
              className="w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-600"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">API Port</label>
            <input
              type="number"
              value={settings.api_port}
              disabled
              className="w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-600"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">JWT Algorithm</label>
            <input
              type="text"
              value={settings.jwt_algorithm}
              disabled
              className="w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-600"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Access Token Expiry (minutes)</label>
            <input
              type="number"
              value={settings.access_token_expire_minutes}
              disabled
              className="w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-600"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Refresh Token Expiry (days)</label>
            <input
              type="number"
              value={settings.refresh_token_expire_days}
              disabled
              className="w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-600"
            />
          </div>
        </div>

        <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-sm text-blue-900">
            System settings are read-only and managed through environment variables. Update .env file to change these values.
          </p>
        </div>
      </div>

      {/* Blockchain Settings */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center gap-3 mb-6">
          <Shield className="text-purple-600" size={24} />
          <h3 className="text-xl font-semibold text-gray-900">Blockchain Configuration</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
            <div>
              <p className="font-medium text-gray-900">Ethereum</p>
              <p className="text-sm text-gray-600">Distributed ledger support</p>
            </div>
            <div className={`px-3 py-1 rounded-full text-sm font-semibold ${
              settings.blockchain.ethereum_enabled
                ? 'bg-green-100 text-green-800'
                : 'bg-gray-100 text-gray-800'
            }`}>
              {settings.blockchain.ethereum_enabled ? 'Enabled' : 'Disabled'}
            </div>
          </div>

          <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
            <div>
              <p className="font-medium text-gray-900">Hyperledger Fabric</p>
              <p className="text-sm text-gray-600">Enterprise blockchain</p>
            </div>
            <div className={`px-3 py-1 rounded-full text-sm font-semibold ${
              settings.blockchain.fabric_enabled
                ? 'bg-green-100 text-green-800'
                : 'bg-gray-100 text-gray-800'
            }`}>
              {settings.blockchain.fabric_enabled ? 'Enabled' : 'Disabled'}
            </div>
          </div>
        </div>
      </div>

      {/* Security Settings */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center gap-3 mb-6">
          <Lock className="text-red-600" size={24} />
          <h3 className="text-xl font-semibold text-gray-900">Security & MFA</h3>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-6">
            <p className="text-gray-600 text-sm mb-2">Total Users</p>
            <p className="text-3xl font-bold text-blue-900">{mfaStatus.total_users}</p>
          </div>

          <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg p-6">
            <p className="text-gray-600 text-sm mb-2">Admin Users</p>
            <p className="text-3xl font-bold text-purple-900">{mfaStatus.admin_users}</p>
          </div>

          <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg p-6">
            <p className="text-gray-600 text-sm mb-2">MFA Adoption Rate</p>
            <p className="text-3xl font-bold text-green-900">{mfaStatus.mfa_adoption_rate}</p>
          </div>
        </div>

        <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <p className="text-sm text-yellow-900">
            Two-factor authentication is recommended for all admin accounts. Current MFA adoption: {mfaStatus.mfa_enabled} of {mfaStatus.total_users} users.
          </p>
        </div>
      </div>

      {/* Notifications */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center gap-3 mb-6">
          <Bell className="text-orange-600" size={24} />
          <h3 className="text-xl font-semibold text-gray-900">System Announcements</h3>
        </div>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Announcement Title</label>
            <input
              type="text"
              value={announcementTitle}
              onChange={(e) => setAnnouncementTitle(e.target.value)}
              placeholder="e.g., System Maintenance"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Message</label>
            <textarea
              value={announcement}
              onChange={(e) => setAnnouncement(e.target.value)}
              placeholder="Enter your announcement message..."
              rows={4}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <button
            onClick={handleSendAnnouncement}
            className="flex items-center gap-2 bg-orange-600 text-white px-6 py-2 rounded-lg hover:bg-orange-700 transition-colors"
          >
            <Bell size={20} />
            Send Announcement
          </button>
        </div>
      </div>

      {/* Additional Settings */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-xl font-semibold text-gray-900 mb-6">Additional Settings</h3>

        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50">
            <div>
              <p className="font-medium text-gray-900">API Documentation</p>
              <p className="text-sm text-gray-600">Access OpenAPI/Swagger documentation</p>
            </div>
            <a
              href={`${API_BASE_URL}/docs`}
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2 text-blue-600 hover:underline font-medium"
            >
              Open
            </a>
          </div>

          <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50">
            <div>
              <p className="font-medium text-gray-900">Database Backup</p>
              <p className="text-sm text-gray-600">Create and download system backups</p>
            </div>
            <button className="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300">
              Manage
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
