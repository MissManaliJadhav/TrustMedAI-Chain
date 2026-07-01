import { useEffect, useState } from 'react';
import { Alert, Button, CircularProgress } from '@mui/material';
import ImageSearchIcon from '@mui/icons-material/ImageSearch';
import MonitorHeartIcon from '@mui/icons-material/MonitorHeart';
import { Link } from 'react-router-dom';
import Header from '../components/Header';
import { api } from '../api/client';
import type { Disease } from '../types';

interface DiseaseGroupProps {
  title: string;
  description: string;
  diseases: Disease[];
  imageBased?: boolean;
}

function DiseaseGroup({ title, description, diseases, imageBased = false }: DiseaseGroupProps) {
  const Icon = imageBased ? ImageSearchIcon : MonitorHeartIcon;

  return (
    <section aria-labelledby={`${imageBased ? 'image' : 'clinical'}-diseases`}>
      <div className="mb-5 flex items-start gap-3">
        <span className="grid h-11 w-11 shrink-0 place-items-center rounded bg-teal-50 text-trust-teal">
          <Icon />
        </span>
        <div>
          <h2 id={`${imageBased ? 'image' : 'clinical'}-diseases`} className="text-2xl font-black">{title}</h2>
          <p className="mt-1 text-slate-600">{description}</p>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {diseases.map((disease) => (
          <article key={disease.key} className="flex min-h-56 flex-col rounded border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-start justify-between gap-3">
              <h3 className="text-xl font-black text-trust-ink">{disease.name}</h3>
              <span className="rounded bg-teal-50 px-2 py-1 text-xs font-bold uppercase text-trust-teal">
                {imageBased ? 'Image upload' : 'Clinical inputs'}
              </span>
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-600">{disease.dataset}</p>
            <p className="mt-2 text-sm text-slate-500">
              Output: {disease.labels.join(' / ').replace(/_/g, ' ')}
            </p>
            <Button
              className="mt-auto pt-5"
              component={Link}
              to={`/diagnosis/${disease.key}`}
              variant="contained"
              fullWidth
            >
              Open {disease.name} Page
            </Button>
          </article>
        ))}
      </div>
    </section>
  );
}

export default function DiagnosisCatalogPage() {
  const [diseases, setDiseases] = useState<Disease[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    api.get<Disease[]>('/datasets/diseases', { signal: controller.signal })
      .then((response) => setDiseases(response.data))
      .catch((requestError) => {
        if (requestError?.code !== 'ERR_CANCELED') {
          setError('The disease catalog could not be loaded.');
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  const imageDiseases = diseases.filter((disease) => disease.modality === 'image');
  const clinicalDiseases = diseases.filter((disease) => disease.modality !== 'image');

  return (
    <div className="min-h-screen bg-[#f7fbfa]">
      <Header />
      <main className="mx-auto max-w-7xl px-4 py-8">
        <div className="mb-10 max-w-3xl">
          <p className="text-sm font-bold uppercase tracking-[0.16em] text-trust-teal">Dedicated diagnosis workflows</p>
          <h1 className="mt-2 text-4xl font-black text-trust-ink">Choose a Disease</h1>
          <p className="mt-3 text-lg leading-8 text-slate-600">
            Every disease has its own page. Patient information is collected first, followed by that model&apos;s
            exact clinical inputs or medical-image upload.
          </p>
        </div>

        {error && <Alert className="mb-6" severity="error">{error}</Alert>}
        {loading ? (
          <div className="flex items-center gap-3 rounded border border-slate-200 bg-white p-6">
            <CircularProgress size={24} />
            <span>Loading disease pages…</span>
          </div>
        ) : (
          <div className="grid gap-12">
            <DiseaseGroup
              title="Clinical and Tabular Diseases"
              description="Enter patient details followed by the disease-specific measurements expected by the trained model."
              diseases={clinicalDiseases}
            />
            <DiseaseGroup
              title="Image-Based Diseases"
              description="Enter patient details, then upload the required X-ray, retinal image, or MRI scan."
              diseases={imageDiseases}
              imageBased
            />
          </div>
        )}
      </main>
    </div>
  );
}
