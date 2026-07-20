import { ChangeEvent, FormEvent, useEffect, useState } from 'react';
import {
  Alert,
  Button,
  CircularProgress,
  LinearProgress,
  MenuItem,
  TextField,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import DescriptionIcon from '@mui/icons-material/Description';
import ImageSearchIcon from '@mui/icons-material/ImageSearch';
import MonitorHeartIcon from '@mui/icons-material/MonitorHeart';
import VerifiedUserIcon from '@mui/icons-material/VerifiedUser';
import { Link, useParams } from 'react-router-dom';
import Header from '../components/Header';
import { api } from '../api/client';
import { useAppSelector } from '../store';
import type { DiseaseFeature, DiseaseInputSpec } from '../types';

interface DiagnosisArtifact {
  id: string;
  kind: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  sha256?: string;
  created_at?: string;
}

type AnyRecord = Record<string, any>;

interface SubmittedCase {
  patientName: string;
  patientEmail: string;
  patientId: string;
  doctorNotes: string;
  inputMode: 'image' | 'features';
  imageName?: string;
  imageSizeKb?: number;
  supportingPdfName?: string;
  features: Record<string, string | number | null>;
}

interface PredictionResult {
  diagnosis_id: string;
  disease_key: string;
  prediction: string;
  confidence: number;
  metrics?: AnyRecord;
  explanation?: {
    shap?: AnyRecord;
    lime?: AnyRecord;
    gradcam?: AnyRecord;
    captum?: AnyRecord;
    integrated_gradients?: AnyRecord;
    counterfactuals?: AnyRecord;
  };
  adversarial?: AnyRecord;
  trust_score: number;
  aecs: number;
  dtei_components?: Record<string, number>;
  blockchain_hash: string;
  blockchain_status: {
    ethereum?: {
      status?: string;
      verified?: boolean;
      tx_hash?: string;
      block_number?: number;
      receipt_status?: string;
      contract_address?: string;
      network?: string;
      [key: string]: unknown;
    };
    fabric?: {
      status?: string;
      verified?: boolean;
      tx_id?: string;
      channel?: string;
      network?: string;
      consensus?: string;
      anchor?: AnyRecord;
      [key: string]: unknown;
    };
    local_ledger?: {
      status?: string;
      verified?: boolean;
      block_number?: number;
      tx_id?: string;
      block_hash?: string;
      record_hash?: string;
      previous_hash?: string;
      timestamp?: string;
      network?: string;
      consensus?: string;
      ledger_status?: string;
      [key: string]: unknown;
    };
    network?: string;
    consensus?: string;
    ledger_status?: string;
    status?: string;
    verified?: boolean;
    [key: string]: unknown;
  };
  input_modality?: string;
  artifacts: DiagnosisArtifact[];
  ethereum_tx_hash?: string | null;
  fabric_tx_id?: string | null;
  created_at?: string;
}

interface DoctorReviewResult {
  doctor_decision?: string | null;
  final_clinical_decision?: string | null;
  review_notes?: string | null;
  review_status?: string | null;
  reviewed_at?: string | null;
}

interface FederatedRoundSummary {
  round_number?: number;
  status?: string;
  strategy?: string;
  submitted_clients?: number;
  global_model_version?: string;
  metrics?: AnyRecord;
  privacy_config?: AnyRecord;
  update_hash?: string | null;
  created_at?: string | null;
  completed_at?: string | null;
}

interface FederatedDashboard {
  mode?: string;
  architecture?: {
    strategy?: string;
    privacy?: string;
    raw_data_shared?: boolean;
  };
  nodes?: Array<{ id: string; trust?: number; reputation?: number; verified?: boolean }>;
  model_weight_round?: number;
  consensus_reliability?: number;
  active_round?: FederatedRoundSummary | null;
  cifts?: {
    trust_synchronization?: number;
    hospital_reputation?: number;
    trust_evolution?: number[];
  };
}

function FeatureInput({ feature, disabled }: { feature: DiseaseFeature; disabled: boolean }) {
  const sharedProps = {
    name: `feature:${feature.name}`,
    label: feature.label,
    required: feature.required,
    disabled,
    fullWidth: true,
  };

  if (feature.input_type === 'boolean') {
    return (
      <TextField {...sharedProps} select defaultValue={feature.default ?? 0}>
        <MenuItem value={0}>No / 0</MenuItem>
        <MenuItem value={1}>Yes / 1</MenuItem>
      </TextField>
    );
  }

  if (feature.input_type === 'category') {
    return (
      <TextField {...sharedProps} select defaultValue={feature.default ?? ''}>
        {(feature.choices ?? []).map((choice) => (
          <MenuItem key={String(choice)} value={choice}>{String(choice)}</MenuItem>
        ))}
      </TextField>
    );
  }

  return (
    <TextField
      {...sharedProps}
      type="number"
      defaultValue={feature.default ?? ''}
      inputProps={{
        step: 'any',
        min: feature.minimum ?? undefined,
        max: feature.maximum ?? undefined,
      }}
      helperText={
        feature.minimum !== null && feature.maximum !== null
          ? `Accepted model range: ${feature.minimum} to ${feature.maximum}`
          : undefined
      }
    />
  );
}

const cleanText = (value: unknown, fallback = 'Not Available') => {
  if (value === null || value === undefined || value === '') return fallback;
  return String(value).replace(/_/g, ' ');
};

const formatPercent = (value: unknown, digits = 1) => {
  const numberValue = Number(value);
  if (!Number.isFinite(numberValue)) return 'Not Available';
  const percent = numberValue <= 1 ? numberValue * 100 : numberValue;
  return `${percent.toFixed(digits)}%`;
};

const formatDateTime = (value: unknown) => {
  if (!value) return 'Not Available';
  const raw = String(value);
  const utcValue = /(?:z|[+-]\d{2}:?\d{2})$/i.test(raw) ? raw : `${raw}Z`;
  const date = new Date(utcValue);
  if (Number.isNaN(date.getTime())) return 'Not Available';
  return `${date.toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: true,
    timeZone: 'Asia/Kolkata',
  })} IST`;
};

const dteiDisplayLabel = (key: string) => (
  key === 'fidelity' ? 'Predictive Fidelity' : cleanText(key)
);

const confidenceExplanation = (confidence: number) => {
  if (confidence >= 0.8) return 'High model certainty for the submitted patient-specific data.';
  if (confidence >= 0.6) return 'Moderate certainty; clinician review should confirm the AI result.';
  return 'Low confidence usually means the patient-specific values are near the model decision boundary, input quality is limited, or the model is uncertain for this case.';
};

const metricValue = (value: unknown) => {
  if (typeof value === 'number') return value <= 1 ? formatPercent(value) : value.toFixed(3);
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  return cleanText(value);
};

const compactHash = (value: unknown) => {
  const text = cleanText(value, '');
  if (!text) return 'Not Available';
  if (text.length <= 18) return text;
  return `${text.slice(0, 8)}...${text.slice(-6)}`;
};

const attackStability = (adversarial?: AnyRecord) => {
  const score = Number(adversarial?.robustness_score ?? adversarial?.score ?? adversarial?.stability_score);
  if (!Number.isFinite(score)) {
    return {
      label: 'Not Evaluated',
      detail: 'No adversarial robustness score was returned for this model run.',
      severity: 'slate',
      score: null as number | null,
    };
  }
  if (score >= 0.75) {
    return {
      label: 'Stable',
      detail: 'Prediction remained reliable under the configured adversarial checks.',
      severity: 'emerald',
      score,
    };
  }
  if (score >= 0.55) {
    return {
      label: 'Needs Clinical Review',
      detail: 'Robustness is moderate, so doctor review should verify the decision before final use.',
      severity: 'amber',
      score,
    };
  }
  return {
    label: 'Unstable',
    detail: 'Adversarial testing found a material prediction stability risk.',
    severity: 'rose',
    score,
  };
};

const pickFeatureImportance = (explanation?: PredictionResult['explanation']) => {
  const shapImportance = explanation?.shap?.feature_importance;
  const limeImportance = explanation?.lime?.feature_importance;
  const source = Array.isArray(shapImportance) ? shapImportance : Array.isArray(limeImportance) ? limeImportance : [];
  return source.slice(0, 6).map((item: any, index: number) => ({
    name: cleanText(item?.feature ?? item?.name ?? `Factor ${index + 1}`),
    value: Number(item?.importance ?? item?.value ?? item?.weight ?? 0),
  }));
};

const hasUsefulPayload = (payload?: AnyRecord) => {
  if (!payload) return false;
  return Object.keys(payload).some((key) => payload[key] !== null && payload[key] !== undefined && payload[key] !== '');
};

export default function DiseaseDiagnosisPage() {
  const { diseaseKey = '' } = useParams();
  const role = useAppSelector((state) => state.auth.role);
  const [inputSpec, setInputSpec] = useState<DiseaseInputSpec | null>(null);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [supportingPdf, setSupportingPdf] = useState<File | null>(null);
  const [result, setResult] = useState<PredictionResult | null>(null);
  const [submittedCase, setSubmittedCase] = useState<SubmittedCase | null>(null);
  const [federated, setFederated] = useState<FederatedDashboard | null>(null);
  const [verification, setVerification] = useState<Record<string, unknown> | null>(null);
  const [doctorReview, setDoctorReview] = useState<DoctorReviewResult | null>(null);
  const [reviewDecision, setReviewDecision] = useState('Confirmed');
  const [reviewFinalDecision, setReviewFinalDecision] = useState('');
  const [reviewComments, setReviewComments] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [downloadingReport, setDownloadingReport] = useState(false);
  const [reviewSubmitting, setReviewSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const canDiagnose = role === 'DOCTOR' || role === 'PATIENT';
  const canVerify = role === 'DOCTOR';

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError('');
    setInputSpec(null);
    setImageFile(null);
    setSupportingPdf(null);
    setResult(null);
    setSubmittedCase(null);
    setDoctorReview(null);
    setReviewFinalDecision('');
    setReviewComments('');

    api.get<DiseaseInputSpec>(`/datasets/diseases/${diseaseKey}/features`, {
      signal: controller.signal,
      timeout: 60000,
    })
      .then((response) => setInputSpec(response.data))
      .catch((requestError) => {
        if (requestError?.code !== 'ERR_CANCELED') {
          const detail = requestError?.response?.data?.detail;
          setError(typeof detail === 'string' ? detail : 'This disease page could not be loaded.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [diseaseKey]);

  useEffect(() => {
    if (!canDiagnose) return;
    const controller = new AbortController();
    api.get<FederatedDashboard>('/federated/dashboard', {
      signal: controller.signal,
      timeout: 60000,
    })
      .then((response) => setFederated(response.data))
      .catch(() => setFederated(null));
    return () => controller.abort();
  }, [canDiagnose]);

  const chooseImage = (event: ChangeEvent<HTMLInputElement>) => {
    setImageFile(event.target.files?.[0] ?? null);
  };

  const choosePdf = (event: ChangeEvent<HTMLInputElement>) => {
    setSupportingPdf(event.target.files?.[0] ?? null);
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!inputSpec) return;

    setSubmitting(true);
    setError('');
    setResult(null);
    setVerification(null);
    setDoctorReview(null);
    const form = new FormData(event.currentTarget);

    try {
      const upload = new FormData();
      const patientName = String(form.get('patient_name') ?? '').trim();
      const patientEmail = String(form.get('patient_email') ?? '').trim();
      const doctorNotes = String(form.get('doctor_notes') ?? '').trim();
      upload.append('disease_key', inputSpec.key);
      upload.append('patient_name', patientName);
      upload.append('patient_email', patientEmail);
      upload.append('doctor_notes', doctorNotes);
      const patientId = String(form.get('patient_id') ?? '').trim();
      if (patientId) upload.append('patient_id', patientId);
      if (supportingPdf) upload.append('supporting_pdf', supportingPdf);

      let response;
      let submittedFeatures: SubmittedCase['features'] = {};
      if (inputSpec.input_mode === 'image') {
        if (!imageFile) throw new Error('Choose a medical image before running the diagnosis.');
        upload.append('image', imageFile);
        submittedFeatures = {
          image_filename: imageFile.name,
          image_size_kb: Math.ceil(imageFile.size / 1024),
          image_type: imageFile.type || 'medical image',
        };
        response = await api.post('/predictions/image', upload, { timeout: 120000 });
      } else {
        const features = Object.fromEntries(
          inputSpec.features.map((feature) => [
            feature.name,
            feature.input_type === 'category'
              ? form.get(`feature:${feature.name}`)
              : Number(form.get(`feature:${feature.name}`)),
          ]),
        );
        submittedFeatures = features as SubmittedCase['features'];
        upload.append('features_json', JSON.stringify(features));
        response = await api.post('/predictions/tabular', upload, { timeout: 120000 });
      }
      setSubmittedCase({
        patientName,
        patientEmail,
        patientId,
        doctorNotes,
        inputMode: inputSpec.input_mode,
        imageName: imageFile?.name,
        imageSizeKb: imageFile ? Math.ceil(imageFile.size / 1024) : undefined,
        supportingPdfName: supportingPdf?.name,
        features: submittedFeatures,
      });
      setResult(response.data);
      setReviewDecision('Confirmed');
      setReviewFinalDecision(response.data?.prediction ? cleanText(response.data.prediction) : '');
      setReviewComments('');
    } catch (requestError: any) {
      const detail = requestError?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : requestError?.message || 'Diagnosis failed.');
    } finally {
      setSubmitting(false);
    }
  };

  const downloadFile = async (path: string, filename: string) => {
    setDownloadingReport(true);
    setError('');
    setSuccess('');
    try {
      const response = await api.get(path, { responseType: 'blob', timeout: 120000 });
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = filename;
      anchor.click();
      URL.revokeObjectURL(url);
      setSuccess('PDF report downloaded successfully.');
    } catch (requestError: any) {
      const detail = requestError?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'The report could not be downloaded.');
    } finally {
      setDownloadingReport(false);
    }
  };

  const verifyBlockchain = async () => {
    if (!result) return;
    try {
      const response = await api.get(`/blockchain/verify/${result.diagnosis_id}`);
      setVerification(response.data);
    } catch {
      setError('Blockchain verification could not be completed.');
    }
  };

  const submitDoctorReview = async () => {
    if (!result) return;
    const confirmed = window.confirm(
      [
        'You are about to finalize this clinical review.',
        '',
        `AI Prediction: ${cleanText(result.prediction)}`,
        `Doctor Decision: ${reviewDecision}`,
        '',
        'After submission, this action will be recorded in the audit trail.',
      ].join('\n'),
    );
    if (!confirmed) return;

    setReviewSubmitting(true);
    setError('');
    setSuccess('');
    try {
      const response = await api.post(`/doctors/diagnoses/${result.diagnosis_id}/finalize`, {
        doctor_decision: reviewDecision,
        final_clinical_decision: reviewFinalDecision.trim() || cleanText(result.prediction),
        review_notes: reviewComments.trim() || 'Reviewed from diagnosis result dashboard.',
        review_status: reviewDecision === 'Rejected' ? 'rejected' : 'reviewed',
      });
      setDoctorReview(response.data);
      setSuccess('Doctor review finalized and recorded in the audit trail.');
    } catch (requestError: any) {
      const detail = requestError?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Doctor review could not be finalized.');
    } finally {
      setReviewSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-[#f7fbfa]">
        <Header />
        <main className="mx-auto flex max-w-7xl items-center gap-3 px-4 py-16">
          <CircularProgress size={28} />
          <span>Loading disease workflow...</span>
        </main>
      </div>
    );
  }

  if (!inputSpec) {
    return (
      <div className="min-h-screen bg-[#f7fbfa]">
        <Header />
        <main className="mx-auto max-w-3xl px-4 py-12">
          <Alert severity="error">{error || 'Disease not found.'}</Alert>
          <Button className="mt-5" component={Link} to="/diagnosis" startIcon={<ArrowBackIcon />}>
            Back to disease pages
          </Button>
        </main>
      </div>
    );
  }

  const isImageDisease = inputSpec.input_mode === 'image';
  const localLedger = result?.blockchain_status?.local_ledger;
  const ethereumVerified = result?.blockchain_status?.ethereum?.verified === true;
  const localLedgerVerified = localLedger?.verified === true;
  const blockchainStatus = ethereumVerified
    ? 'Verified'
    : localLedgerVerified
      ? 'Verified'
      : cleanText(
          result?.blockchain_status?.status
            ?? result?.blockchain_status?.ethereum?.status
            ?? result?.blockchain_status?.fabric?.status
            ?? localLedger?.status,
          'Pending',
        );
  const blockchainConfirmed = ['verified', 'anchored', 'confirmed', 'success'].some((status) => (
    blockchainStatus.toLowerCase().includes(status)
  )) || result?.blockchain_status?.verified === true || localLedgerVerified;
  const transactionId = result?.fabric_tx_id
    ?? result?.blockchain_status?.fabric?.tx_id
    ?? result?.ethereum_tx_hash
    ?? result?.blockchain_status?.ethereum?.tx_hash
    ?? localLedger?.tx_id;
  const transactionHash = result?.ethereum_tx_hash
    ?? result?.blockchain_status?.ethereum?.tx_hash
    ?? localLedger?.block_hash
    ?? result?.blockchain_hash;
  const blockNumber = result?.blockchain_status?.ethereum?.block_number ?? localLedger?.block_number;
  const networkName = cleanText(
    result?.blockchain_status?.network
      ?? result?.blockchain_status?.ethereum?.network
      ?? result?.blockchain_status?.fabric?.network
      ?? result?.blockchain_status?.fabric?.channel
      ?? localLedger?.network
      ?? 'TrustMedAI-Chain',
  );
  const consensusStatus = cleanText(
    result?.blockchain_status?.consensus
      ?? result?.blockchain_status?.fabric?.consensus
      ?? localLedger?.consensus
      ?? (blockchainConfirmed ? 'Verified' : 'Pending'),
  );
  const ledgerTimestamp = result?.blockchain_status?.fabric?.anchor?.timestamp ?? localLedger?.timestamp ?? result?.created_at;
  const trustScoreValue = Number(result?.trust_score ?? 0);
  const dteiStatus = cleanText(
    result?.metrics?.dtei?.status
      ?? (trustScoreValue >= 0.8
        ? 'High Trust'
        : trustScoreValue >= 0.6
          ? 'Moderate Trust'
          : trustScoreValue >= 0.4
            ? 'Low Trust'
            : 'Critical Review Required'),
  );
  const fairnessValue = Number(
    result?.metrics?.fairness
      ?? result?.metrics?.fairness_score
      ?? result?.dtei_components?.fairness
      ?? result?.dtei_components?.compliance,
  );
  const explanationMethods = result
    ? [
        { name: 'Grad-CAM', payload: result.explanation?.gradcam, bestFor: 'Image model heatmap' },
        { name: 'Integrated Gradients', payload: result.explanation?.integrated_gradients, bestFor: 'Image attribution' },
        { name: 'SHAP', payload: result.explanation?.shap, bestFor: 'Feature contribution' },
        { name: 'LIME', payload: result.explanation?.lime, bestFor: 'Local explanation' },
      ]
    : [];
  const hasExplainability = explanationMethods.some((method) => hasUsefulPayload(method.payload));
  const governanceRows = [
    ['Transparency', hasExplainability ? 'Passed' : 'Pending Explanation Payload'],
    ['Accountability', result?.diagnosis_id && result?.blockchain_hash ? 'Passed' : 'Pending'],
    ['Reproducibility', inputSpec.model_info?.selected_model ? 'Passed' : 'Pending Model Metadata'],
    ['Fairness', Number.isFinite(fairnessValue) ? formatPercent(fairnessValue) : 'Not Available'],
    ['Auditability', blockchainConfirmed || result?.blockchain_hash ? 'Verified' : 'Pending'],
  ];
  const ledgerRows = [
    ['Block Number', blockNumber],
    ['Transaction ID', transactionId],
    ['Network', networkName],
    ['Consensus', consensusStatus],
    ['Timestamp', ledgerTimestamp],
    ['Diagnosis Record', result?.blockchain_hash ? 'Verified' : 'Pending'],
    ['Blockchain Status', blockchainConfirmed ? 'Confirmed' : blockchainStatus],
    ['Ledger Status', result?.blockchain_hash ? cleanText(result?.blockchain_status?.ledger_status ?? localLedger?.ledger_status, 'Immutable') : 'Pending'],
  ];
  const dteiRows = Object.entries(result?.dtei_components ?? {}).map(([key, value]) => ({
    key,
    label: dteiDisplayLabel(key),
    value: Number(value),
  }));
  const dteiWeightRows = Object.entries(result?.metrics?.dtei?.weights ?? {
    fidelity: 0.3,
    interpretability: 0.2,
    robustness: 0.2,
    blockchain_integrity: 0.15,
    compliance: 0.15,
  }).map(([key, value]) => ({
    key,
    label: dteiDisplayLabel(key),
    value: Number(value),
  }));
  const attackSummary = attackStability(result?.adversarial);
  const activeFederatedRound = federated?.active_round ?? null;
  const globalTrustValue = Number(
    federated?.cifts?.trust_synchronization
      || federated?.consensus_reliability
      || federated?.cifts?.hospital_reputation
      || 0,
  );
  const federatedRows = [
    ['Federated Status', federated?.mode ? 'Active' : 'Unavailable'],
    ['Privacy Mode', federated?.architecture?.privacy ? 'Protected' : 'Not Available'],
    ['Raw Data Sharing', federated?.architecture?.raw_data_shared === false ? 'Not Required' : 'Not Available'],
    ['Current Training Round', Number(activeFederatedRound?.round_number ?? federated?.model_weight_round ?? 0) > 0 ? `Round ${activeFederatedRound?.round_number ?? federated?.model_weight_round}` : 'No Active Round'],
    ['Participating Clients', activeFederatedRound?.submitted_clients ?? federated?.nodes?.length ?? 'Not Available'],
    ['Aggregation Method', activeFederatedRound?.strategy ?? federated?.architecture?.strategy ?? 'FedAvg'],
    ['Global Model', activeFederatedRound?.status === 'aggregated' || activeFederatedRound?.update_hash ? 'Updated' : cleanText(activeFederatedRound?.status, 'Initializing')],
  ];
  const trustSyncRows = [
    ['Trust Sync Status', globalTrustValue > 0 ? 'Synchronized' : 'Pending'],
    ['Global Trust State', globalTrustValue > 0 ? formatPercent(globalTrustValue) : 'Not Available'],
    ['Local Diagnosis DTEI', formatPercent(result?.trust_score)],
  ];
  const federatedComponentRows = (dteiRows.length ? dteiRows : [
    { key: 'fidelity', label: 'Predictive Fidelity', value: result?.confidence ?? 0 },
    { key: 'interpretability', label: 'Interpretability', value: result?.aecs ?? 0 },
    { key: 'robustness', label: 'Robustness', value: attackSummary.score ?? 0 },
    { key: 'blockchain_integrity', label: 'Blockchain Integrity', value: blockchainConfirmed ? 1 : 0 },
    { key: 'compliance', label: 'Compliance', value: Number(result?.dtei_components?.compliance ?? 0) },
  ]).filter((item) => ['fidelity', 'interpretability', 'robustness', 'blockchain_integrity', 'compliance'].includes(item.key));
  const federatedLastSync = activeFederatedRound?.completed_at
    ?? activeFederatedRound?.created_at
    ?? ledgerTimestamp
    ?? result?.created_at;
  const featureImportance = pickFeatureImportance(result?.explanation);
  const adversarialRows = Object.entries(result?.adversarial ?? {})
    .filter(([, value]) => typeof value !== 'object' || value === null)
    .slice(0, 8);
  const metricRows = Object.entries(result?.metrics ?? {})
    .filter(([, value]) => typeof value !== 'object' || value === null)
    .slice(0, 8);
  const attackStatusClass = attackSummary.severity === 'emerald'
    ? 'border-emerald-200 bg-emerald-50 text-emerald-800'
    : attackSummary.severity === 'amber'
      ? 'border-amber-200 bg-amber-50 text-amber-800'
      : attackSummary.severity === 'rose'
        ? 'border-rose-200 bg-rose-50 text-rose-800'
        : 'border-slate-200 bg-slate-50 text-slate-700';
  const patientRows = submittedCase
    ? [
        ['Full Name', submittedCase.patientName],
        ['Patient ID', submittedCase.patientId || result?.diagnosis_id],
        ['Email', submittedCase.patientEmail],
        ['Clinical Notes', submittedCase.doctorNotes],
      ]
    : [];
  const inputRows = submittedCase ? Object.entries(submittedCase.features).slice(0, 12) : [];

  return (
    <div className="min-h-screen bg-[#f7fbfa]">
      <Header />
      <main className="mx-auto max-w-6xl px-4 py-8">
        <Button component={Link} to="/diagnosis" startIcon={<ArrowBackIcon />}>
          All disease pages
        </Button>

        <header className="mt-4 rounded border border-teal-900/10 bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-sm font-bold uppercase tracking-[0.16em] text-trust-teal">
                {isImageDisease ? 'Image-based diagnosis' : 'Clinical / tabular diagnosis'}
              </p>
              <h1 className="mt-2 text-4xl font-black text-trust-ink">{inputSpec.name}</h1>
              <p className="mt-2 text-slate-600">{inputSpec.dataset}</p>
            </div>
            <span className="grid h-14 w-14 place-items-center rounded bg-teal-50 text-trust-teal">
              {isImageDisease ? <ImageSearchIcon fontSize="large" /> : <MonitorHeartIcon fontSize="large" />}
            </span>
          </div>
        </header>

        {error && <Alert className="mt-5" severity="error">{error}</Alert>}
        {success && <Alert className="mt-5" severity="success" onClose={() => setSuccess('')}>{success}</Alert>}
        {!canDiagnose && (
          <Alert className="mt-5" severity="info">
            This page is available only to doctors and patients. Administrators manage the system and cannot run predictions.
          </Alert>
        )}

        <form onSubmit={submit} className="mt-6 grid gap-6">
          <fieldset className="rounded border border-slate-200 bg-white p-6 shadow-sm">
            <legend className="px-2 text-xl font-black text-trust-ink">1. Patient Personal Information</legend>
            <p className="mb-5 text-sm text-slate-600">
              Fill in the patient identity before entering disease data.
            </p>
            <div className="grid gap-4 md:grid-cols-2">
              <TextField name="patient_name" label="Patient full name" required disabled={!canDiagnose} />
              <TextField name="patient_email" label="Patient email" type="email" required disabled={!canDiagnose} />
              <TextField
                name="patient_id"
                label="Patient user ID (optional)"
                helperText="Use when the patient already has a platform account."
                disabled={!canDiagnose}
              />
              <TextField
                name="doctor_notes"
                label="Clinical notes"
                multiline
                minRows={3}
                defaultValue={`Assessment for ${inputSpec.name}.`}
                disabled={!canDiagnose}
              />
            </div>
          </fieldset>

          <fieldset className="rounded border border-slate-200 bg-white p-6 shadow-sm">
            <legend className="px-2 text-xl font-black text-trust-ink">
              2. {inputSpec.name} {isImageDisease ? 'Medical Image' : 'Clinical Inputs'}
            </legend>

            {inputSpec.model_info?.selected_model && (
              <div className="mb-5 rounded border border-teal-100 bg-teal-50 p-4 text-sm text-teal-900">
                <strong>Active model:</strong> {inputSpec.model_info.selected_model.replace(/_/g, ' ')}
              </div>
            )}

            {inputSpec.model_info?.deployment_status === 'blocked_low_quality' && (
              <Alert className="mb-5" severity="warning">
                This model is disabled because its current validation quality is insufficient.
              </Alert>
            )}

            {isImageDisease ? (
              <div className="grid gap-5 md:grid-cols-[1fr_300px]">
                <div className="rounded border-2 border-dashed border-teal-200 bg-teal-50/40 p-8 text-center">
                  <CloudUploadIcon className="text-trust-teal" sx={{ fontSize: 48 }} />
                  <h2 className="mt-3 text-lg font-black">Upload {inputSpec.name} Image</h2>
                  <p className="mt-2 text-sm leading-6 text-slate-600">
                    JPEG, PNG, or WebP, up to 10 MB. Use the correct clinical image type for this disease.
                  </p>
                  <Button className="mt-5" component="label" variant="contained" disabled={!canDiagnose}>
                    Select Medical Image
                    <input
                      hidden
                      type="file"
                      accept="image/jpeg,image/png,image/webp"
                      onChange={chooseImage}
                    />
                  </Button>
                </div>
                <div className="rounded border border-slate-200 bg-slate-50 p-5">
                  <p className="text-sm font-bold uppercase tracking-wide text-slate-500">Selected image</p>
                  <p className="mt-3 break-words font-semibold text-trust-teal">
                    {imageFile?.name ?? 'No image selected'}
                  </p>
                  <p className="mt-2 text-sm text-slate-500">
                    {imageFile ? `${Math.ceil(imageFile.size / 1024)} KB` : 'Choose an image to enable diagnosis.'}
                  </p>
                </div>
              </div>
            ) : (
              <>
                <Alert className="mb-5" severity="info">
                  This model requires {inputSpec.features.length} disease-specific values.
                </Alert>
                <div className="grid gap-4 md:grid-cols-2">
                  {inputSpec.features.map((feature) => (
                    <FeatureInput
                      key={`${inputSpec.key}:${feature.name}`}
                      feature={feature}
                      disabled={!canDiagnose}
                    />
                  ))}
                </div>
              </>
            )}
          </fieldset>

          <fieldset className="rounded border border-slate-200 bg-white p-6 shadow-sm">
            <legend className="px-2 text-xl font-black text-trust-ink">3. Supporting Report</legend>
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <p className="font-semibold">Optional medical report PDF</p>
                <p className="mt-1 text-sm text-slate-500">Maximum file size: 15 MB.</p>
                {supportingPdf && <p className="mt-2 text-sm font-semibold text-trust-teal">{supportingPdf.name}</p>}
              </div>
              <Button component="label" variant="outlined" startIcon={<DescriptionIcon />} disabled={!canDiagnose}>
                Select PDF
                <input hidden type="file" accept="application/pdf" onChange={choosePdf} />
              </Button>
            </div>
          </fieldset>

          <Button
            type="submit"
            variant="contained"
            size="large"
            disabled={
              !canDiagnose ||
              submitting ||
              !inputSpec.model_available ||
              (!isImageDisease && inputSpec.features.length === 0) ||
              (isImageDisease && !imageFile)
            }
          >
            {submitting ? 'Running diagnosis...' : `Run ${inputSpec.name} Diagnosis`}
          </Button>
        </form>

        {result && (
          <section className="mt-8 space-y-6" aria-labelledby="diagnosis-result">
            <div className="rounded border border-teal-900/10 bg-white p-6 shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-bold uppercase tracking-[0.16em] text-trust-teal">Completed diagnosis</p>
                  <h2 id="diagnosis-result" className="mt-1 text-3xl font-black text-trust-ink">
                    AI-Powered Multi-Disease Result Dashboard
                  </h2>
                  <p className="mt-2 text-sm text-slate-600">
                    Diagnosis ID: <span className="font-semibold">{result.diagnosis_id}</span> |
                    Generated: <span className="font-semibold">{formatDateTime(result.created_at)}</span>
                  </p>
                </div>
                <span className="grid h-14 w-14 place-items-center rounded border border-teal-100 bg-teal-50 text-trust-teal">
                  <VerifiedUserIcon color={ethereumVerified ? 'success' : 'disabled'} fontSize="large" />
                </span>
              </div>

              <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-5">
                {[
                  ['Disease Detected Name', inputSpec.name],
                  ['AI Prediction', cleanText(result.prediction)],
                  ['Confidence', formatPercent(result.confidence)],
                  ['Trust Score', formatPercent(result.trust_score)],
                  ['DTEI Status', dteiStatus],
                ].map(([label, value]) => (
                  <div key={label} className="rounded border border-slate-200 bg-slate-50 p-4">
                    <p className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</p>
                    <p className="mt-2 break-words text-2xl font-black capitalize text-trust-ink">{value}</p>
                  </div>
                ))}
              </div>
              <LinearProgress className="mt-5" variant="determinate" value={Math.min(100, Math.max(0, result.confidence * 100))} />
              <p className="mt-3 rounded bg-slate-50 p-3 text-sm leading-6 text-slate-600">
                <span className="font-bold text-trust-ink">Confidence note:</span> {confidenceExplanation(result.confidence)}
              </p>
            </div>

            <section className="rounded border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-bold uppercase tracking-[0.16em] text-trust-teal">
                    Governance & Compliance Validation
                  </p>
                  <h3 className="mt-1 text-2xl font-black text-trust-ink">Governance Validation</h3>
                  <p className="mt-2 text-sm text-slate-600">
                    Compliance checks, auditability, and ledger confirmation for this exact diagnosis record.
                  </p>
                </div>
                <span className={`rounded px-3 py-2 text-sm font-black ${blockchainConfirmed ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
                  {blockchainConfirmed ? 'Confirmed' : 'Pending'}
                </span>
              </div>

              <div className="mt-5 grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
                <div className="rounded border border-slate-100 bg-slate-50 p-4">
                  <h4 className="font-black text-slate-800">Validation Checks</h4>
                  <div className="mt-4 grid gap-3">
                    {governanceRows.map(([label, value]) => (
                      <div key={label} className="flex items-center justify-between gap-4 rounded bg-white p-3">
                        <span className="text-sm font-bold text-slate-600">{label}</span>
                        <span className="text-sm font-black text-trust-teal">{cleanText(value)}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="rounded border border-slate-100 bg-slate-50 p-4">
                  <h4 className="font-black text-slate-800">Blockchain Ledger Proof</h4>
                  <div className="mt-4 grid gap-3 sm:grid-cols-2">
                    {ledgerRows.map(([label, value]) => (
                      <div key={label} className="rounded bg-white p-3">
                        <p className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</p>
                        <p className="mt-1 break-words text-sm font-semibold text-slate-800">
                          {label === 'Timestamp' ? formatDateTime(value) : cleanText(value)}
                        </p>
                      </div>
                    ))}
                  </div>
                  <div className="mt-4 rounded border border-teal-100 bg-teal-50 p-4">
                    <p className="text-xs font-bold uppercase tracking-wide text-teal-700">Transaction Hash</p>
                    <p className="mt-2 break-all text-lg font-black text-trust-ink">{compactHash(transactionHash)}</p>
                    <p className="mt-2 break-all text-xs text-slate-600">{cleanText(transactionHash)}</p>
                  </div>
                </div>
              </div>
            </section>

            <div className="grid gap-6 xl:grid-cols-[1fr_1.2fr]">
              <section className="rounded border border-slate-200 bg-white p-6 shadow-sm">
                <h3 className="text-xl font-black text-trust-ink">Patient Details</h3>
                <div className="mt-4 grid gap-3">
                  {patientRows.map(([label, value]) => (
                    <div key={label} className="rounded bg-slate-50 p-3">
                      <p className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</p>
                      <p className="mt-1 break-words text-sm font-semibold text-slate-800">{cleanText(value)}</p>
                    </div>
                  ))}
                </div>
              </section>

              <section className="rounded border border-slate-200 bg-white p-6 shadow-sm">
                <h3 className="text-xl font-black text-trust-ink">Medical Input Data</h3>
                <p className="mt-1 text-sm text-slate-500">
                  Actual values submitted to the diagnosis API for this run.
                </p>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  {inputRows.map(([label, value]) => (
                    <div key={label} className="rounded bg-slate-50 p-3">
                      <p className="text-xs font-bold uppercase tracking-wide text-slate-500">{cleanText(label)}</p>
                      <p className="mt-1 break-words text-sm font-semibold text-slate-800">{cleanText(value)}</p>
                    </div>
                  ))}
                  {submittedCase?.supportingPdfName && (
                    <div className="rounded bg-slate-50 p-3">
                      <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Supporting PDF</p>
                      <p className="mt-1 break-words text-sm font-semibold text-slate-800">{submittedCase.supportingPdfName}</p>
                    </div>
                  )}
                </div>
              </section>
            </div>

            <div className="grid gap-6 xl:grid-cols-3">
              <section className="rounded border border-slate-200 bg-white p-6 shadow-sm xl:col-span-2">
                <h3 className="text-xl font-black text-trust-ink">Dynamic Trust Evolution</h3>
                <p className="mt-1 text-sm text-slate-500">
                  DTEI combines prediction performance, explanation reliability, robustness, blockchain integrity, and governance signals.
                </p>
                <div className="mt-4 rounded border border-teal-100 bg-teal-50 p-4">
                  <p className="text-sm font-bold uppercase tracking-wide text-teal-700">DTEI Calculation</p>
                  <p className="mt-1 text-sm font-semibold text-trust-ink">
                    DTEI = alpha*F + beta*I + gamma*R + delta*B + lambda*C
                  </p>
                  <p className="mt-2 text-sm text-slate-600">
                    Status: <span className="font-black text-trust-teal">{dteiStatus}</span>
                  </p>
                  <div className="mt-3 grid gap-2 sm:grid-cols-5">
                    {dteiWeightRows.map((weight) => (
                      <div key={weight.key} className="rounded bg-white p-2 text-center">
                        <p className="text-[11px] font-bold uppercase text-slate-500">{weight.label}</p>
                        <p className="text-sm font-black text-trust-ink">{weight.value.toFixed(2)}</p>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="mt-5 grid gap-4 md:grid-cols-2">
                  {(dteiRows.length ? dteiRows : [
                    { key: 'fidelity', label: 'Predictive Fidelity', value: result.confidence },
                    { key: 'robustness', label: 'Robustness', value: attackSummary.score ?? 0 },
                    { key: 'blockchain_integrity', label: 'Blockchain Integrity', value: ethereumVerified ? 1 : 0 },
                    { key: 'doctor_feedback', label: 'Doctor Feedback', value: doctorReview ? 1 : 0 },
                  ]).map((item) => (
                    <div key={item.key} className="rounded border border-slate-100 p-4">
                      <div className="flex items-center justify-between gap-3">
                        <p className="font-bold capitalize text-slate-700">{item.label}</p>
                        <span className="text-sm font-black text-trust-teal">{formatPercent(item.value)}</span>
                      </div>
                      {item.key === 'fidelity' && (
                        <p className="mt-2 text-xs leading-5 text-slate-500">
                          This value is currently calculated from this patient's prediction confidence.
                        </p>
                      )}
                      <LinearProgress className="mt-3" variant="determinate" value={Math.min(100, Math.max(0, item.value * 100))} />
                    </div>
                  ))}
                </div>
              </section>

              <section className="rounded border border-slate-200 bg-white p-6 shadow-sm">
                <h3 className="text-xl font-black text-trust-ink">AECS</h3>
                <p className="mt-1 text-sm text-slate-500">Adversarial Explanation Consistency Score.</p>
                <p className="mt-5 text-5xl font-black text-trust-teal">{formatPercent(result.aecs)}</p>
                <p className="mt-3 text-sm text-slate-600">
                  Compares explanation stability before and after attack simulation.
                </p>
              </section>
            </div>

            <section className="rounded border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-bold uppercase tracking-[0.16em] text-trust-teal">
                    Federated Learning & Trust Synchronization
                  </p>
                  <h3 className="mt-1 text-2xl font-black text-trust-ink">Cross-Institutional Trust Synchronization</h3>
                  <p className="mt-2 text-sm text-slate-600">
                    Uses the federated coordinator dashboard plus this diagnosis DTEI. Raw patient data is not shared.
                  </p>
                </div>
                <span className={`rounded px-3 py-2 text-sm font-black ${federated?.mode ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>
                  {federated?.mode ? 'Active' : 'Unavailable'}
                </span>
              </div>

              <div className="mt-5 grid gap-6 lg:grid-cols-2">
                <div className="rounded border border-slate-100 bg-slate-50 p-4">
                  <h4 className="font-black text-slate-800">Federated Learning Status</h4>
                  <div className="mt-4 grid gap-3">
                    {federatedRows.map(([label, value]) => (
                      <div key={label} className="flex items-center justify-between gap-4 rounded bg-white p-3">
                        <span className="text-sm font-bold text-slate-600">{label}</span>
                        <span className="text-right text-sm font-black text-trust-ink">{cleanText(value)}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="rounded border border-slate-100 bg-slate-50 p-4">
                  <h4 className="font-black text-slate-800">Cross-Institutional Trust Synchronization</h4>
                  <div className="mt-4 grid gap-3">
                    {trustSyncRows.map(([label, value]) => (
                      <div key={label} className="flex items-center justify-between gap-4 rounded bg-white p-3">
                        <span className="text-sm font-bold text-slate-600">{label}</span>
                        <span className="text-right text-sm font-black text-trust-teal">{cleanText(value)}</span>
                      </div>
                    ))}
                  </div>
                  <div className="mt-4 grid gap-2 sm:grid-cols-2">
                    {federatedComponentRows.map((item) => (
                      <div key={item.key} className="flex items-center gap-2 rounded bg-white p-3">
                        <span className="grid h-5 w-5 place-items-center rounded-full bg-emerald-100 text-[10px] font-black text-emerald-700">OK</span>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-bold text-slate-700">{item.label}</p>
                          <LinearProgress className="mt-2" variant="determinate" value={Math.min(100, Math.max(0, item.value * 100))} />
                        </div>
                        <span className="text-xs font-black text-trust-teal">{formatPercent(item.value)}</span>
                      </div>
                    ))}
                  </div>
                  <p className="mt-4 text-sm text-slate-600">
                    Last Sync: <span className="font-bold text-trust-ink">{formatDateTime(federatedLastSync)}</span>
                  </p>
                </div>
              </div>
            </section>

            <div className="grid gap-6 xl:grid-cols-2">
              <section className="rounded border border-slate-200 bg-white p-6 shadow-sm">
                <h3 className="text-xl font-black text-trust-ink">Explainability Generation</h3>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  {explanationMethods.map((method) => (
                    <div key={method.name} className="rounded border border-slate-100 bg-slate-50 p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="font-black text-slate-800">{method.name}</p>
                          <p className="mt-1 text-xs text-slate-500">{method.bestFor}</p>
                        </div>
                        <span className={`rounded px-2 py-1 text-xs font-bold ${hasUsefulPayload(method.payload) ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-200 text-slate-600'}`}>
                          {hasUsefulPayload(method.payload) ? 'Generated' : 'Not Available'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="mt-5 rounded bg-slate-50 p-4">
                  <p className="font-bold text-slate-800">Important contributing factors</p>
                  {featureImportance.length ? (
                    <div className="mt-3 space-y-3">
                      {featureImportance.map((item) => (
                        <div key={item.name}>
                          <div className="flex justify-between gap-4 text-sm">
                            <span className="capitalize text-slate-700">{item.name}</span>
                            <span className="font-bold text-trust-teal">{metricValue(item.value)}</span>
                          </div>
                          <LinearProgress className="mt-1" variant="determinate" value={Math.min(100, Math.abs(item.value) * 100)} />
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="mt-2 text-sm text-slate-500">No feature-importance payload was returned for this model run.</p>
                  )}
                </div>
              </section>

              <section className="rounded border border-slate-200 bg-white p-6 shadow-sm">
                <h3 className="text-xl font-black text-trust-ink">Adversarial Attacks</h3>
                <div className={`mt-4 rounded border p-4 ${attackStatusClass}`}>
                  <p className="text-sm font-bold uppercase tracking-wide">Disease stability status</p>
                  <p className="mt-1 text-3xl font-black">{attackSummary.label}</p>
                  <p className="mt-2 text-sm">{attackSummary.detail}</p>
                </div>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  {adversarialRows.length ? adversarialRows.map(([label, value]) => (
                    <div key={label} className="rounded bg-slate-50 p-3">
                      <p className="text-xs font-bold uppercase tracking-wide text-slate-500">{cleanText(label)}</p>
                      <p className="mt-1 font-semibold text-slate-800">{metricValue(value)}</p>
                    </div>
                  )) : (
                    <p className="text-sm text-slate-500">FGSM, PGD, Gaussian noise, and poisoning metrics were not returned for this run.</p>
                  )}
                </div>
              </section>
            </div>

            <div className="grid gap-6 xl:grid-cols-2">
              <section className="rounded border border-slate-200 bg-white p-6 shadow-sm">
                <h3 className="text-xl font-black text-trust-ink">Blockchain Trust Ledger</h3>
                <div className="mt-4 grid gap-3">
                  {[
                    ['Verification Status', blockchainStatus],
                    ['Blockchain Hash', result.blockchain_hash],
                    ['Ethereum Tx Hash', result.ethereum_tx_hash ?? result.blockchain_status?.ethereum?.tx_hash],
                    ['Fabric Tx ID', result.fabric_tx_id ?? result.blockchain_status?.fabric?.tx_id],
                  ].map(([label, value]) => (
                    <div key={label} className="rounded bg-slate-50 p-3">
                      <p className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</p>
                      <p className="mt-1 break-all text-sm font-semibold text-slate-800">{cleanText(value)}</p>
                    </div>
                  ))}
                </div>
                <div className="mt-5 flex flex-wrap gap-3">
                  {canVerify && (
                    <Button variant="outlined" onClick={verifyBlockchain}>
                      Verify Blockchain
                    </Button>
                  )}
                </div>
                {verification && (
                  <Alert className="mt-4" severity={verification.verified ? 'success' : 'warning'}>
                    Blockchain verification {verification.verified ? 'passed' : 'did not pass'}.
                  </Alert>
                )}
              </section>

              <section className="rounded border border-slate-200 bg-white p-6 shadow-sm">
                <h3 className="text-xl font-black text-trust-ink">Governance + Federated Trust</h3>
                <div className="mt-4 grid gap-3">
                  {[
                    ['Active Model', inputSpec.model_info?.selected_model],
                    ['Model Version', inputSpec.model_info?.artifact_version],
                    ['Input Modality', result.input_modality ?? submittedCase?.inputMode],
                    ['Federated Status', 'Hospital collaboration enabled without raw patient data sharing'],
                    ['Governance State', blockchainStatus === 'Verified' ? 'Ledger integrity verified' : 'Ledger verification pending'],
                  ].map(([label, value]) => (
                    <div key={label} className="rounded bg-slate-50 p-3">
                      <p className="text-xs font-bold uppercase tracking-wide text-slate-500">{label}</p>
                      <p className="mt-1 text-sm font-semibold text-slate-800">{cleanText(value)}</p>
                    </div>
                  ))}
                </div>
                {metricRows.length > 0 && (
                  <div className="mt-5">
                    <p className="font-bold text-slate-800">Model evaluation metrics</p>
                    <div className="mt-3 grid gap-3 sm:grid-cols-2">
                      {metricRows.map(([label, value]) => (
                        <div key={label} className="rounded bg-slate-50 p-3">
                          <p className="text-xs font-bold uppercase tracking-wide text-slate-500">{cleanText(label)}</p>
                          <p className="mt-1 font-semibold text-slate-800">{metricValue(value)}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </section>
            </div>

            <section className="rounded border border-slate-200 bg-white p-6 shadow-sm">
              <h3 className="text-xl font-black text-trust-ink">Doctor Reviews AI Result</h3>
              {role === 'DOCTOR' ? (
                <div className="mt-4 grid gap-4 md:grid-cols-[220px_1fr]">
                  <TextField
                    select
                    label="Doctor Decision"
                    value={reviewDecision}
                    onChange={(event) => setReviewDecision(event.target.value)}
                  >
                    {['Confirmed', 'Rejected', 'Overridden'].map((option) => (
                      <MenuItem key={option} value={option}>{option}</MenuItem>
                    ))}
                  </TextField>
                  <TextField
                    label="Final Clinical Decision"
                    value={reviewFinalDecision}
                    onChange={(event) => setReviewFinalDecision(event.target.value)}
                    placeholder="Enter final diagnosis decision"
                  />
                  <TextField
                    className="md:col-span-2"
                    label="Doctor Approves / Rejects / Comments"
                    multiline
                    minRows={4}
                    value={reviewComments}
                    onChange={(event) => setReviewComments(event.target.value)}
                    placeholder="Add clinical reasoning, follow-up steps, or rejection notes."
                  />
                  <div className="md:col-span-2 flex flex-wrap items-center gap-3">
                    <Button
                      variant="contained"
                      disabled={reviewSubmitting}
                      onClick={submitDoctorReview}
                      startIcon={reviewSubmitting ? <CircularProgress color="inherit" size={16} /> : undefined}
                    >
                      {reviewSubmitting ? 'Saving Review...' : 'Submit Final Clinical Decision'}
                    </Button>
                    {doctorReview && (
                      <span className="text-sm font-semibold text-emerald-700">
                        Review status: {cleanText(doctorReview.review_status)}
                      </span>
                    )}
                  </div>
                </div>
              ) : (
                <Alert className="mt-4" severity="info">
                  Doctor approval, rejection, comments, and final clinical decision will appear after a clinician reviews this diagnosis.
                </Alert>
              )}
            </section>

            <section className="rounded border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <h3 className="text-xl font-black text-trust-ink">Final Diagnosis Report</h3>
                  <p className="mt-1 text-sm text-slate-500">
                    Download a professional PDF report with patient details, AI prediction, explainability, blockchain integrity, and disclaimer.
                  </p>
                </div>
                <Button
                  variant="contained"
                  disabled={downloadingReport}
                  startIcon={downloadingReport ? <CircularProgress color="inherit" size={16} /> : <DescriptionIcon />}
                  onClick={() => downloadFile(
                    `/reports/${result.diagnosis_id}.pdf`,
                    `trustmedai-${result.diagnosis_id}.pdf`,
                  )}
                >
                  {downloadingReport ? 'Generating Report...' : 'Download PDF Report'}
                </Button>
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-3">
                {(result.artifacts ?? []).length ? result.artifacts.map((artifact) => (
                  <div key={artifact.id} className="rounded bg-slate-50 p-3">
                    <p className="text-xs font-bold uppercase tracking-wide text-slate-500">{cleanText(artifact.kind)}</p>
                    <p className="mt-1 break-words text-sm font-semibold text-slate-800">{artifact.original_filename}</p>
                    <p className="mt-1 text-xs text-slate-500">{Math.ceil(artifact.size_bytes / 1024)} KB</p>
                  </div>
                )) : (
                  <div className="rounded bg-slate-50 p-3">
                    <p className="text-sm text-slate-500">No uploaded artifacts are attached to this diagnosis.</p>
                  </div>
                )}
              </div>
            </section>
          </section>
        )}
      </main>
    </div>
  );
}
