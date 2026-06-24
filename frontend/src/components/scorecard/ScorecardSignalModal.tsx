import { useSignalFeedItem } from '../../hooks/useSignalsFeed';
import SignalDetailModal from '../signals/SignalDetailModal';

interface Props {
  signalId: string | null;
  onClose: () => void;
}

export function ScorecardSignalModal({ signalId, onClose }: Props) {
  const { data: item } = useSignalFeedItem(signalId);
  if (!signalId || !item) return null;
  return <SignalDetailModal item={item} onClose={onClose} />;
}
