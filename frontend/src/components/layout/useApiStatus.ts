import { useHealth } from '@/api/hooks';

export function useApiStatus() {
  const health = useHealth();
  const online = health.isSuccess && !health.isError;
  const data = health.data;
  const status: 'online' | 'warning' | 'offline' | 'idle' = health.isLoading
    ? 'idle'
    : !online
      ? 'offline'
      : data?.status === 'degraded' || data?.use_mock_models
        ? 'warning'
        : 'online';
  const label = health.isLoading
    ? 'Connecting…'
    : !online
      ? 'API offline'
      : data?.use_mock_models
        ? 'API online · mock models'
        : 'API online · trained models';
  return { status, label, health };
}
