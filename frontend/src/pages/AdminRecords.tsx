import React, { useEffect, useState } from 'react';
import { Trash2, Download, Search, Filter } from 'lucide-react';
import { API_BASE_URL } from '../config';

interface DiagnosisRecord {
  id: string;
  patient_name: string | null;
  disease_key: string;
  prediction: string;
  confidence: number;
  trust_score: number;
  blockchain_hash: string | null;
  created_at: string;
}

interface RecordsResponse {
  total: number;
  records: DiagnosisRecord[];
}

export const AdminRecords: React.FC = () => {
  const [records, setRecords] = useState<DiagnosisRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [diseaseFilter, setDiseaseFilter] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalRecords, setTotalRecords] = useState(0);

  const PAGE_SIZE = 15;
  const DISEASES = [
    'asthma',
    'brain_tumor',
    'diabetes',
    'eye',
    'heart',
    'liver',
    'parkinson',
    'pneumonia',
    'tuberculosis',
  ];

  useEffect(() => {
    fetchRecords();
  }, [currentPage, search, diseaseFilter]);

  const fetchRecords = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('trustmedai_access');
      const params = new URLSearchParams({
        skip: String((currentPage - 1) * PAGE_SIZE),
        limit: String(PAGE_SIZE),
      });

      if (search) params.append('search', search);
      if (diseaseFilter) params.append('disease_key', diseaseFilter);

      const response = await fetch(`${API_BASE_URL}/admin/data/records?${params}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error('Failed to fetch records');
      const data: RecordsResponse = await response.json();
      setRecords(data.records);
      setTotalRecords(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteRecord = async (recordId: string) => {
    if (!confirm('Are you sure you want to delete this record? This action cannot be undone.')) return;

    try {
      const token = localStorage.getItem('trustmedai_access');
      const response = await fetch(`${API_BASE_URL}/admin/data/records/${recordId}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error('Failed to delete record');
      fetchRecords();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete record');
    }
  };

  const handleExport = async () => {
    try {
      const token = localStorage.getItem('trustmedai_access');
      const response = await fetch(`${API_BASE_URL}/admin/data/export?record_type=records&format=csv`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) throw new Error('Failed to export');

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `diagnosis-records-${new Date().toISOString()}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export');
    }
  };

  const totalPages = Math.ceil(totalRecords / PAGE_SIZE);

  const getConfidenceColor = (confidence: number) => {
    if (confidence > 0.8) return 'text-green-600 bg-green-50';
    if (confidence > 0.6) return 'text-blue-600 bg-blue-50';
    return 'text-yellow-600 bg-yellow-50';
  };

  const getTrustColor = (trust: number) => {
    if (trust > 0.8) return 'bg-green-100 text-green-800';
    if (trust > 0.6) return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">Diagnosis Records</h2>
          <p className="text-gray-600 mt-1">Manage and view all diagnosis records</p>
        </div>
        <button
          onClick={handleExport}
          className="flex items-center gap-2 bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700"
        >
          <Download size={20} />
          Export
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="relative">
            <Search className="absolute left-3 top-3 text-gray-400" size={20} />
            <input
              type="text"
              placeholder="Search by patient name/email..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setCurrentPage(1);
              }}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <select
            value={diseaseFilter}
            onChange={(e) => {
              setDiseaseFilter(e.target.value);
              setCurrentPage(1);
            }}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All Diseases</option>
            {DISEASES.map((disease) => (
              <option key={disease} value={disease}>
                {disease.replace('_', ' ').toUpperCase()}
              </option>
            ))}
          </select>

          <button
            onClick={() => fetchRecords()}
            className="px-4 py-2 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 flex items-center gap-2 justify-center"
          >
            <Filter size={20} />
            Refresh
          </button>
        </div>
      </div>

      {/* Error Message */}
      {error && <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">{error}</div>}

      {/* Records Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-100 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Patient</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Disease</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Prediction</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Confidence</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Trust Score</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Date</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {loading ? (
                <tr>
                  <td colSpan={7} className="px-6 py-4 text-center text-gray-500">
                    Loading...
                  </td>
                </tr>
              ) : records.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-4 text-center text-gray-500">
                    No records found
                  </td>
                </tr>
              ) : (
                records.map((record) => (
                  <tr key={record.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm text-gray-900">{record.patient_name || 'Anonymous'}</td>
                    <td className="px-6 py-4 text-sm">
                      <span className="inline-block px-3 py-1 rounded-full text-xs font-semibold bg-purple-100 text-purple-800">
                        {record.disease_key.replace('_', ' ').toUpperCase()}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">{record.prediction}</td>
                    <td className="px-6 py-4 text-sm">
                      <span className={`inline-block px-3 py-1 rounded-full text-xs font-semibold ${getConfidenceColor(record.confidence)}`}>
                        {(record.confidence * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <span className={`inline-block px-3 py-1 rounded-full text-xs font-semibold ${getTrustColor(record.trust_score)}`}>
                        {(record.trust_score * 100).toFixed(0)}%
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {new Date(record.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 text-sm">
                      <button
                        onClick={() => handleDeleteRecord(record.id)}
                        className="p-1 text-red-600 hover:bg-red-50 rounded"
                        title="Delete record"
                      >
                        <Trash2 size={16} />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
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
          Total records: {totalRecords} | Showing {records.length} on this page
        </p>
      </div>
    </div>
  );
};
