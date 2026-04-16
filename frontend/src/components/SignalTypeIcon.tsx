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
  product_update: Package,
  ai_announcement: Brain,
  partnership: Handshake,
  positioning_change: Compass,
  target_market_change: Target,
  event_or_thought_leadership: Calendar,
  hiring_signal: UserPlus,
  other: HelpCircle,
};

const labelMap: Record<SignalType, string> = {
  product_update: 'Product Update',
  ai_announcement: 'AI Announcement',
  partnership: 'Partnership',
  positioning_change: 'Positioning Change',
  target_market_change: 'Market Shift',
  event_or_thought_leadership: 'Thought Leadership',
  hiring_signal: 'Hiring Signal',
  other: 'Other',
};

interface SignalTypeIconProps {
  type: SignalType;
  showLabel?: boolean;
  size?: number;
}

export default function SignalTypeIcon({ type, showLabel = true, size = 16 }: SignalTypeIconProps) {
  const Icon = iconMap[type];
  const colorClass = `text-type-${type}`;

  return (
    <span className="inline-flex items-center gap-1.5">
      <Icon size={size} className={colorClass} />
      {showLabel && <span className={`text-sm ${colorClass}`}>{labelMap[type]}</span>}
    </span>
  );
}

export { labelMap };
