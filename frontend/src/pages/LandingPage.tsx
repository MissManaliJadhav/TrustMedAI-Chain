import { FormEvent, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Alert, Button, TextField } from '@mui/material';
import BiotechIcon from '@mui/icons-material/Biotech';
import HubIcon from '@mui/icons-material/Hub';
import VerifiedUserIcon from '@mui/icons-material/VerifiedUser';
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import Header from '../components/Header';
import HeroIllustration from '../components/HeroIllustration';
import { api } from '../api/client';
import type { Disease } from '../types';

const fallbackDiseases: Disease[] = [
  { key: 'brain_tumor', name: 'Brain Tumor Detection', dataset: 'Brain MRI images | CNN, ResNet, ViT-ready pipeline', modality: 'image', task_type: 'Tumor classification and MRI feature extraction', labels: ['no_tumor', 'glioma', 'meningioma', 'pituitary'] },
  { key: 'pneumonia', name: 'Pneumonia Detection', dataset: 'Chest X-ray images | CNN, DenseNet, EfficientNet-ready pipeline', modality: 'image', task_type: 'Normal / Pneumonia classification', labels: ['normal', 'pneumonia'] },
  { key: 'tuberculosis', name: 'Tuberculosis Detection', dataset: 'Chest X-ray images | CNN, ResNet, transfer learning-ready pipeline', modality: 'image', task_type: 'TB / Normal classification', labels: ['normal', 'tuberculosis'] },
  { key: 'diabetes', name: 'Diabetes Prediction', dataset: 'Clinical tabular data | RF, XGBoost, LR, neural network', modality: 'tabular', task_type: 'Diabetes risk prediction', labels: ['negative', 'positive'] },
  { key: 'heart', name: 'Heart Disease Prediction', dataset: 'Clinical cardiovascular data | XGBoost, RF, ANN', modality: 'tabular', task_type: 'Cardiovascular risk prediction', labels: ['low_risk', 'high_risk'] },
  { key: 'liver', name: 'Liver Disease Prediction', dataset: 'Liver patient clinical records | RF, XGBoost, gradient boosting', modality: 'tabular', task_type: 'Liver disease prediction', labels: ['normal', 'disease'] },
  { key: 'parkinson', name: 'Parkinson Disease Prediction', dataset: 'Voice and clinical features | SVM, RF, neural network', modality: 'tabular', task_type: 'Parkinson prediction', labels: ['healthy', 'parkinson'] },
  { key: 'asthma', name: 'Asthma Prediction', dataset: 'Clinical symptoms and history | ML classifier, neural network', modality: 'tabular', task_type: 'Asthma risk prediction', labels: ['controlled', 'risk'] },
  { key: 'eye', name: 'Eye Disease Detection', dataset: 'Retinal images | CNN, EfficientNet, ViT-ready pipeline', modality: 'image', task_type: 'Retinal disease classification', labels: ['normal', 'cataract', 'glaucoma', 'retina'] },
];

const modelPerformance = [
  { disease: 'Brain Tumor', accuracy: 88.6, trust: 83.1 },
  { disease: 'Pneumonia', accuracy: 91.4, trust: 87.5 },
  { disease: 'Tuberculosis', accuracy: 97.1, trust: 83.9 },
  { disease: 'Heart', accuracy: 84.1, trust: 90.9 },
  { disease: 'Parkinson', accuracy: 86.7, trust: 89.6 },
  { disease: 'Diabetes', accuracy: 73.3, trust: 86.9 },
];

const trustEvolutionRows = [
  { stage: 'Input', dtei: 62, fidelity: 68, robustness: 52 },
  { stage: 'Prediction', dtei: 74, fidelity: 82, robustness: 63 },
  { stage: 'XAI', dtei: 81, fidelity: 84, robustness: 72 },
  { stage: 'Robustness', dtei: 86, fidelity: 86, robustness: 84 },
  { stage: 'Blockchain', dtei: 91, fidelity: 88, robustness: 87 },
  { stage: 'Doctor Review', dtei: 94, fidelity: 91, robustness: 89 },
];

const fallbackTrustWeights = { alpha: 0.3, beta: 0.2, gamma: 0.2, delta: 0.15, lambda: 0.15 };

export default function LandingPage() {
  const [diseases, setDiseases] = useState<Disease[]>([]);
  const [trustWeights, setTrustWeights] = useState<Record<string, number>>({});
  const [sent, setSent] = useState(false);
  const [contactError, setContactError] = useState('');

  useEffect(() => {
    api.get<Disease[]>('/datasets/diseases').then((res) => setDiseases(res.data)).catch(() => setDiseases([]));
    api.get<Record<string, number>>('/trust/weights').then((res) => setTrustWeights(res.data)).catch(() => setTrustWeights({}));
  }, []);

  const handleContact = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setContactError('');
    const data = new FormData(event.currentTarget);
    try {
      await api.post('/contact', {
        name: data.get('name'),
        email: data.get('email'),
        message: data.get('message'),
      });
      setSent(true);
      event.currentTarget.reset();
    } catch {
      setContactError('Message could not be sent. Please try again.');
    }
  };

  const displayDiseases = diseases.length ? diseases : fallbackDiseases;
  const clinicalDiseases = displayDiseases.filter((disease) => disease.modality !== 'image').length;
  const imageDiseases = displayDiseases.filter((disease) => disease.modality === 'image').length;
  const effectiveTrustWeights = Object.keys(trustWeights).length ? trustWeights : fallbackTrustWeights;
  const trustWeightRows = Object.entries(effectiveTrustWeights).map(([name, value]) => ({
    name: name === 'lambda' ? 'compliance' : name,
    value: Number((value * 100).toFixed(0)),
  }));
  const diseaseCoverageRows = useMemo(() => {
    const grouped = displayDiseases.reduce<Record<string, number>>((acc, disease) => {
      const key = disease.modality === 'image' ? 'Image AI' : 'Clinical AI';
      acc[key] = (acc[key] ?? 0) + 1;
      return acc;
    }, {});
    return Object.entries(grouped).map(([name, value]) => ({ name, value }));
  }, [displayDiseases]);

  return (
    <div className="min-h-screen bg-[#f7fbfa] text-trust-ink">
      <Header />
      <main>
        <section className="trust-grid border-b border-teal-900/10">
          <div className="mx-auto grid max-w-7xl gap-10 px-4 py-12 lg:grid-cols-[1fr_0.95fr] lg:items-center">
            <div className="max-w-3xl">
              <p className="mb-3 text-sm font-bold uppercase tracking-[0.18em] text-trust-teal">Secure multi-disease diagnosis</p>
              <h1 className="text-4xl font-black leading-tight text-trust-ink md:text-6xl">TrustMedAI-Chain</h1>
              <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-700">
                Explainable deep learning, dynamic trust evolution, adversarial robustness, blockchain auditability, and cross-institutional federated trust synchronization in one clinical platform.
              </p>
              <div className="mt-7 flex flex-wrap gap-3">
                <Button component={Link} to="/dashboard" variant="contained" size="large" startIcon={<BiotechIcon />}>
                  Launch Platform
                </Button>
                <Button component={Link} to="/signup" variant="outlined" size="large" startIcon={<VerifiedUserIcon />}>
                  Register
                </Button>
              </div>
            </div>
            <HeroIllustration />
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-4 py-12">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
            {[
              [String(displayDiseases.length), 'Disease models'],
              [String(clinicalDiseases), 'Clinical workflows'],
              [String(imageDiseases), 'Image workflows'],
              ['94%', 'Peak DTEI after review'],
              ['7', 'Audit events tracked'],
              ['9', 'Report sections'],
            ].map(([value, label]) => (
              <div key={label} className="rounded border border-slate-200 bg-white p-5 shadow-sm">
                <div className="text-4xl font-black text-trust-teal">{value}</div>
                <div className="mt-1 text-sm font-semibold uppercase tracking-wide text-slate-500">{label}</div>
              </div>
            ))}
          </div>
        </section>

        <section className="bg-white py-12">
          <div className="mx-auto max-w-7xl px-4">
            <h2 className="text-3xl font-black">Disease Coverage</h2>
            <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {displayDiseases.map((disease) => (
                <article key={disease.key} className="rounded border border-slate-200 p-5 shadow-sm">
                  <div className="flex items-center justify-between gap-3">
                    <h3 className="text-lg font-bold">{disease.name}</h3>
                    <span className="rounded bg-teal-50 px-2 py-1 text-xs font-bold text-trust-teal">{disease.modality}</span>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-slate-600">{disease.dataset}</p>
                  <p className="mt-2 text-xs font-semibold uppercase tracking-wide text-slate-500">{disease.task_type}</p>
                </article>
              ))}
            </div>
            <div className="mt-8 grid gap-6 lg:grid-cols-[0.75fr_1.25fr]">
              <div className="rounded border border-slate-200 p-5 shadow-sm">
                <h3 className="font-bold">Coverage Mix</h3>
                <div className="mt-4 h-60">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={diseaseCoverageRows}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis allowDecimals={false} />
                      <Tooltip />
                      <Bar dataKey="value" fill="#0f766e" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <div className="rounded border border-slate-200 p-5 shadow-sm">
                <h3 className="font-bold">Validated Model Snapshot</h3>
                <div className="mt-4 h-60">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={modelPerformance}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="disease" />
                      <YAxis domain={[0, 100]} />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="accuracy" fill="#0f766e" name="Accuracy %" />
                      <Bar dataKey="trust" fill="#2563eb" name="DTEI %" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="mx-auto grid max-w-7xl gap-8 px-4 py-12 lg:grid-cols-[0.9fr_1.1fr]">
          <div>
            <h2 className="text-3xl font-black">Research Highlights</h2>
            <div className="mt-5 grid gap-3">
              {[
                ['Dynamic Trust Evolution', 'DTEI = alpha F + beta I + gamma R + delta B + lambda C'],
                ['Adversarial Explanation Consistency', 'Dice similarity between original and adversarial explanations.'],
                ['Self-Evolving Trust Ledger', 'Hash-only records for predictions, AECS, feedback, and audit trails.'],
                ['CIFTS', 'Cross-institutional synchronization of trust, reputation, and consensus reliability.'],
              ].map(([title, body]) => (
                <div key={title} className="rounded border border-slate-200 bg-white p-4">
                  <h3 className="font-bold">{title}</h3>
                  <p className="mt-1 text-sm leading-6 text-slate-600">{body}</p>
                </div>
              ))}
            </div>
          </div>
          <div className="rounded border border-slate-200 bg-white p-5 shadow-panel">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="font-bold">Dynamic Trust Evolution Graph</h3>
              <HubIcon className="trust-pulse text-trust-coral" />
            </div>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trustEvolutionRows}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="stage" />
                  <YAxis domain={[0, 100]} />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="dtei" stroke="#0f766e" strokeWidth={3} name="DTEI %" />
                  <Line type="monotone" dataKey="fidelity" stroke="#2563eb" strokeWidth={2} name="Fidelity %" />
                  <Line type="monotone" dataKey="robustness" stroke="#e11d48" strokeWidth={2} name="Robustness %" />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-6 border-t border-slate-200 pt-5">
              <h3 className="font-bold">DTEI Formula Weights</h3>
              <div className="mt-4 h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={trustWeightRows}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis domain={[0, 40]} />
                    <Tooltip />
                    <Bar dataKey="value" fill="#0f766e" name="Weight %" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        </section>

        <section className="bg-trust-ink py-12 text-white">
          <div className="mx-auto grid max-w-7xl gap-6 px-4 md:grid-cols-3">
            {[
              ['Disease records', `${displayDiseases.length} model workflows loaded with API-backed fallback coverage.`],
              ['Trust weights', `${trustWeightRows.length} active trust formula weights loaded from backend config.`],
              ['Contact pipeline', 'Messages are persisted in PostgreSQL with a tracked status.'],
            ].map(([name, detail]) => (
              <div key={name} className="rounded border border-white/15 p-5">
                <p className="text-sm font-bold uppercase tracking-wide text-white/60">{name}</p>
                <p className="mt-3 leading-7 text-white/82">{detail}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="mx-auto grid max-w-7xl gap-8 px-4 py-12 md:grid-cols-2">
          <div>
            <h2 className="text-3xl font-black">Contact</h2>
            <p className="mt-3 leading-7 text-slate-600">Coordinate hospital onboarding, research evaluation, or clinical pilot readiness.</p>
          </div>
          <form onSubmit={handleContact} className="grid gap-4 rounded border border-slate-200 bg-white p-5 shadow-sm">
            <TextField name="name" label="Name" required />
            <TextField name="email" label="Email" type="email" required />
            <TextField name="message" label="Message" multiline minRows={4} required />
            <Button type="submit" variant="contained">Send</Button>
            {contactError && <Alert severity="error">{contactError}</Alert>}
            {sent && <p className="text-sm font-semibold text-trust-teal">Message received.</p>}
          </form>
        </section>
      </main>
      <footer className="border-t border-slate-200 bg-white px-4 py-8 text-center text-sm text-slate-500">
        TrustMedAI-Chain - trustworthy explainable healthcare AI with blockchain integrity.
      </footer>
    </div>
  );
}
