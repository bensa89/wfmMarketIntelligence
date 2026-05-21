import { useSignalFeedItem } from '../../hooks/useSignalsFeed';
import SignalDetailDrawer from '../signals/SignalDetailDrawer';

interface Props {
  signalId: string | null;
  onClose: () => void;
}

export function ScorecardSignalDrawer({ signalId, onClose }: Props) {
  const { data: item } = useSignalFeedItem(signalId);
  if (!signalId || !item) return null;
  return <SignalDetailDrawer item={item} onClose={onClose} />;
}
