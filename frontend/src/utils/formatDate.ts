// ISO -> "16.11.2026"
export function formatDate(iso: string): string {
  const d = new Date(iso);
  const day = String(d.getDate()).padStart(2, '0');
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const year = d.getFullYear();
  return `${day}.${month}.${year}`;
}

// Relative expiration string -> "Expires in 2 days" or "Expires in 5 hours"
export function formatExpiresIn(iso: string): string {
  const diffMs = new Date(iso).getTime() - Date.now();
  if (diffMs <= 0) return 'Expired';
  const hours = Math.ceil(diffMs / 3_600_000);
  if (hours >= 24) {
    const days = Math.round(hours / 24);
    return `Expires in ${days} ${days === 1 ? 'day' : 'days'}`;
  }
  return `Expires in ${hours} ${hours === 1 ? 'hour' : 'hours'}`;
}
