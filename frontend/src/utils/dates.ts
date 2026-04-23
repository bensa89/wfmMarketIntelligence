export function formatDistanceToNow(dateStr: string | null | undefined): string {
  if (!dateStr) return 'unknown date';
  const diff = Date.now() - new Date(dateStr).getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  if (days === 0) return 'today';
  if (days === 1) return '1 day ago';
  if (days < 30) return `${days} days ago`;
  const months = Math.floor(days / 30);
  if (months === 1) return '1 month ago';
  return `${months} months ago`;
}

export function formatPublishedAt(publishedAt: string | null): {
  label: string;
  isUnknown: boolean;
} {
  if (!publishedAt) return { label: 'Datum unbekannt', isUnknown: true };
  const date = new Date(publishedAt);
  if (isNaN(date.getTime())) return { label: 'Datum unbekannt', isUnknown: true };
  return {
    label: date.toLocaleDateString('de-DE'),
    isUnknown: false,
  };
}

export function formatAbsolute(dateStr: string | null | undefined): string {
  if (!dateStr) return '–';
  const date = new Date(dateStr);
  if (isNaN(date.getTime())) return '–';
  return date.toLocaleString('de-DE', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}
