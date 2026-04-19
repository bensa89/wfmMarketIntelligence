interface TagListProps {
  items: string[];
  label?: string;
}

export default function TagList({ items, label }: TagListProps) {
  if (!items || items.length === 0) {
    return (
      <div>
        {label && <span className="text-xs text-ink-muted">{label}:</span>}
        <span className="text-xs text-ink-muted italic">None</span>
      </div>
    );
  }

  return (
    <div>
      {label && <span className="text-xs text-ink-muted block mb-1">{label}:</span>}
      <div className="flex flex-wrap gap-1.5">
        {items.map((item, i) => (
          <span
            key={i}
            className="text-xs px-2 py-0.5 rounded bg-app-bg border border-app-border text-ink"
          >
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}
