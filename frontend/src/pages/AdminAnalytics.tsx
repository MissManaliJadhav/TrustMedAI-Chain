import React, { useEffect, useState } from 'react';
import { API_BASE_URL } from '../config';

interface DailyStats {
  date: string;
  new_users: number;
  new_diagnoses: number;
}

interface AnalyticsResponse {
  statistics: DailyStats[];
}

interface GrowthMonth {
  month: string;
  new_users: number;
}

export const AdminAnalytics: React.FC = () => {
  const [dailyStats, setDailyStats] = useState<DailyStats[]>([]);
  const [monthlyGrowth, setMonthlyGrowth] = useState<GrowthMonth[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchAnalyticsData();
  }, []);

  const fetchAnalyticsData = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('trustmedai_access');

      // Fetch daily stats
      const dailyResponse = await fetch(`${API_BASE_URL}/admin/analytics/daily-stats?days=30`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!dailyResponse.ok) throw new Error('Failed to fetch daily stats');
      const dailyData: AnalyticsResponse = await dailyResponse.json();
      setDailyStats(dailyData.statistics);

      // Fetch monthly growth
      const monthlyResponse = await fetch(`${API_BASE_URL}/admin/analytics/user-growth`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!monthlyResponse.ok) throw new Error('Failed to fetch monthly growth');
      const monthlyData = await monthlyResponse.json();
      setMonthlyGrowth(monthlyData.monthly_growth);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="text-center py-8">Loading...</div>;
  }

  if (error) {
    return <div className="text-center py-8 text-red-600">Error: {error}</div>;
  }

  const maxNewUsers = Math.max(...dailyStats.map((s) => s.new_users), 1);
  const maxNewDiagnoses = Math.max(...dailyStats.map((s) => s.new_diagnoses), 1);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Analytics</h2>
        <p className="text-gray-600 mt-1">System metrics and trends</p>
      </div>

      {/* Daily Stats Chart */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-xl font-semibold text-gray-900 mb-6">Daily Activity (Last 30 Days)</h3>

        <div className="space-y-8">
          {/* New Users Chart */}
          <div>
            <h4 className="text-sm font-semibold text-gray-700 mb-3">New Users</h4>
            <div className="flex items-end gap-1 h-32">
              {dailyStats.map((stat, idx) => (
                <div
                  key={idx}
                  className="flex-1 bg-blue-500 rounded-t hover:bg-blue-600 transition-colors"
                  style={{
                    height: `${(stat.new_users / maxNewUsers) * 100}%`,
                  }}
                  title={`${stat.date}: ${stat.new_users} users`}
                />
              ))}
            </div>
            <div className="flex justify-between text-xs text-gray-500 mt-2">
              <span>{dailyStats[0]?.date}</span>
              <span>{dailyStats[dailyStats.length - 1]?.date}</span>
            </div>
          </div>

          {/* New Diagnoses Chart */}
          <div>
            <h4 className="text-sm font-semibold text-gray-700 mb-3">New Diagnoses</h4>
            <div className="flex items-end gap-1 h-32">
              {dailyStats.map((stat, idx) => (
                <div
                  key={idx}
                  className="flex-1 bg-purple-500 rounded-t hover:bg-purple-600 transition-colors"
                  style={{
                    height: `${(stat.new_diagnoses / maxNewDiagnoses) * 100}%`,
                  }}
                  title={`${stat.date}: ${stat.new_diagnoses} diagnoses`}
                />
              ))}
            </div>
            <div className="flex justify-between text-xs text-gray-500 mt-2">
              <span>{dailyStats[0]?.date}</span>
              <span>{dailyStats[dailyStats.length - 1]?.date}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Monthly Growth Chart */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-xl font-semibold text-gray-900 mb-6">User Growth (12 Months)</h3>

        <div className="space-y-4">
          {monthlyGrowth.map((month, idx) => {
            const maxGrowth = Math.max(...monthlyGrowth.map((m) => m.new_users), 1);
            const percentage = (month.new_users / maxGrowth) * 100;

            return (
              <div key={idx} className="flex items-center gap-4">
                <span className="w-16 text-sm font-medium text-gray-600">{month.month}</span>
                <div className="flex-1 bg-gray-200 rounded-full h-6 overflow-hidden">
                  <div
                    className="bg-green-500 h-full rounded-full transition-all"
                    style={{ width: `${percentage}%` }}
                  />
                </div>
                <span className="w-16 text-right font-semibold text-gray-900">{month.new_users}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Statistics Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h4 className="text-sm font-semibold text-gray-600 mb-2">Total New Users (30 days)</h4>
          <p className="text-3xl font-bold text-gray-900">{dailyStats.reduce((sum, s) => sum + s.new_users, 0)}</p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h4 className="text-sm font-semibold text-gray-600 mb-2">Total New Diagnoses (30 days)</h4>
          <p className="text-3xl font-bold text-gray-900">{dailyStats.reduce((sum, s) => sum + s.new_diagnoses, 0)}</p>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h4 className="text-sm font-semibold text-gray-600 mb-2">Avg Daily New Users</h4>
          <p className="text-3xl font-bold text-gray-900">
            {(dailyStats.reduce((sum, s) => sum + s.new_users, 0) / dailyStats.length).toFixed(1)}
          </p>
        </div>
      </div>
    </div>
  );
};
