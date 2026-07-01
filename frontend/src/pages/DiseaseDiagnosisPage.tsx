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
}

interface PredictionResult {
  diagnosis_id: string;
  disease_key: string;
  prediction: string;
  confidence: number;
  trust_score: number;
  aecs: number;
  blockchain_hash: string;
  blockchain_status: {
    ethereum?: {
      status?: string;
      verified?: boolean;
      tx_hash?: string;
    };
  };
  artifacts: DiagnosisArtifact[];
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

export default function DiseaseDiagnosisPage() {
  const { diseaseKey = '' } = useParams();
  const role = useAppSelector((state) => state.auth.role);
  const [inputSpec, setInputSpec] = useState<DiseaseInputSpec | null>(null);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [supportingPdf, setSupportingPdf] = useState<File | null>(null);
  const [result, setResult] = useState<PredictionResult | null>(null);
  const [verification, setVerification] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const canDiagnose = role === 'DOCTOR' || role === 'SUPER_ADMIN';
  const canVerify = role === 'DOCTOR' || role === 'SUPER_ADMIN' || role === 'HOSPITAL_ADMIN';

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError('');
    setInputSpec(null);
    setImageFile(null);
    setSupportingPdf(null);
    setResult(null);

    api.get<DiseaseInputSpec>(`/datasets/diseases/${diseaseKey}/features`, {
      signal: controller.signal,
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
    const form = new FormData(event.currentTarget);

    try {
      const upload = new FormData();
      upload.append('disease_key', inputSpec.key);
      upload.append('patient_name', String(form.get('patient_name') ?? ''));
      upload.append('patient_email', String(form.get('patient_email') ?? ''));
      upload.append('doctor_notes', String(form.get('doctor_notes') ?? ''));
      const patientId = String(form.get('patient_id') ?? '').trim();
      if (patientId) upload.append('patient_id', patientId);
      if (supportingPdf) upload.append('supporting_pdf', supportingPdf);

      let response;
      if (inputSpec.input_mode === 'image') {
        if (!imageFile) throw new Error('Choose a medical image before running the diagnosis.');
        upload.append('image', imageFile);
        response = await api.post('/predictions/image', upload);
      } else {
        const features = Object.fromEntries(
          inputSpec.features.map((feature) => [
            feature.name,
            feature.input_type === 'category'
              ? form.get(`feature:${feature.name}`)
              : Number(form.get(`feature:${feature.name}`)),
          ]),
        );
        upload.append('features_json', JSON.stringify(features));
        response = await api.post('/predictions/tabular', upload);
      }
      setResult(response.data);
    } catch (requestError: any) {
      const detail = requestError?.response?.data?.detail;
      setError(typeof detail === 'string' ? detail : requestError?.message || 'Diagnosis failed.');
    } finally {
      setSubmitting(false);
    }
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
      setError('The report could not be downloaded.');
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

  if (loading) {
    return (
      <div className="min-h-screen bg-[#f7fbfa]">
        <Header />
        <main className="mx-auto flex max-w-7xl items-center gap-3 px-4 py-16">
          <CircularProgress size={28} />
          <span>Loading disease workflow…</span>
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
  const ethereumVerified = result?.blockchain_status?.ethereum?.verified === true;

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
        {!canDiagnose && (
          <Alert className="mt-5" severity="info">
            This page is read-only for your role. Doctors and super administrators can submit diagnoses.
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
            {submitting ? 'Running diagnosis…' : `Run ${inputSpec.name} Diagnosis`}
          </Button>
        </form>

        {result && (
          <section className="mt-8 rounded border border-slate-200 bg-white p-6 shadow-sm" aria-labelledby="diagnosis-result">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <p className="text-sm font-bold uppercase tracking-[0.16em] text-trust-teal">Completed</p>
                <h2 id="diagnosis-result" className="mt-1 text-2xl font-black">Diagnosis Result</h2>
              </div>
              <VerifiedUserIcon color={ethereumVerified ? 'success' : 'disabled'} fontSize="large" />
            </div>

            <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {[
                ['Prediction', result.prediction.replace(/_/g, ' ')],
                ['Confidence', `${(result.confidence * 100).toFixed(1)}%`],
                ['Trust Score', result.trust_score.toFixed(3)],
                ['Ethereum', ethereumVerified ? 'Verified' : result.blockchain_status?.ethereum?.status ?? 'Unavailable'],
              ].map(([label, value]) => (
                <div key={label} className="rounded bg-slate-50 p-4">
                  <p className="text-sm font-semibold text-slate-500">{label}</p>
                  <p className="mt-2 text-xl font-black capitalize text-trust-ink">{value}</p>
                </div>
              ))}
            </div>
            <LinearProgress className="mt-5" variant="determinate" value={result.confidence * 100} />
            <p className="mt-4 break-all text-xs text-slate-500">Record hash: {result.blockchain_hash}</p>

            <div className="mt-5 flex flex-wrap gap-3">
              <Button
                variant="contained"
                onClick={() => downloadFile(
                  `/reports/${result.diagnosis_id}.pdf`,
                  `trustmedai-${result.diagnosis_id}.pdf`,
                )}
              >
                Download PDF Report
              </Button>
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
        )}
      </main>
    </div>
  );
}
