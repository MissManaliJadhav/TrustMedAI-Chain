import { FormEvent, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Button, TextField } from '@mui/material';
import BiotechIcon from '@mui/icons-material/Biotech';
import HubIcon from '@mui/icons-material/Hub';
import VerifiedUserIcon from '@mui/icons-material/VerifiedUser';
import DownloadIcon from '@mui/icons-material/Download';
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import Header from '../components/Header';
import HeroIllustration from '../components/HeroIllustration';
import { api } from '../api/client';
import type { Disease } from '../types';

const fallbackDiseases: Disease[] = [
  { key: 'heart', name: 'Heart Disease', dataset: 'UCI Heart Disease Dataset', modality: 'tabular', task_type: 'binary', labels: [] },
  { key: 'diabetes', name: 'Diabetes', dataset: 'Pima Indians Diabetes Dataset', modality: 'tabular', task_type: 'binary', labels: [] },
  { key: 'asthma', name: 'Asthma', dataset: 'Asthma Prediction Dataset', modality: 'tabular', task_type: 'binary', labels: [] },
  { key: 'pneumonia', name: 'Pneumonia', dataset: 'Chest X-Ray Pneumonia Dataset', modality: 'image', task_type: 'binary', labels: [] },
  { key: 'eye', name: 'Eye Disease', dataset: 'Ocular Disease Recognition Dataset', modality: 'image', task_type: 'multiclass', labels: [] },
  { key: 'tuberculosis', name: 'Tuberculosis', dataset: 'TB Chest X-Ray Dataset', modality: 'image', task_type: 'binary', labels: [] },
  { key: 'liver', name: 'Liver Disease', dataset: 'Indian Liver Patient Dataset', modality: 'tabular', task_type: 'binary', labels: [] },
  { key: 'parkinson', name: 'Parkinson Disease', dataset: 'UCI Parkinson Dataset', modality: 'voice', task_type: 'binary', labels: [] },
  { key: 'brain_tumor', name: 'Brain Tumor', dataset: 'Brain MRI Dataset', modality: 'image', task_type: 'multiclass', labels: [] },
];

const trustSeries = [
  { round: 'R1', dtei: 0.72, aecs: 0.78 },
  { round: 'R2', dtei: 0.79, aecs: 0.82 },
  { round: 'R3', dtei: 0.84, aecs: 0.87 },
  { round: 'R4', dtei: 0.88, aecs: 0.91 },
  { round: 'R5', dtei: 0.92, aecs: 0.94 },
];

export default function LandingPage() {
  const [diseases, setDiseases] = useState<Disease[]>(fallbackDiseases);
  const [sent, setSent] = useState(false);

  useEffect(() => {
    api.get<Disease[]>('/datasets/diseases').then((res) => setDiseases(res.data)).catch(() => setDiseases(fallbackDiseases));
  }, []);

  const handleContact = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    await api.post('/contact', {
      name: data.get('name'),
      email: data.get('email'),
      message: data.get('message'),
    });
    setSent(true);
    event.currentTarget.reset();
  };

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
          <div className="grid gap-4 md:grid-cols-3">
            {[
              ['9', 'Disease models'],
              ['0.94', 'AECS target'],
              ['4', 'Federated nodes'],
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
              {diseases.map((disease) => (
                <article key={disease.key} className="rounded border border-slate-200 p-5 shadow-sm">
                  <div className="flex items-center justify-between gap-3">
                    <h3 className="text-lg font-bold">{disease.name}</h3>
                    <span className="rounded bg-teal-50 px-2 py-1 text-xs font-bold text-trust-teal">{disease.modality}</span>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-slate-600">{disease.dataset}</p>
                </article>
              ))}
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
              <h3 className="font-bold">Dynamic Trust Evolution</h3>
              <HubIcon className="trust-pulse text-trust-coral" />
            </div>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trustSeries}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="round" />
                  <YAxis domain={[0.6, 1]} />
                  <Tooltip />
                  <Area dataKey="dtei" stroke="#0f766e" fill="#ccfbf1" />
                  <Area dataKey="aecs" stroke="#f97316" fill="#ffedd5" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </section>

        <section className="bg-trust-ink py-12 text-white">
          <div className="mx-auto grid max-w-7xl gap-6 px-4 md:grid-cols-3">
            {[
              ['Clinical AI Lead', 'The trust score and explanation stability views make model review faster.'],
              ['Hospital Admin', 'Federated trust synchronization gives leadership a clean institutional picture.'],
              ['Researcher', 'The adversarial and XAI dashboards are exactly the experiment surface we need.'],
            ].map(([name, quote]) => (
              <blockquote key={name} className="rounded border border-white/15 p-5">
                <p className="leading-7 text-white/82">{quote}</p>
                <footer className="mt-4 font-bold">{name}</footer>
              </blockquote>
            ))}
          </div>
        </section>

        <section className="mx-auto grid max-w-7xl gap-8 px-4 py-12 md:grid-cols-2">
          <div>
            <h2 className="text-3xl font-black">Contact</h2>
            <p className="mt-3 leading-7 text-slate-600">Coordinate hospital onboarding, research evaluation, or clinical pilot readiness.</p>
            <Button className="mt-5" variant="outlined" startIcon={<DownloadIcon />}>
              Download Research Brief
            </Button>
          </div>
          <form onSubmit={handleContact} className="grid gap-4 rounded border border-slate-200 bg-white p-5 shadow-sm">
            <TextField name="name" label="Name" required />
            <TextField name="email" label="Email" type="email" required />
            <TextField name="message" label="Message" multiline minRows={4} required />
            <Button type="submit" variant="contained">Send</Button>
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
