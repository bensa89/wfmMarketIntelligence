import {
  Package,
  Brain,
  Handshake,
  Compass,
  Target,
  Calendar,
  UserPlus,
  HelpCircle,
} from 'lucide-react';
import type { SignalType } from '../types';

const iconMap: Record<SignalType, React.ComponentType<{ size?: number }>> = {
  product_update:              Package,
  ai_announcement:             Brain,
  partnership:                 Handshake,
  positioning_change:          Compass,
  target_market_change:        Target,
  event_or_thought_leadership: Calendar,
  hiring_signal:               UserPlus,
  other:                       HelpCircle,
};

export const labelMap: Record<SignalType, string> = {
  product_update:              'Product Update',
  ai_announcement:             'AI Announcement',
  partnership:                 'Partnership',
  positioning_change:          'Positioning',
  target_market_change:        'Market Shift',
  event_or_thought_leadership: 'Thought Leadership',
  hiring_signal:               'Hiring Signal',
  other:                       'Other',
};

// Explicit chip styles — avoids dynamic class generation issues with Tailwind JIT
const chipStyles: Record<SignalType, { bg: string; color: string }> = {
  product_update:              { bg: '#f0fdf4', color: '#15803d' },
  ai_announcement:             { bg: '#f5f3ff', color: '#6d28d9' },
  partnership:                 { bg: '#fff7ed', color: '#c2410c' },
  positioning_change:          { bg: '#fdf4ff', color: '#86198f' },
  target_market_change:        { bg: '#fff1f2', color: '#be123c' },
  event_or_thought_leadership: { bg: '#f0fdfa', color: '#0f766e' },
  hiring_signal:               { bg: '#eff6ff', color: '#1d4ed8' },
  other:                       { bg: '#f4f4f5', color: '#52525b' },
};

interface SignalTypeIconProps {
  type: SignalType;
  /** 'chip' renders a colored pill label; 'icon' renders icon only */
  variant?: 'chip' | 'icon';
  size?: number;
}

export default function SignalTypeIcon({ type, variant = 'chip', size = 14 }: SignalTypeIconProps) {
  const Icon = iconMap[type];
  const { bg, color } = chipStyles[type];

  if (variant === 'icon') {
    return <Icon size={size} style={{ color }} />;
  }

  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-semibold"
      style={{ background: bg, color }}
    >
      <Icon size={11} />
      {labelMap[type]}
    </span>
  );
}
