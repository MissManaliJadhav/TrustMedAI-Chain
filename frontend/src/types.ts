export interface Disease {
  key: string;
  name: string;
  dataset: string;
  modality: string;
  task_type: string;
  labels: string[];
}

export interface TrustPoint {
  timestamp: string;
  disease_key: string;
  dtei: number;
  fidelity: number;
  interpretability: number;
  robustness: number;
  blockchain_integrity: number;
  compliance: number;
}
