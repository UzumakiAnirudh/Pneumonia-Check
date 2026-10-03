import type {
  AuthUser,
  HealthResponse,
  HistoryItem,
  MetricsResponse,
  PredictParams,
  PredictResponse,
  RegisterParams,
  SampleImage,
  ValidationResult,
} from './types';
import { createHttpClient } from './httpClient';

/** Everything the UI needs from the backend. */
export interface ApiClient {
  me(): Promise<AuthUser>;
  login(email: string, password: string): Promise<AuthUser>;
  register(params: RegisterParams): Promise<AuthUser>;
  logout(): Promise<void>;
  health(): Promise<HealthResponse>;
  validate(file: File): Promise<ValidationResult>;
  predict(params: PredictParams): Promise<PredictResponse>;
  metrics(): Promise<MetricsResponse>;
  samples(): Promise<SampleImage[]>;
  sampleFile(sample: SampleImage): Promise<File>;
  history(): Promise<HistoryItem[]>;
  historyItem(id: string): Promise<PredictResponse>;
  deleteHistoryItem(id: string): Promise<void>;
  clearHistory(): Promise<void>;
}

const baseUrl = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');

export const api: ApiClient = createHttpClient(baseUrl);
