import axios from 'axios';

// Turn an API error into a readable English message
export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status;
    const detail = error.response?.data?.detail;
    if (status === 403) return typeof detail === 'string' ? detail : 'Access denied';
    if (status === 413) return 'File is too large';
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail) && detail[0]?.msg) return String(detail[0].msg);
    if (!error.response) return 'Could not connect to the server';
    if (status === 404) return 'Not found';
  }
  return 'Something went wrong';
}
