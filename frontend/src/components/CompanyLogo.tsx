import { getCompanyColor } from './dashboard/CompanyColorMap';

interface CompanyLogoProps {
  name: string;
  slug: string;
  logo_path?: string | null;
  size: 'sm' | 'md' | 'lg';
  companyId?: string; // used for color lookup when no logo
}

const SIZE_PX: Record<'sm' | 'md' | 'lg', number> = {
  sm: 24,
  md: 36,
  lg: 56,
};

const FONT_SIZE: Record<'sm' | 'md' | 'lg', string> = {
  sm: '9px',
  md: '13px',
  lg: '20px',
};

export default function CompanyLogo({ name, slug, logo_path, size, companyId }: CompanyLogoProps) {
  const px = SIZE_PX[size];
  const initials = name.slice(0, 2).toUpperCase();
  const bgColor = getCompanyColor(companyId ?? slug);

  const containerStyle: React.CSSProperties = {
    width: px,
    height: px,
    minWidth: px,
    borderRadius: 6,
    overflow: 'hidden',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  };

  if (logo_path) {
    return (
      <div
        style={{
          ...containerStyle,
          background: '#fff',
          boxShadow: '0 0 0 1px rgba(0,0,0,0.08)',
          padding: size === 'lg' ? 4 : 2,
        }}
      >
        <img
          src={`/static/${logo_path}`}
          alt={name}
          style={{ width: '100%', height: '100%', objectFit: 'contain' }}
          onError={(e) => {
            (e.target as HTMLImageElement).style.display = 'none';
          }}
        />
      </div>
    );
  }

  return (
    <div
      style={{
        ...containerStyle,
        background: bgColor,
        color: '#fff',
        fontSize: FONT_SIZE[size],
        fontWeight: 700,
        letterSpacing: '0.02em',
      }}
    >
      {initials}
    </div>
  );
}
