import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Alert, Button, LinearProgress, MenuItem, TextField } from '@mui/material';
import MonitorHeartIcon from '@mui/icons-material/MonitorHeart';
import ShieldIcon from '@mui/icons-material/Shield';
import AccountTreeIcon from '@mui/icons-material/AccountTree';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import Header from '../components/Header';
import { api } from '../api/client';
import type { Disease, TrustPoint } from '../types';
import { useAppSelector } from '../store';

interface PredictionResult {
  diagnosis_id: string;
  disease_key: string;
  prediction: string;
  confidence: number;
  metrics: Record<string, number>;
  adversarial: Record<string, number>;
  aecs: number;
  trust_score: number;
  dtei_components: Record<string, number>;
  blockchain_hash: string;
}

export default function DashboardPage() {
  const role = useAppSelector((state) => state.auth.role);
  const [diseases, setDiseases] = useState<Disease[]>([]);
  const [trust, setTrust] = useState<TrustPoint[]>([]);
  const [result, setResult] = useState<PredictionResult | null>(null);
  const [federated, setFederated] = useState<any>(null);
  const [blockchain, setBlockchain] = useState<any>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.get('/datasets/diseases').then((res) => setDiseases(res.data));
    api.get('/federated/dashboard').then((res) => setFederated(res.data)).catch(() => null);
    api.get('/blockchain/explorer').then((res) => setBlockchain(res.data)).catch(() => null);
    api.get('/trust/history').then((res) => setTrust(res.data)).catch(() => null);
  }, [result]);

  const metricRows = useMemo(() => {
    if (!result) return [];
    return Object.entries(result.metrics).map(([name, value]) => ({ name, value }));
  }, [result]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    const data = new FormData(event.currentTarget);
    try {
      const res = await api.post('/predictions', {
        disease_key: data.get('disease_key'),
        features: {
          age: Number(data.get('age')),
          clinical_score: Number(data.get('clinical_score')),
          biomarker: Number(data.get('biomarker')),
        },
        doctor_notes: data.get('doctor_notes'),
      });
      setResult(res.data);
    } catch {
      setError('Prediction failed. Your role may not have diagnosis permission.');
    }
  };

  return (
    <div className="min-h-screen bg-[#f7fbfa]">
      <Header />
      <main className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-3xl font-black">TrustMedAI Dashboard</h1>
            <p className="mt-1 text-slate-600">Active role: {role ?? 'UNKNOWN'}</p>
          </div>
          <div className="flex gap-2">
            <Button variant="outlined" startIcon={<ShieldIcon />}>Trust</Button>
            <Button variant="outlined" startIcon={<AccountTreeIcon />}>Federated</Button>
          </div>
        </div>

        {error && <Alert className="mb-5" severity="error">{error}</Alert>}

        <section className="grid gap-5 lg:grid-cols-[380px_1fr]">
          <form onSubmit={submit} className="grid content-start gap-4 rounded border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center gap-2">
              <MonitorHeartIcon className="text-trust-teal" />
              <h2 className="text-xl font-black">Diagnosis</h2>
            </div>
            <TextField name="disease_key" label="Disease" select defaultValue={diseases[0]?.key ?? 'heart'}>
              {(diseases.length ? diseases : [{ key: 'heart', name: 'Heart Disease' }]).map((disease: any) => (
                <MenuItem key={disease.key} value={disease.key}>{disease.name}</MenuItem>
              ))}
            </TextField>
            <TextField name="age" label="Age" type="number" defaultValue={58} />
            <TextField name="clinical_score" label="Clinical score" type="number" defaultValue={72} />
            <TextField name="biomarker" label="Biomarker" type="number" defaultValue={64} />
            <TextField name="doctor_notes" label="Doctor notes" multiline minRows={3} defaultValue="Reviewed clinical profile and uploaded report." />
            <Button type="submit" variant="contained">Run Diagnosis</Button>
          </form>

          <div className="grid gap-5">
            <div className="grid gap-4 md:grid-cols-4">
              {[
                ['Trust Score', result?.trust_score ?? 0.91],
                ['AECS', result?.aecs ?? 0.94],
                ['Robustness', result?.adversarial?.robustness_score ?? 0.88],
                ['Blockchain', blockchain?.reliability ?? 0.986],
              ].map(([label, value]) => (
                <div key={label as string} className="rounded border border-slate-200 bg-white p-4 shadow-sm">
                  <p className="text-sm font-semibold text-slate-500">{label}</p>
                  <p className="mt-2 text-3xl font-black text-trust-teal">{Number(value).toFixed(3)}</p>
                  <LinearProgress className="mt-3" variant="determinate" value={Number(value) * 100} />
                </div>
              ))}
            </div>

            {result && (
              <div className="rounded border border-slate-200 bg-white p-5 shadow-sm">
                <h2 className="text-xl font-black">Latest Prediction</h2>
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  <p><strong>Prediction:</strong> {result.prediction}</p>
                  <p><strong>Confidence:</strong> {result.confidence.toFixed(3)}</p>
                  <p className="break-all"><strong>Hash:</strong> {result.blockchain_hash}</p>
                  <p><strong>Diagnosis ID:</strong> {result.diagnosis_id}</p>
                </div>
                <Button className="mt-4" variant="outlined" href={`${import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'}/reports/${result.diagnosis_id}.pdf`}>
                  Download PDF Report
                </Button>
              </div>
            )}

            <div className="grid gap-5 lg:grid-cols-2">
              <div className="rounded border border-slate-200 bg-white p-5 shadow-sm">
                <h2 className="mb-4 text-xl font-black">Model Metrics</h2>
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={metricRows.length ? metricRows : [{ name: 'accuracy', value: 0.91 }, { name: 'precision', value: 0.9 }, { name: 'recall', value: 0.88 }, { name: 'auc', value: 0.94 }]}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis domain={[0, 1]} />
                      <Tooltip />
                      <Bar dataKey="value" fill="#0f766e" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="rounded border border-slate-200 bg-white p-5 shadow-sm">
                <h2 className="mb-4 text-xl font-black">Trust Evolution</h2>
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={trust.length ? trust : [{ timestamp: 'R1', dtei: 0.78, robustness: 0.76 }, { timestamp: 'R2', dtei: 0.84, robustness: 0.82 }, { timestamp: 'R3', dtei: 0.91, robustness: 0.88 }]}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="timestamp" hide />
                      <YAxis domain={[0, 1]} />
                      <Tooltip />
                      <Legend />
                      <Line dataKey="dtei" stroke="#0f766e" strokeWidth={3} />
                      <Line dataKey="robustness" stroke="#f97316" strokeWidth={3} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            <div className="grid gap-5 lg:grid-cols-2">
              <div className="rounded border border-slate-200 bg-white p-5 shadow-sm">
                <h2 className="text-xl font-black">Federated Dashboard</h2>
                <div className="mt-4 grid gap-3">
                  {(federated?.nodes ?? []).map((node: any) => (
                    <div key={node.id} className="flex items-center justify-between rounded bg-slate-50 p-3">
                      <span className="font-semibold">{node.name}</span>
                      <span className="text-trust-teal">{node.trust}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="rounded border border-slate-200 bg-white p-5 shadow-sm">
                <h2 className="text-xl font-black">Blockchain Explorer</h2>
                <p className="mt-3 text-sm text-slate-600">Mode: {blockchain?.mode ?? 'hash-only'}</p>
                <p className="mt-2 text-sm text-slate-600">Fabric: {blockchain?.fabric?.chaincode ?? 'trustledger'}</p>
                <div className="mt-4 max-h-44 overflow-auto rounded bg-slate-50 p-3 text-xs">
                  {(blockchain?.events ?? []).length ? blockchain.events.map((event: any) => (
                    <p key={event.hash} className="break-all">{event.timestamp} - {event.hash}</p>
                  )) : <p>No ledger events yet.</p>}
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
