const COMPANY_COLORS = [
  '#7c3aed',
  '#2563eb',
  '#10b981',
  '#f59e0b',
  '#ef4444',
  '#ec4899',
  '#06b6d4',
  '#84cc16',
];

const colorMap = new Map<string, string>();

export function getCompanyColor(companyId: string): string {
  if (colorMap.has(companyId)) return colorMap.get(companyId)!;
  const index = colorMap.size % COMPANY_COLORS.length;
  const color = COMPANY_COLORS[index];
  colorMap.set(companyId, color);
  return color;
}

export function resetCompanyColors(): void {
  colorMap.clear();
}

export { COMPANY_COLORS };