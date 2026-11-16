import { api } from './client';
import type { Document } from '../types';

export const listDocuments = async (projectId: number): Promise<Document[]> =>
  (await api.get<Document[]>(`/project/${projectId}/documents`)).data;

export async function uploadDocuments(
  projectId: number,
  files: File[],
  onProgress?: (percent: number) => void,
): Promise<Document[]> {
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));
  const { data } = await api.post<Document[]>(`/project/${projectId}/documents`, formData, {
    onUploadProgress: (e) => {
      if (onProgress && e.total) onProgress(Math.round((e.loaded * 100) / e.total));
    },
  });
  return data;
}

export async function replaceDocument(
  documentId: number,
  file: File,
  onProgress?: (percent: number) => void,
): Promise<Document> {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await api.put<Document>(`/document/${documentId}`, formData, {
    onUploadProgress: (e) => {
      if (onProgress && e.total) onProgress(Math.round((e.loaded * 100) / e.total));
    },
  });
  return data;
}

export async function downloadDocument(documentId: number, filename: string): Promise<void> {
  const response = await api.get<Blob>(`/document/${documentId}`, { responseType: 'blob' });
  const url = URL.createObjectURL(response.data);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export const deleteDocument = async (documentId: number): Promise<void> => {
  await api.delete(`/document/${documentId}`);
};
