import type { SignalFeedItem } from '../../types/intelligence';

interface Props {
  item: SignalFeedItem;
  onClose: () => void;
}

export default function SignalDetailDrawer({ onClose }: Props) {
  return <div className="fixed inset-0 bg-black/50 z-50" onClick={onClose} />;
}
