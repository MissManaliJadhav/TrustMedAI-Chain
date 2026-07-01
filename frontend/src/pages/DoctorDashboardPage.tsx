import { FormEvent, useEffect, useState } from 'react';
import { Alert, Button, MenuItem, TextField } from '@mui/material';
import Header from '../components/Header';
import { api } from '../api/client';
import type { Disease, TrustPoint } from '../types';

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

export default function DoctorDashboardPage() {
  const [diseases, setDiseases] = useState<Disease[]>([]);
  const [records, setRecords] = useState<DiagnosisRecord[]>([]);
  const [trust, setTrust] = useState<TrustPoint[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get('/datasets/diseases').then((res) => setDiseases(res.data)).catch(() => setDiseases([]));
    api.get('/predictions').then((res) => setRecords(res.data)).catch(() => setRecords([]));
    api.get('/trust/history').then((res) => setTrust(res.data)).catch(() => setTrust([]));
  }, []);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    const data = new FormData(event.currentTarget);
    try {
      await api.post('/predictions', {
        disease_key: data.get('disease_key'),
        patient_id: String(data.get('patient_id')),
        features: {
          age: Number(data.get('age')),
          clinical_score: Number(data.get('clinical_score')),
          biomarker: Number(data.get('biomarker')),
        },
        doctor_notes: data.get('doctor_notes'),
      });
      setRecords((await api.get('/predictions')).data);
    } catch {
      setError('Diagnosis creation failed. Check your permissions and patient ID.');
    }
  };

  return (
    <div className="min-h-screen bg-[#f7fbfa]">
      <Header />
      <main className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-6">
          <h1 className="text-3xl font-black">Doctor Dashboard</h1>
          <p className="mt-1 text-slate-600">Create diagnoses and review patient trust history.</p>
        </div>

        {error && <Alert className="mb-5" severity="error">{error}</Alert>}

        <div className="grid gap-5 lg:grid-cols-[420px_1fr]">
          <form onSubmit={submit} className="grid gap-4 rounded border border-slate-200 bg-white p-5 shadow-sm">
            <h2 className="text-xl font-black">New Diagnosis</h2>
            <TextField name="patient_id" label="Patient ID" required />
            <TextField name="disease_key" label="Disease" select defaultValue={diseases[0]?.key ?? 'heart'} required>
              {(diseases.length ? diseases : [{ key: 'heart', name: 'Heart Disease' }]).map((disease) => (
                <MenuItem key={disease.key} value={disease.key}>{disease.name}</MenuItem>
              ))}
            </TextField>
            <TextField name="age" label="Age" type="number" defaultValue={58} required />
            <TextField name="clinical_score" label="Clinical score" type="number" defaultValue={72} required />
            <TextField name="biomarker" label="Biomarker" type="number" defaultValue={64} required />
            <TextField name="doctor_notes" label="Doctor notes" multiline minRows={3} defaultValue="Reviewed clinical profile and uploaded report." />
            <Button type="submit" variant="contained">Submit Diagnosis</Button>
          </form>

          <div className="space-y-5">
            <div className="rounded border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-xl font-black">Patient Records</h2>
              <div className="mt-4 space-y-3">
                {records.length ? records.map((record) => (
                  <div key={record.diagnosis_id} className="rounded border border-slate-200 bg-slate-50 p-3">
                    <div className="grid gap-2 md:grid-cols-2">
                      <p><strong>Patient:</strong> {record.patient_id ?? 'N/A'}</p>
                      <p><strong>Disease:</strong> {record.disease_key}</p>
                      <p><strong>Prediction:</strong> {record.prediction}</p>
                      <p><strong>Confidence:</strong> {record.confidence.toFixed(3)}</p>
                    </div>
                    <p className="mt-2 text-xs text-slate-500 break-all"><strong>Hash:</strong> {record.blockchain_hash}</p>
                  </div>
                )) : <p className="text-slate-500">No patient diagnosis records yet.</p>}
              </div>
            </div>

            <div className="rounded border border-slate-200 bg-white p-5 shadow-sm">
              <h2 className="text-xl font-black">Trust Insights</h2>
              <div className="mt-4 text-sm text-slate-600">
                {trust.length ? (
                  <ul className="list-disc space-y-2 pl-5">
                    {trust.slice(-5).map((point, index) => (
                      <li key={index}>{point.disease_key}: DTEI {point.dtei.toFixed(3)}</li>
                    ))}
                  </ul>
                ) : (
                  <p>No trust history available yet.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
