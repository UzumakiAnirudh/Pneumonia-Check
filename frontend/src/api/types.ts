/**
 * API contract — mirrors backend/app/schemas. Keep both in sync.
 */

export type ModelKey = 'densenet' | 'swin';
export type ModelChoice = ModelKey | 'both';
export type ClassificationMode = 'two_stage' | 'three_class';

export type Stage1Label = 'NORMAL' | 'PNEUMONIA';
export type Stage2Label = 'BACTERIAL' | 'VIRAL';
export type FinalLabel = 'NORMAL' | 'BACTERIAL' | 'VIRAL';
export type AnyLabel = Stage1Label | Stage2Label;

export interface StageResult<L extends string> {
  label: L;
  /** Calibrated probability of `label`, 0–1. */
  confidence: number;
  /** Calibrated probabilities for every class in this stage. */
  probabilities: Record<L, number>;
  /** Temperature used for calibration (1.0 = uncalibrated). */
  temperature: number;
}

export interface Reliability {
  level: 'high' | 'low';
  threshold: number;
  message: string;
}

export interface DominantRegion {
  vertical: 'upper' | 'middle' | 'lower';
  /** Patient side (radiological convention: patient's right is on the image left). */
  side: 'left' | 'right' | 'bilateral';
  label: string;
}

export interface Explanation {
  method: string;
  target_label: AnyLabel | FinalLabel;
  target_layer: string;
  /** Data URI (PNG) — colour-mapped Grad-CAM heatmap, same aspect as `image_png`. */
  heatmap_png: string;
  /** Data URI (PNG) — heatmap blended onto the X-ray at 45% opacity. May be null in history. */
  overlay_png: string | null;
  dominant_region: DominantRegion;
  description: string;
  /** Share of heatmap energy that falls inside the estimated lung fields, 0–100. */
  lung_attention_pct: number;
  /** Share of the image covered by the lung mask — the in-lung attention expected by chance. */
  lung_area_pct?: number | null;
  /** Mean attention per zone, keys like `right_upper`, normalised to sum 1. */
  region_scores: Record<string, number>;
}

export interface ModelResult {
  model: ModelKey;
  model_name: string;
  mode: ClassificationMode;
  stage1: StageResult<Stage1Label>;
  stage2: StageResult<Stage2Label> | null;
  final_label: FinalLabel;
  final_confidence: number;
  /**
   * Joint probabilities P(N), P(P)·P(B|P), P(P)·P(V|P) — or just NORMAL/PNEUMONIA when
   * Stage 2 did not run (the subtype is never invented for a normal result).
   */
  class_probabilities: Partial<Record<AnyLabel, number>>;
  reliability: Reliability;
  explanation: Explanation | null;
  inference_ms: number;
}

export interface ImageInfo {
  width: number;
  height: number;
  format: string;
  file_size_bytes: number;
  is_dicom: boolean;
}

export interface ValidationResult {
  /** True when the image can be analysed (it is a CXR and quality is acceptable). */
  is_valid: boolean;
  is_chest_xray: boolean;
  /** 0–1 likelihood the image is a frontal chest X-ray. */
  score: number;
  method: 'heuristic' | 'model';
  message: string;
  reasons: string[];
  warnings: string[];
  image: ImageInfo;
}

export interface Agreement {
  agree: boolean;
  message: string;
  labels: Partial<Record<ModelKey, FinalLabel>>;
}

export interface PredictResponse {
  id: string;
  created_at: string;
  source_name: string | null;
  image: ImageInfo;
  /** Data URI — metadata-stripped, grayscale display image (thumbnail when reopened from history). */
  image_png: string;
  validation: ValidationResult;
  results: ModelResult[];
  agreement: Agreement | null;
  is_mock: boolean;
  total_ms: number;
  saved_to_history: boolean;
}

export interface PredictParams {
  file: File;
  model: ModelChoice;
  threshold: number;
  saveHistory: boolean;
  sourceName?: string | null;
}

export interface ModelStatus {
  key: ModelKey;
  name: string;
  ready: boolean;
  weights: Record<string, boolean>;
}

export interface HealthResponse {
  status: 'ok' | 'degraded';
  version: string;
  use_mock_models: boolean;
  classification_mode: ClassificationMode;
  device: string;
  models: ModelStatus[];
  validator: { method: 'heuristic' | 'model'; loaded: boolean };
  calibration: { loaded: boolean; temperatures: Record<string, number> };
  history_enabled: boolean;
  model_version?: { id: string; label: string } | null;
  training?: TrainingStatus | null;
}

export interface TrainingStatus {
  state:
    'training' | 'evaluating' | 'comparing' | 'activated' | 'kept_previous' | 'failed' | string;
  label: string;
  percent: number;
  epoch?: number | null;
  epochs?: number | null;
  active_version?: string | null;
  new_version?: string | null;
  description: string;
  message: string;
  started_at?: string | null;
  updated_at?: string | null;
}

export interface SampleImage {
  id: string;
  label: FinalLabel;
  title: string;
  description: string;
  url: string;
  synthetic: boolean;
}

export interface HistoryItem {
  id: string;
  created_at: string;
  source_name: string | null;
  models: ModelKey[];
  final_label: FinalLabel;
  confidence: number;
  thumbnail: string;
  is_mock: boolean;
  agree: boolean | null;
}

// ---------------------------------------------------------------- metrics ---

/** `null` = undefined for this set (e.g. recall/AUC on a normals-only external set). */
export interface MetricSummary {
  accuracy: number | null;
  precision: number | null;
  recall: number | null;
  specificity: number | null;
  f1: number | null;
  roc_auc: number | null;
}

export interface RocCurve {
  fpr: number[];
  tpr: number[];
  auc: number;
}

export interface CalibrationCurve {
  bin_confidence: number[];
  bin_accuracy: number[];
  bin_count: number[];
  ece_before: number | null;
  ece_after: number | null;
}

export interface TaskMetrics {
  labels: string[];
  positive_label: string;
  n: number;
  metrics: MetricSummary;
  confusion_matrix: number[][];
  roc: RocCurve | null;
  calibration?: CalibrationCurve | null;
}

export type ModelTaskMetrics = Partial<
  Record<'stage1' | 'stage2' | 'three_class' | 'pipeline', TaskMetrics>
>;

export interface ExternalDataset {
  name: string;
  description: string;
  n: number;
  models: Partial<Record<ModelKey, { stage1: TaskMetrics; drop: Partial<MetricSummary> }>>;
}

export interface EpochLog {
  epoch: number;
  train_loss: number;
  val_loss: number;
  train_acc: number;
  val_acc: number;
  lr?: number;
}

export interface GalleryItem {
  model: ModelKey;
  category: 'correct' | 'misclassified' | 'failure';
  true_label: string;
  pred_label: string;
  confidence: number;
  lung_attention_pct: number;
  image: string;
  note: string;
}

export interface MetricsResponse {
  is_demo: boolean;
  generated_at: string;
  notes: string;
  dataset: { name: string; split: Record<string, number>; description: string };
  internal: Partial<Record<ModelKey, ModelTaskMetrics>>;
  external: ExternalDataset[];
  training_curves: Partial<Record<ModelKey, Partial<Record<string, EpochLog[]>>>>;
  /** Same test-set metrics split by population (pediatric Kermany vs adult sources). */
  by_domain?: Partial<
    Record<ModelKey, Partial<Record<string, Partial<Record<'pediatric' | 'adult', TaskMetrics>>>>>
  >;
  gallery: GalleryItem[];
}

// ----------------------------------------------------------------- auth ---

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  created_at: string;
}

export interface RegisterParams {
  name: string;
  email: string;
  password: string;
}

// --------------------------------------------------------------- errors ---

export interface ApiErrorDetail {
  code: string;
  message: string;
  validation?: ValidationResult;
}

export class ApiError extends Error {
  readonly status: number;
  readonly detail: ApiErrorDetail;

  constructor(status: number, detail: ApiErrorDetail) {
    super(detail.message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}
