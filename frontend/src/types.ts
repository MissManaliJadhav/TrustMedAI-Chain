export interface Disease {
  key: string;
  name: string;
  dataset: string;
  modality: string;
  task_type: string;
  labels: string[];
}

export interface DiseaseFeature {
  name: string;
  label: string;
  input_type: 'number' | 'boolean' | 'category';
  required: boolean;
  minimum: number | null;
  maximum: number | null;
  default: number | string | null;
  choices: Array<number | string> | null;
}

export interface DiseaseInputSpec extends Disease {
  input_mode: 'features' | 'image';
  model_available: boolean | null;
  features: DiseaseFeature[];
  model_info: {
    artifact_version?: number;
    trained_at?: string;
    selected_model?: string;
    deployment_status?: 'ready_for_research' | 'blocked_low_quality' | 'baseline_only' | 'unknown';
    test_metrics?: Record<string, number>;
    data_quality?: {
      source_rows?: number;
      rows_after_exact_deduplication?: number;
      exact_duplicates_removed?: number;
      notes?: string[];
    };
    limitations?: string[];
  };
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
