import axios from 'axios';

// Turn an API error into a readable Ukrainian message
export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status;
    const detail = error.response?.data?.detail;
    if (status === 403) return 'Доступ заборонено';
    if (status === 413) return 'Файл занадто великий';
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg);
    if (!error.response) return 'Не вдалося зʼєднатися із сервером';
    if (status === 404) return 'Не знайдено';
  }
  return 'Щось пішло не так';
}
