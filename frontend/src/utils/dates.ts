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
