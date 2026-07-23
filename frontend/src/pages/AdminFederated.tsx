import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Activity, Database, Hospital, Play, ShieldCheck, Users } from 'lucide-react';
import { API_BASE_URL } from '../config';

interface FederatedNode {
  id: string;
  name: string;
  region: string;
  verified: boolean;
  reputation: number;
  trust: number;
}

interface FederatedUpdate {
  id: string;
  hospital_id: string;
  hospital_name: string;
  sample_count: number;
  metrics: Record<string, number>;
  privacy_report: Record<string, boolean | number | string>;
  payload_hash: string;
  created_at: string;
}

interface FederatedRound {
  id: string;
  round_number: number;
  model_name: string;
  disease_key: string;
  status: string;
  strategy: string;
  min_clients: number;
  submitted_clients: number;
  global_model_version: string;
  metrics: Record<string, number>;
  privacy_config: Record<string, boolean | number | string | string[]>;
  update_hash: string | null;
  created_at: string;
  completed_at: string | null;
  updates: FederatedUpdate[];
}

interface FederatedDashboard {
  mode: string;
  architecture: {
    orchestrator: string;
    strategy: string;
    privacy: string;
    raw_data_shared: boolean;
    storage: string;
  };
  nodes: FederatedNode[];
  model_weight_round: number;
  consensus_reliability: number;
  active_round: FederatedRound | null;
  rounds: FederatedRound[];
  cifts: {
    trust_synchronization: number;
    hospital_reputation: number;
    trust_evolution: number[];
  };
}

function tokenHeaders() {
  const token = localStorage.getItem('trustmedai_access');
  return {
    Authorization: `Bearer ${token}`,
    'Content-Type': 'application/json',
  };
}

function pct(value: number | undefined) {
  return `${(((value ?? 0) as number) * 100).toFixed(1)}%`;
}

export const AdminFederated: React.FC = () => {
  const [dashboard, setDashboard] = useState<FederatedDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboard = useCallback(async () => {
    try {
      setError(null);
      const response = await fetch(`${API_BASE_URL}/federated/dashboard`, {
        headers: tokenHeaders(),
      });
      if (!response.ok) throw new Error('Failed to load federated dashboard');
      setDashboard(await response.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  const activeCollectingRound = useMemo(
    () => dashboard?.rounds.find((round) => round.status === 'collecting') ?? null,
    [dashboard],
  );


  const startRound = async () => {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/federated/rounds`, {
        method: 'POST',
        headers: tokenHeaders(),
        body: JSON.stringify({
          model_name: 'trustmedai-risk-model',
          disease_key: 'heart',
          min_clients: 2,
          global_model_version: 'v1',
          privacy_epsilon: 3,
          secure_aggregation: true,
          differential_privacy: true,
        }),
      });
      if (!response.ok) throw new Error('Could not start federated round');
      setDashboard(await response.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setBusy(false);
    }
  };

  const runDemoRound = async () => {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/federated/demo-round`, {
        method: 'POST',
        headers: tokenHeaders(),
        body: JSON.stringify({
          model_name: 'trustmedai-risk-model',
          disease_key: 'heart',
          participating_hospitals: 4,
        }),
      });
      if (!response.ok) throw new Error('Demo federated round failed');
      const data = await response.json();
      setDashboard(data.dashboard);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setBusy(false);
    }
  };

  const submitHospitalUpdate = async (hospital: FederatedNode) => {
    if (!activeCollectingRound) return;
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/federated/rounds/${activeCollectingRound.id}/updates`, {
        method: 'POST',
        headers: tokenHeaders(),
        body: JSON.stringify({
          hospital_id: hospital.id,
          sample_count: 1,
          metrics: {},
          privacy_epsilon_spent: 0.2,
        }),
      });
      if (!response.ok) throw new Error('Hospital update was rejected');
      const data = await response.json();
      setDashboard(data.dashboard);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setBusy(false);
    }
  };

  const aggregateActiveRound = async () => {
    if (!activeCollectingRound) return;
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/federated/rounds/${activeCollectingRound.id}/aggregate`, {
        method: 'POST',
        headers: tokenHeaders(),
      });
      if (!response.ok) throw new Error('Aggregation needs more hospital updates');
      const data = await response.json();
      setDashboard(data.dashboard);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return <div className="py-8 text-center">Loading federated learning dashboard...</div>;
  }

  if (!dashboard) {
    return <div className="py-8 text-center text-red-600">Federated dashboard is unavailable.</div>;
  }

  const latestRound = dashboard.rounds[0] ?? null;
  const cards = [
    {
      label: 'Hospitals',
      value: dashboard.nodes.length,
      detail: 'verified FL clients',
      icon: <Hospital className="h-6 w-6 text-white" />,
      tone: 'bg-blue-600',
    },
    {
      label: 'Current Round',
      value: dashboard.model_weight_round,
      detail: latestRound ? latestRound.status : 'not started',
      icon: <Activity className="h-6 w-6 text-white" />,
      tone: 'bg-teal-600',
    },
    {
      label: 'Submitted Updates',
      value: latestRound?.submitted_clients ?? 0,
      detail: latestRound ? `minimum ${latestRound.min_clients}` : 'waiting',
      icon: <Users className="h-6 w-6 text-white" />,
      tone: 'bg-indigo-600',
    },
    {
      label: 'Consensus Reliability',
      value: pct(dashboard.consensus_reliability),
      detail: 'weighted model accuracy',
      icon: <ShieldCheck className="h-6 w-6 text-white" />,
      tone: 'bg-emerald-600',
    },
    {
      label: 'Data Shared',
      value: dashboard.architecture.raw_data_shared ? 'Raw' : 'None',
      detail: 'updates only, no patient rows',
      icon: <Database className="h-6 w-6 text-white" />,
      tone: 'bg-slate-700',
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-3xl font-bold text-gray-950">Federated Learning</h2>
          <p className="mt-1 text-gray-600">
            Multi-hospital AI training with secure model-update aggregation and no raw patient data sharing.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={startRound}
            disabled={busy}
            className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-bold text-gray-800 hover:bg-gray-100 disabled:opacity-50"
          >
            Start Round
          </button>
          <button
            type="button"
            onClick={runDemoRound}
            disabled={busy}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-bold text-white hover:bg-blue-700 disabled:opacity-50"
          >
            <Play className="h-4 w-4" />
            Run Demo Round
          </button>
        </div>
      </div>

      {error && <div className="rounded border border-red-200 bg-red-50 px-4 py-3 text-red-700">{error}</div>}

      <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
        {cards.map((card) => (
          <article key={card.label} className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="text-sm font-semibold text-gray-500">{card.label}</p>
                <p className="mt-2 text-3xl font-bold text-gray-950">{card.value}</p>
                <p className="mt-2 text-xs font-medium text-gray-500">{card.detail}</p>
              </div>
              <span className={`grid h-12 w-12 shrink-0 place-items-center rounded-lg ${card.tone}`}>{card.icon}</span>
            </div>
          </article>
        ))}
      </section>

      <section className="grid gap-6 xl:grid-cols-[1fr_380px]">
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h3 className="text-xl font-bold text-gray-950">Hospital Clients</h3>
              <p className="mt-1 text-sm text-gray-600">Each hospital trains locally and sends only privacy-preserving weight deltas.</p>
            </div>
            {activeCollectingRound && (
              <button
                type="button"
                onClick={aggregateActiveRound}
                disabled={busy || activeCollectingRound.submitted_clients < activeCollectingRound.min_clients}
                className="rounded-lg bg-emerald-600 px-4 py-2 text-sm font-bold text-white hover:bg-emerald-700 disabled:opacity-50"
              >
                Aggregate Round
              </button>
            )}
          </div>

          <div className="mt-5 overflow-hidden rounded-lg border border-gray-200">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-bold text-gray-700">Hospital</th>
                  <th className="px-4 py-3 text-left text-sm font-bold text-gray-700">Region</th>
                  <th className="px-4 py-3 text-left text-sm font-bold text-gray-700">Trust</th>
                  <th className="px-4 py-3 text-left text-sm font-bold text-gray-700">Privacy</th>
                  <th className="px-4 py-3 text-left text-sm font-bold text-gray-700">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {dashboard.nodes.map((node) => {
                  const alreadySubmitted = activeCollectingRound?.updates.some((update) => update.hospital_id === node.id);
                  return (
                    <tr key={node.id} className="bg-white">
                      <td className="px-4 py-3">
                        <p className="font-bold text-gray-950">{node.name}</p>
                        <p className="text-xs text-gray-500">{node.verified ? 'Verified client' : 'Pending verification'}</p>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-600">{node.region}</td>
                      <td className="px-4 py-3 text-sm font-bold text-gray-950">{pct(node.trust)}</td>
                      <td className="px-4 py-3 text-sm text-gray-600">No raw patient data</td>
                      <td className="px-4 py-3">
                        <button
                          type="button"
                          disabled={busy || !activeCollectingRound || Boolean(alreadySubmitted)}
                          onClick={() => submitHospitalUpdate(node)}
                          className="rounded-lg border border-gray-300 px-3 py-2 text-xs font-bold text-gray-800 hover:bg-gray-100 disabled:opacity-50"
                        >
                          {alreadySubmitted ? 'Submitted' : 'Submit Update'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        <aside className="space-y-6">
          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
            <h3 className="font-bold text-gray-950">Architecture</h3>
            <div className="mt-4 space-y-3 text-sm text-gray-600">
              <p><strong>Orchestrator:</strong> {dashboard.architecture.orchestrator}</p>
              <p><strong>Strategy:</strong> {dashboard.architecture.strategy}</p>
              <p><strong>Privacy:</strong> {dashboard.architecture.privacy}</p>
              <p><strong>Storage:</strong> {dashboard.architecture.storage}</p>
            </div>
          </div>

          <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
            <h3 className="font-bold text-gray-950">Latest Round</h3>
            {latestRound ? (
              <div className="mt-4 space-y-3 text-sm text-gray-600">
                <p><strong>Model:</strong> {latestRound.model_name}</p>
                <p><strong>Disease:</strong> {latestRound.disease_key}</p>
                <p><strong>Status:</strong> {latestRound.status}</p>
                <p><strong>Accuracy:</strong> {pct(latestRound.metrics.accuracy)}</p>
                <p><strong>Total Samples:</strong> {latestRound.metrics.total_samples ?? 0}</p>
                <p className="break-all"><strong>Aggregate Hash:</strong> {latestRound.update_hash ?? 'Pending'}</p>
              </div>
            ) : (
              <p className="mt-4 text-sm text-gray-600">No rounds have been started yet.</p>
            )}
          </div>
        </aside>
      </section>

      <section className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
        <h3 className="text-xl font-bold text-gray-950">Round History</h3>
        <div className="mt-5 grid gap-3">
          {dashboard.rounds.length ? dashboard.rounds.map((round) => (
            <article key={round.id} className="rounded-lg border border-gray-200 bg-gray-50 p-4">
              <div className="grid gap-4 md:grid-cols-5">
                <div>
                  <p className="text-xs font-bold uppercase text-gray-500">Round</p>
                  <p className="font-bold text-gray-950">#{round.round_number}</p>
                </div>
                <div>
                  <p className="text-xs font-bold uppercase text-gray-500">Status</p>
                  <p className="font-bold capitalize text-gray-950">{round.status}</p>
                </div>
                <div>
                  <p className="text-xs font-bold uppercase text-gray-500">Hospitals</p>
                  <p className="font-bold text-gray-950">{round.submitted_clients}</p>
                </div>
                <div>
                  <p className="text-xs font-bold uppercase text-gray-500">Accuracy</p>
                  <p className="font-bold text-gray-950">{pct(round.metrics.accuracy)}</p>
                </div>
                <div>
                  <p className="text-xs font-bold uppercase text-gray-500">Raw Data</p>
                  <p className="font-bold text-gray-950">Never shared</p>
                </div>
              </div>
            </article>
          )) : (
            <p className="rounded bg-gray-50 p-5 text-gray-600">Start or run a federated round to populate history.</p>
          )}
        </div>
      </section>
    </div>
  );
};
