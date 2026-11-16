export const ALLOWED_EXTENSIONS = ['.pdf', '.docx', '.png', '.jpg', '.jpeg'];
export const ACCEPT_ATTR = ALLOWED_EXTENSIONS.join(',');

export type FileKind = 'pdf' | 'doc' | 'image' | 'other';

export function getFileKind(filename: string): FileKind {
  const ext = filename.slice(filename.lastIndexOf('.')).toLowerCase();
  if (ext === '.pdf') return 'pdf';
  if (ext === '.docx') return 'doc';
  if (['.png', '.jpg', '.jpeg'].includes(ext)) return 'image';
  return 'other';
}

export function isAllowedFile(file: File): boolean {
  const name = file.name.toLowerCase();
  return ALLOWED_EXTENSIONS.some((ext) => name.endsWith(ext));
}
