import { apiDelete, apiGet, apiPut } from './client';
import type { AppSetting } from '../types/settings';

export function fetchAppSettings() {
  return apiGet<AppSetting[]>('/admin/settings');
}

export function updateAppSetting(key: string, value: string) {
  return apiPut<AppSetting>(`/admin/settings/${encodeURIComponent(key)}`, { value });
}

export function resetAppSetting(key: string): Promise<void> {
  return apiDelete(`/admin/settings/${encodeURIComponent(key)}`);
}
