import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from 'react';
import { Alert, Button, CircularProgress, LinearProgress, MenuItem, TextField } from '@mui/material';
import MonitorHeartIcon from '@mui/icons-material/MonitorHeart';
import ShieldIcon from '@mui/icons-material/Shield';
import AccountTreeIcon from '@mui/icons-material/AccountTree';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import MedicalServicesIcon from '@mui/icons-material/MedicalServices';
import { useNavigate } from 'react-router-dom';
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
import type { Disease, DiseaseInputSpec, TrustPoint } from '../types';
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
  blockchain_status: Record<string, any>;
  input_modality: string;
  artifacts: DiagnosisArtifact[];
}

interface DiagnosisArtifact {
  id: string;
  kind: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  sha256: string;
}

interface DiagnosisRecord {
  diagnosis_id: string;
  patient_id: string | null;
  patient_name: string | null;
  patient_email: string | null;
  doctor_id: string | null;
  disease_key: string;
  prediction: string;
  confidence: number;
  input_modality: string;
  artifacts: DiagnosisArtifact[];
  trust_score: number;
  blockchain_hash: string;
  ethereum_tx_hash: string | null;
  fabric_tx_id: string | null;
  doctor_notes: string | null;
  created_at: string;
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const role = useAppSelector((state) => state.auth.role);
  const [diseases, setDiseases] = useState<Disease[]>([]);
  const [trust, setTrust] = useState<TrustPoint[]>([]);
  const [result, setResult] = useState<PredictionResult | null>(null);
  const [records, setRecords] = useState<DiagnosisRecord[]>([]);
  const [federated, setFederated] = useState<any>(null);
  const [blockchain, setBlockchain] = useState<any>(null);
  const [error, setError] = useState('');
  const [selectedDiseaseKey, setSelectedDiseaseKey] = useState('');
  const [inputSpec, setInputSpec] = useState<DiseaseInputSpec | null>(null);
  const [schemaLoading, setSchemaLoading] = useState(false);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [supportingPdf, setSupportingPdf] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [verification, setVerification] = useState<Record<string, any> | null>(null);

  const canDiagnose = role === 'DOCTOR' || role === 'SUPER_ADMIN';
  const canViewBlockchain = role === 'SUPER_ADMIN' || role === 'HOSPITAL_ADMIN' || role === 'DOCTOR';

  useEffect(() => {
    api.get<Disease[]>('/datasets/diseases').then((res) => {
      setDiseases(res.data);
      setSelectedDiseaseKey((current) => current || res.data[0]?.key || '');
    }).catch(() => setError('Could not load the disease catalog.'));
  }, []);

  useEffect(() => {
    api.get('/federated/dashboard').then((res) => setFederated(res.data)).catch(() => null);
    if (canViewBlockchain) {
      api.get('/blockchain/explorer').then((res) => setBlockchain(res.data)).catch(() => null);
    }
    api.get('/trust/history').then((res) => setTrust(res.data)).catch(() => null);
    api.get('/predictions').then((res) => setRecords(res.data)).catch(() => setRecords([]));
  }, [result, canViewBlockchain]);

  useEffect(() => {
    if (!selectedDiseaseKey) return;
    const controller = new AbortController();
    setSchemaLoading(true);
    setInputSpec(null);
    setImageFile(null);
    setSupportingPdf(null);
    api.get<DiseaseInputSpec>(`/datasets/diseases/${selectedDiseaseKey}/features`, {
      signal: controller.signal,
      timeout: 60000,
    })
      .then((res) => setInputSpec(res.data))
      .catch((requestError) => {
        if (requestError?.code !== 'ERR_CANCELED') {
          setError('Could not load the required inputs for this disease.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setSchemaLoading(false);
      });
    return () => controller.abort();
  }, [selectedDiseaseKey]);

  const metricRows = useMemo(() => {
    if (!result) return [];
    const comparableMetrics = ['accuracy', 'balanced_accuracy', 'precision', 'recall', 'f1_score', 'auc'];
    return Object.entries(result.metrics)
      .filter(([name, value]) => comparableMetrics.includes(name) && value >= 0 && value <= 1)
      .map(([name, value]) => ({ name: name.replace(/_/g, ' '), value }));
  }, [result]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');
    const data = new FormData(event.currentTarget);
    setSubmitting(true);
    try {
      if (!inputSpec) throw new Error('Disease input specification is not loaded.');
      const patientId = data.get('patient_id');
      let response;
      if (inputSpec.input_mode === 'image') {
        if (!imageFile) throw new Error('Choose a medical image before running the diagnosis.');
        const upload = new FormData();
        upload.append('disease_key', selectedDiseaseKey);
        upload.append('patient_name', String(data.get('patient_name') ?? ''));
        upload.append('patient_email', String(data.get('patient_email') ?? ''));
        upload.append('doctor_notes', String(data.get('doctor_notes') ?? ''));
        if (patientId) upload.append('patient_id', String(patientId));
        upload.append('image', imageFile);
        if (supportingPdf) upload.append('supporting_pdf', supportingPdf);
        response = await api.post('/predictions/image', upload);
      } else {
        const features = Object.fromEntries(
          inputSpec.features.map((feature) => [
            feature.name,
            feature.input_type === 'category'
              ? data.get(`feature:${feature.name}`)
              : Number(data.get(`feature:${feature.name}`)),
          ]),
        );
        const upload = new FormData();
        upload.append('disease_key', selectedDiseaseKey);
        upload.append('patient_name', String(data.get('patient_name') ?? ''));
        upload.append('patient_email', String(data.get('patient_email') ?? ''));
        upload.append('doctor_notes', String(data.get('doctor_notes') ?? ''));
        upload.append('features_json', JSON.stringify(features));
        if (patientId) upload.append('patient_id', String(patientId));
        if (supportingPdf) upload.append('supporting_pdf', supportingPdf);
        response = await api.post('/predictions/tabular', upload);
      }
      setResult(response.data);
      setVerification(null);
    } catch (requestError: any) {
      const detail = requestError?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : requestError?.message || 'Prediction failed.');
    } finally {
      setSubmitting(false);
    }
  };

  const chooseImage = (event: ChangeEvent<HTMLInputElement>) => {
    setImageFile(event.target.files?.[0] ?? null);
  };

  const choosePdf = (event: ChangeEvent<HTMLInputElement>) => {
    setSupportingPdf(event.target.files?.[0] ?? null);
  };

  const downloadFile = async (path: string, filename: string) => {
    try {
      const response = await api.get(path, { responseType: 'blob' });
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = filename;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch {
      setError('The file could not be downloaded or you do not have access.');
    }
  };

  const verifyBlockchain = async (diagnosisId: string) => {
    try {
      const response = await api.get(`/blockchain/verify/${diagnosisId}`);
      setVerification(response.data);
    } catch {
      setError('Blockchain verification could not be completed.');
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
            <Button
              variant="contained"
              startIcon={<MedicalServicesIcon />}
              onClick={() => navigate('/diagnosis')}
            >
              Disease Pages
            </Button>
            <Button variant="outlined" startIcon={<ShieldIcon />}>Trust</Button>
            <Button variant="outlined" startIcon={<AccountTreeIcon />}>Federated</Button>
            <Button
              variant="contained"
              startIcon={<SmartToyIcon />}
              onClick={() => navigate('/chat')}
            >
              MedAI Chat
            </Button>
            <Button
              variant="contained"
              onClick={() => navigate('/role-dashboard')}
            >
              Role Dashboard
            </Button>
          </div>
        </div>

        {error && <Alert className="mb-5" severity="error">{error}</Alert>}

        <section className="grid gap-5 lg:grid-cols-[380px_1fr]">
          <form onSubmit={submit} className="grid content-start gap-4 rounded border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center gap-2">
              <MonitorHeartIcon className="text-trust-teal" />
              <h2 className="text-xl font-black">Diagnosis</h2>
            </div>
            {!canDiagnose && (
              <Alert severity="info">Only doctors and super admins can run model diagnosis. Patients may view their own results below.</Alert>
            )}
            <div className="border-t border-slate-200 pt-3">
              <h3 className="font-bold">Patient information</h3>
              <p className="text-sm text-slate-500">Identify the patient before entering disease-specific clinical data.</p>
            </div>
            <TextField name="patient_name" label="Patient full name" required disabled={!canDiagnose} />
            <TextField name="patient_email" label="Patient email" type="email" required disabled={!canDiagnose} />
            {(role === 'DOCTOR' || role === 'SUPER_ADMIN') && (
              <TextField name="patient_id" label="Patient user ID (optional)" helperText="Use this when the patient already has an account." />
            )}
            <div className="border-t border-slate-200 pt-3">
              <h3 className="font-bold">Disease and clinical inputs</h3>
              <p className="text-sm text-slate-500">The fields below come directly from the selected model.</p>
            </div>
            <TextField
              name="disease_key"
              label="Disease"
              select
              value={selectedDiseaseKey}
              onChange={(event) => setSelectedDiseaseKey(event.target.value)}
              disabled={!canDiagnose || !diseases.length}
            >
              {diseases.map((disease) => (
                <MenuItem key={disease.key} value={disease.key}>{disease.name}</MenuItem>
              ))}
            </TextField>
            {inputSpec?.model_info?.selected_model && (
              <div className="rounded border border-teal-100 bg-teal-50 p-3 text-sm">
                <p className="font-bold text-teal-900">Model card</p>
                <p className="mt-1 text-teal-800">
                  {inputSpec.model_info.selected_model.replace(/_/g, ' ')}
                  {inputSpec.model_info.test_metrics?.balanced_accuracy !== undefined
                    ? ` · held-out balanced accuracy ${(inputSpec.model_info.test_metrics.balanced_accuracy * 100).toFixed(1)}%`
                    : ''}
                </p>
                <p className="mt-1 text-xs text-teal-700">
                  Research decision support only. A prediction is not a medical diagnosis.
                </p>
              </div>
            )}
            {inputSpec?.model_info?.deployment_status === 'blocked_low_quality' && (
              <Alert severity="warning">
                This model is disabled because leakage-safe testing found insufficient predictive signal.
                Replace the dataset with a representative patient cohort before use.
              </Alert>
            )}
            {schemaLoading && <div className="flex items-center gap-2 text-sm text-slate-500"><CircularProgress size={18} /> Loading model inputs…</div>}
            {inputSpec?.input_mode === 'features' && (
              <>
                <Alert severity="info">{inputSpec.features.length} required model features</Alert>
                <div className="grid max-h-[520px] gap-3 overflow-y-auto pr-1">
                  {inputSpec.features.map((feature) => feature.input_type === 'boolean' ? (
                    <TextField
                      key={`${selectedDiseaseKey}:${feature.name}`}
                      name={`feature:${feature.name}`}
                      label={feature.label}
                      select
                      required
                      defaultValue={feature.default ?? 0}
                      disabled={!canDiagnose}
                    >
                      <MenuItem value={0}>No / 0</MenuItem>
                      <MenuItem value={1}>Yes / 1</MenuItem>
                    </TextField>
                  ) : feature.input_type === 'category' ? (
                    <TextField
                      key={`${selectedDiseaseKey}:${feature.name}`}
                      name={`feature:${feature.name}`}
                      label={feature.label}
                      select
                      required
                      defaultValue={feature.default ?? ''}
                      disabled={!canDiagnose}
                    >
                      {(feature.choices ?? []).map((choice) => (
                        <MenuItem key={String(choice)} value={choice}>{String(choice)}</MenuItem>
                      ))}
                    </TextField>
                  ) : (
                    <TextField
                      key={`${selectedDiseaseKey}:${feature.name}`}
                      name={`feature:${feature.name}`}
                      label={feature.label}
                      type="number"
                      required
                      defaultValue={feature.default ?? ''}
                      disabled={!canDiagnose}
                      inputProps={{ step: 'any', min: feature.minimum ?? undefined, max: feature.maximum ?? undefined }}
                      helperText={
                        feature.minimum !== null && feature.maximum !== null
                          ? `Training range: ${feature.minimum} to ${feature.maximum}`
                          : undefined
                      }
                    />
                  ))}
                </div>
                {!schemaLoading && inputSpec.features.length === 0 && (
                  <Alert severity="warning">No trained model schema is available for this disease.</Alert>
                )}
              </>
            )}
            {inputSpec?.input_mode === 'image' && (
              <div className="grid gap-3 rounded border border-dashed border-slate-300 p-4">
                <p className="text-sm text-slate-600">Upload one JPEG, PNG, or WebP medical image (maximum 10 MB).</p>
                {!inputSpec.model_available && (
                  <Alert severity="warning">This image model has not been trained yet.</Alert>
                )}
                <Button component="label" variant="outlined" disabled={!canDiagnose}>
                  Choose medical image
                  <input hidden type="file" accept="image/jpeg,image/png,image/webp" onChange={chooseImage} />
                </Button>
                <p className="truncate text-sm font-semibold text-trust-teal">
                  {imageFile ? imageFile.name : 'No image selected'}
                </p>
              </div>
            )}
            <div className="grid gap-2 rounded border border-dashed border-slate-300 p-4">
              <p className="text-sm text-slate-600">Optional supporting medical report (PDF, maximum 15 MB).</p>
              <Button component="label" variant="outlined" disabled={!canDiagnose}>
                Choose supporting PDF
                <input hidden type="file" accept="application/pdf" onChange={choosePdf} />
              </Button>
              <p className="truncate text-sm font-semibold text-trust-teal">
                {supportingPdf ? supportingPdf.name : 'No supporting PDF selected'}
              </p>
            </div>
            <TextField
              name="doctor_notes"
              label="Doctor notes"
              multiline
              minRows={3}
              defaultValue="Reviewed clinical profile and uploaded report."
              disabled={!canDiagnose}
            />
            <Button
              type="submit"
              variant="contained"
              disabled={
                !canDiagnose ||
                submitting ||
                schemaLoading ||
                !inputSpec ||
                !inputSpec.model_available ||
                (inputSpec.input_mode === 'features' && !inputSpec.features.length) ||
                (inputSpec.input_mode === 'image' && (!imageFile || !inputSpec.model_available))
              }
            >
              {submitting ? 'Running model…' : 'Run Diagnosis'}
            </Button>
          </form>

          <div className="grid gap-5">
            <div className="grid gap-4 md:grid-cols-4">
              {([
                ['Trust Score', result?.trust_score ?? null],
                ['AECS', result?.aecs ?? null],
                ['Robustness', result?.adversarial?.robustness_score ?? null],
                ['Data Integrity', blockchain?.reliability ?? null],
              ] as [string, number | null][]).map(([label, value]) => (
                <div key={label as string} className="rounded border border-slate-200 bg-white p-4 shadow-sm">
                  <p className="text-sm font-semibold text-slate-500">{label}</p>
                  <p className="mt-2 text-3xl font-black text-trust-teal">{value === null ? '—' : value.toFixed(3)}</p>
                  <LinearProgress className="mt-3" variant="determinate" value={(value ?? 0) * 100} />
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
                <Button className="mr-2 mt-4" variant="outlined" onClick={() => downloadFile(`/reports/${result.diagnosis_id}.pdf`, `trustmedai-${result.diagnosis_id}.pdf`)}>
                  Download PDF Report
                </Button>
                {canViewBlockchain && (
                  <Button className="mt-4" variant="outlined" onClick={() => verifyBlockchain(result.diagnosis_id)}>
                    Verify Blockchain
                  </Button>
                )}
                <div className="mt-4 grid gap-2">
                  {result.artifacts.map((artifact) => (
                    <Button
                      key={artifact.id}
                      size="small"
                      variant="text"
                      onClick={() => downloadFile(
                        `/reports/${result.diagnosis_id}/artifacts/${artifact.id}`,
                        artifact.original_filename,
                      )}
                    >
                      {artifact.kind}: {artifact.original_filename} ({Math.ceil(artifact.size_bytes / 1024)} KB)
                    </Button>
                  ))}
                </div>
                {verification && (
                  <Alert className="mt-3" severity={verification.verified ? 'success' : 'warning'}>
                    Local hash: {verification.local_hash_match ? 'valid' : 'invalid'}; chain anchor: {verification.verified ? 'verified' : 'not verified'}
                  </Alert>
                )}
              </div>
            )}

            <div className="rounded border border-slate-200 bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <h2 className="mb-2 text-xl font-black">Clinical Record Summary</h2>
                  <p className="text-sm text-slate-500">Showing records you can access for this role.</p>
                </div>
                <div className="rounded-full bg-slate-100 px-3 py-1 text-sm font-semibold text-slate-700">{records.length} records</div>
              </div>
              <div className="mt-4 grid gap-3">
                {records.length ? records.map((record) => (
                  <div
                    key={record.diagnosis_id}
                    data-testid={`diagnosis-record-${record.diagnosis_id}`}
                    className="rounded border border-slate-200 bg-slate-50 p-3"
                  >
                    <div className="grid gap-2 md:grid-cols-2">
                      <p><strong>Disease:</strong> {record.disease_key}</p>
                      <p><strong>Prediction:</strong> {record.prediction}</p>
                      <p><strong>Confidence:</strong> {record.confidence.toFixed(3)}</p>
                      <p><strong>Trust:</strong> {record.trust_score.toFixed(3)}</p>
                      <p><strong>Input:</strong> {record.input_modality}</p>
                      <p><strong>Stored files:</strong> {record.artifacts.length}</p>
                      <p><strong>Patient:</strong> {record.patient_id ?? 'N/A'}</p>
                      <p><strong>Patient name:</strong> {record.patient_name ?? 'N/A'}</p>
                      <p><strong>Patient email:</strong> {record.patient_email ?? 'N/A'}</p>
                      <p><strong>Doctor:</strong> {record.doctor_id ?? 'N/A'}</p>
                    </div>
                    <div className="mt-2 text-xs text-slate-500">
                      <p><strong>Created:</strong> {new Date(record.created_at).toLocaleString()}</p>
                      <p className="break-all"><strong>Hash:</strong> {record.blockchain_hash}</p>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <Button
                        data-testid={`download-report-${record.diagnosis_id}`}
                        size="small"
                        variant="outlined"
                        onClick={() => downloadFile(
                          `/reports/${record.diagnosis_id}.pdf`,
                          `trustmedai-${record.diagnosis_id}.pdf`,
                        )}
                      >
                        Download PDF
                      </Button>
                      {canViewBlockchain && (
                        <Button
                          size="small"
                          variant="text"
                          onClick={() => verifyBlockchain(record.diagnosis_id)}
                        >
                          Verify Blockchain
                        </Button>
                      )}
                    </div>
                  </div>
                )) : <p className="text-slate-500">No diagnosis records currently available.</p>}
              </div>
            </div>
            <div className="grid gap-5 lg:grid-cols-2">
              <div className="rounded border border-slate-200 bg-white p-5 shadow-sm">
                <h2 className="mb-4 text-xl font-black">Model Metrics</h2>
                {metricRows.length ? <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={metricRows}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis domain={[0, 1]} />
                      <Tooltip />
                      <Bar dataKey="value" fill="#0f766e" />
                    </BarChart>
                  </ResponsiveContainer>
                </div> : <p className="text-slate-500">Run a diagnosis to view measured model metrics.</p>}
              </div>

              <div className="rounded border border-slate-200 bg-white p-5 shadow-sm">
                <h2 className="mb-4 text-xl font-black">Trust Evolution</h2>
                {trust.length ? <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={trust}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="timestamp" hide />
                      <YAxis domain={[0, 1]} />
                      <Tooltip />
                      <Legend />
                      <Line dataKey="dtei" stroke="#0f766e" strokeWidth={3} />
                      <Line dataKey="robustness" stroke="#f97316" strokeWidth={3} />
                    </LineChart>
                  </ResponsiveContainer>
                </div> : <p className="text-slate-500">No trust history has been recorded yet.</p>}
              </div>
            </div>

            <div className="grid gap-5 lg:grid-cols-2">
              <div className="rounded border border-slate-200 bg-white p-5 shadow-sm">
                <h2 className="text-xl font-black">Federated Simulation</h2>
                <p className="mt-1 text-sm text-slate-500">
                  Demonstration nodes only; no live Flower training round is connected.
                </p>
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
                <p className="mt-2 text-sm text-slate-600">Chain anchor rate: {blockchain ? Number(blockchain.chain_anchor_rate).toFixed(3) : 'N/A'}</p>
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
