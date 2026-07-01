import { useEffect, useState } from 'react';
import { Alert, Button } from '@mui/material';
import Header from '../components/Header';
import { api } from '../api/client';
import type { TrustPoint } from '../types';

interface DiagnosisRecord {
  diagnosis_id: string;
  patient_id: string | null;
  doctor_id: string | null;
  disease_key: string;
  prediction: string;
  confidence: number;
  trust_score: number;
  blockchain_hash: string;
  ethereum_tx_hash: string | null;
  fabric_tx_id: string | null;
  doctor_notes: string | null;
  created_at: string;
}

export default function AdminDashboardPage() {
  const [records, setRecords] = useState<DiagnosisRecord[]>([]);
  const [trust, setTrust] = useState<TrustPoint[]>([]);
  const [nodes, setNodes] = useState<any[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get('/predictions').then((res) => setRecords(res.data)).catch(() => setRecords([]));
    api.get('/trust/history').then((res) => setTrust(res.data)).catch(() => setTrust([]));
    api.get('/blockchain/nodes')
      .then((res) => setNodes(res.data.ethereum || []))
      .catch(() => setNodes([]));
  }, []);

  return (
    <div className="min-h-screen bg-[#f7fbfa]">
      <Header />
      <main className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-black">Admin Dashboard</h1>
          <p className="mt-1 text-slate-600">Monitor the platform, blockchain anchors, and all diagnosis records.</p>
        </div>

        {error && <Alert className="mb-5" severity="error">{error}</Alert>}

        <div className="grid gap-5 lg:grid-cols-[1fr_420px]">
          <div className="space-y-5">
            <div className="rounded border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-xl font-black">Platform Records</h2>
              <p className="mt-3 text-slate-600">Total records: {records.length}</p>
              <div className="mt-4 space-y-3">
                {records.slice(0, 4).map((record) => (
                  <div key={record.diagnosis_id} className="rounded border border-slate-200 bg-slate-50 p-3">
                    <div className="grid gap-2 md:grid-cols-2">
                      <p><strong>Disease:</strong> {record.disease_key}</p>
                      <p><strong>Prediction:</strong> {record.prediction}</p>
                      <p><strong>Patient:</strong> {record.patient_id ?? 'N/A'}</p>
                      <p><strong>Doctor:</strong> {record.doctor_id ?? 'N/A'}</p>
                    </div>
                    <p className="mt-2 text-xs text-slate-500 break-all"><strong>Hash:</strong> {record.blockchain_hash}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-xl font-black">Blockchain Network</h2>
              <div className="mt-4 space-y-2 text-sm text-slate-600">
                {nodes.length ? nodes.map((node) => (
                  <div key={node.name} className="rounded border border-slate-200 bg-slate-50 p-3">
                    <p><strong>{node.name}</strong></p>
                    <p>Status: {node.status}</p>
                  </div>
                )) : <p>No blockchain node metadata available.</p>}
              </div>
            </div>
          </div>

          <aside className="space-y-5">
            <div className="rounded border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-xl font-black">Trust History</h2>
              <div className="mt-4 text-sm text-slate-600">
                {trust.length ? (
                  <ul className="list-disc space-y-2 pl-5">
                    {trust.slice(-5).map((point, index) => (
                      <li key={index}>{point.disease_key}: DTEI {point.dtei.toFixed(3)}, integrity {point.blockchain_integrity.toFixed(3)}</li>
                    ))}
                  </ul>
                ) : (
                  <p>No trust history available yet.</p>
                )}
              </div>
            </div>

            <div className="rounded border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-xl font-black">Admin Actions</h2>
              <Button variant="contained" onClick={() => window.location.reload()}>Refresh Data</Button>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}
