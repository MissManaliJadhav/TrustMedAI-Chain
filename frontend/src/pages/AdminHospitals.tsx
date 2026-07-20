import React, { useEffect, useState } from 'react';
import { Check, X, Search } from 'lucide-react';
import { API_BASE_URL } from '../config';

interface Hospital {
  id: string;
  name: string;
  region: string;
  reputation_score: number;
  verified: boolean;
  user_count: number;
  created_at: string;
}

interface HospitalsResponse {
  total: number;
  hospitals: Hospital[];
}

export const AdminHospitals: React.FC = () => {
  const [hospitals, setHospitals] = useState<Hospital[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [verifiedFilter, setVerifiedFilter] = useState<string>('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalHospitals, setTotalHospitals] = useState(0);

  const PAGE_SIZE = 10;

  useEffect(() => {
    fetchHospitals();
  }, [currentPage, verifiedFilter]);

  const fetchHospitals = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('trustmedai_access');
      const params = new URLSearchParams({
        skip: String((currentPage - 1) * PAGE_SIZE),
        limit: String(PAGE_SIZE),
      });

      if (verifiedFilter !== '') {
        params.append('verified', verifiedFilter === 'true' ? 'true' : 'false');
      }

      const response = await fetch(`${API_BASE_URL}/admin/hospitals?${params}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error('Failed to fetch hospitals');
      const data: HospitalsResponse = await response.json();
      setHospitals(data.hospitals);
      setTotalHospitals(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyHospital = async (hospitalId: string) => {
    try {
      const token = localStorage.getItem('trustmedai_access');
      const response = await fetch(`${API_BASE_URL}/admin/hospitals/${hospitalId}/verify`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error('Failed to verify hospital');
      fetchHospitals();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to verify hospital');
    }
  };

  const totalPages = Math.ceil(totalHospitals / PAGE_SIZE);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Hospital Management</h2>
        <p className="text-gray-600 mt-1">Manage partner hospitals and verify credentials</p>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4">
        <select
          value={verifiedFilter}
          onChange={(e) => {
            setVerifiedFilter(e.target.value);
            setCurrentPage(1);
          }}
          className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">All Hospitals</option>
          <option value="true">Verified</option>
          <option value="false">Pending Verification</option>
        </select>
      </div>

      {/* Error Message */}
      {error && <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">{error}</div>}

      {/* Hospitals Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {loading ? (
          <div className="col-span-full text-center py-8 text-gray-500">Loading...</div>
        ) : hospitals.length === 0 ? (
          <div className="col-span-full text-center py-8 text-gray-500">No hospitals found</div>
        ) : (
          hospitals.map((hospital) => (
            <div key={hospital.id} className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow overflow-hidden">
              <div className="p-6">
                {/* Header */}
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h3 className="text-lg font-bold text-gray-900">{hospital.name}</h3>
                    <p className="text-sm text-gray-600">{hospital.region}</p>
                  </div>
                  {hospital.verified ? (
                    <div className="flex items-center gap-1 px-3 py-1 rounded-full bg-green-100 text-green-800 text-xs font-semibold">
                      <Check size={14} />
                      Verified
                    </div>
                  ) : (
                    <div className="flex items-center gap-1 px-3 py-1 rounded-full bg-yellow-100 text-yellow-800 text-xs font-semibold">
                      <X size={14} />
                      Pending
                    </div>
                  )}
                </div>

                {/* Stats */}
                <div className="space-y-3 mb-4 pb-4 border-b border-gray-200">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Users</span>
                    <span className="font-bold">{hospital.user_count}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Reputation Score</span>
                    <span className="font-bold">{(hospital.reputation_score * 100).toFixed(1)}%</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Added</span>
                    <span className="font-mono text-xs">{new Date(hospital.created_at).toLocaleDateString()}</span>
                  </div>
                </div>

                {/* Reputation Bar */}
                <div className="mb-4">
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-gray-600">Reputation</span>
                    <span className="font-semibold">{(hospital.reputation_score * 100).toFixed(0)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full ${
                        hospital.reputation_score > 0.8
                          ? 'bg-green-500'
                          : hospital.reputation_score > 0.6
                          ? 'bg-yellow-500'
                          : 'bg-red-500'
                      }`}
                      style={{ width: `${hospital.reputation_score * 100}%` }}
                    />
                  </div>
                </div>

                {/* Action Button */}
                {!hospital.verified && (
                  <button
                    onClick={() => handleVerifyHospital(hospital.id)}
                    className="w-full bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
                  >
                    Verify Hospital
                  </button>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-2">
          <button
            onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
            disabled={currentPage === 1}
            className="px-4 py-2 border border-gray-300 rounded-lg disabled:opacity-50"
          >
            Previous
          </button>
          <span className="px-4 py-2">
            Page {currentPage} of {totalPages}
          </span>
          <button
            onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
            disabled={currentPage === totalPages}
            className="px-4 py-2 border border-gray-300 rounded-lg disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}

      {/* Summary */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-900">
          Total hospitals: {totalHospitals} | Verified: {hospitals.filter((h) => h.verified).length} | Pending: {hospitals.filter((h) => !h.verified).length}
        </p>
      </div>
    </div>
  );
};
