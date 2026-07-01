import { useEffect, useState } from 'react';
import { Alert, Button, LinearProgress } from '@mui/material';
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
  created_at: string;
}

export default function PatientDashboardPage() {
  const [records, setRecords] = useState<DiagnosisRecord[]>([]);
  const [trust, setTrust] = useState<TrustPoint[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get('/predictions').then((res) => setRecords(res.data)).catch(() => setRecords([]));
    api.get('/trust/history').then((res) => setTrust(res.data)).catch(() => setTrust([]));
  }, []);

  return (
    <div className="min-h-screen bg-[#f7fbfa]">
      <Header />
      <main className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-black">Patient Dashboard</h1>
          <p className="mt-1 text-slate-600">Your diagnosis results and trust history are shown here.</p>
        </div>

        {error && <Alert className="mb-5" severity="error">{error}</Alert>}

        <div className="grid gap-5 lg:grid-cols-[1fr_420px]">
          <div className="space-y-5">
            <div className="rounded border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-xl font-black">Your Diagnosis Records</h2>
              <div className="mt-4 space-y-3">
                {records.length ? records.map((record) => (
                  <div key={record.diagnosis_id} className="rounded border border-slate-200 bg-slate-50 p-3">
                    <div className="grid gap-2 md:grid-cols-2">
                      <p><strong>Disease:</strong> {record.disease_key}</p>
                      <p><strong>Prediction:</strong> {record.prediction}</p>
                      <p><strong>Confidence:</strong> {record.confidence.toFixed(3)}</p>
                      <p><strong>Trust Score:</strong> {record.trust_score.toFixed(3)}</p>
                    </div>
                    <p className="mt-2 text-sm text-slate-500"><strong>Doctor:</strong> {record.doctor_id ?? 'N/A'}</p>
                    <p className="mt-1 text-xs text-slate-500 break-all"><strong>Blockchain Hash:</strong> {record.blockchain_hash}</p>
                    <p className="mt-1 text-xs text-slate-500">Created: {new Date(record.created_at).toLocaleString()}</p>
                  </div>
                )) : <p className="text-slate-500">No diagnosis records available yet.</p>}
              </div>
            </div>
          </div>

          <aside className="space-y-5">
            <div className="rounded border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-xl font-black">Trust Evolution</h2>
              <div className="mt-4 text-sm text-slate-600">
                {trust.length ? (
                  <ul className="list-disc space-y-2 pl-5">
                    {trust.slice(-5).map((point, index) => (
                      <li key={index}>
                        {point.disease_key}: DTEI {point.dtei.toFixed(3)}, robustness {point.robustness.toFixed(3)}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p>No trust history available yet.</p>
                )}
              </div>
            </div>

            <div className="rounded border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-xl font-black">Patient Guidance</h2>
              <p className="mt-3 text-slate-600">If your results are available, you can share the diagnosis ID with your doctor or export the PDF report from the backend using your record ID.</p>
              <Button variant="contained" onClick={() => window.location.reload()}>Refresh</Button>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}
