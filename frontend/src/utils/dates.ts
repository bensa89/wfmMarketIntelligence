export function formatPublishedAt(publishedAt: string | null): {
  label: string;
  isUnknown: boolean;
} {
  if (!publishedAt) return { label: 'Datum unbekannt', isUnknown: true };
  return {
    label: new Date(publishedAt).toLocaleDateString('de-DE'),
    isUnknown: false,
  };
}
