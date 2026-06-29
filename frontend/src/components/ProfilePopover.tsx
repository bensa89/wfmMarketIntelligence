import { useState, useRef, useEffect } from 'react';
import { User, KeyRound, LogOut } from 'lucide-react';
import { apiPut } from '../api/client';
import { useCurrentUser } from '../hooks/useCurrentUser';

interface Props {
  onLogout: () => void;
}

function ChangePasswordModal({ onClose }: { onClose: () => void }) {
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (next !== confirm) { setError('Passwörter stimmen nicht überein'); return; }
    if (next.length < 6) { setError('Passwort muss mindestens 6 Zeichen haben'); return; }
    setLoading(true);
    setError('');
    try {
      await apiPut('/users/me/password', { current_password: current, new_password: next });
      setSuccess(true);
      setTimeout(onClose, 1200);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Fehler beim Ändern des Passworts');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center px-4">
      <div className="bg-app-card border border-app-border rounded-2xl p-6 w-full max-w-sm shadow-lg">
        <h2 className="text-base font-semibold text-ink mb-4">Passwort ändern</h2>
        {success ? (
          <p className="text-sm text-signal-high">Passwort erfolgreich geändert.</p>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-3">
            <div>
              <label className="block text-xs text-ink-muted mb-1">Aktuelles Passwort</label>
              <input type="password" value={current} onChange={e => setCurrent(e.target.value)}
                className="input-field w-full" autoComplete="current-password" />
            </div>
            <div>
              <label className="block text-xs text-ink-muted mb-1">Neues Passwort</label>
              <input type="password" value={next} onChange={e => setNext(e.target.value)}
                className="input-field w-full" autoComplete="new-password" />
            </div>
            <div>
              <label className="block text-xs text-ink-muted mb-1">Bestätigen</label>
              <input type="password" value={confirm} onChange={e => setConfirm(e.target.value)}
                className="input-field w-full" autoComplete="new-password" />
            </div>
            {error && <p className="text-xs text-signal-low">{error}</p>}
            <div className="flex gap-2 pt-1">
              <button type="button" onClick={onClose}
                className="flex-1 px-3 py-2 text-sm rounded-lg border border-app-border text-ink-muted hover:bg-white/5">
                Abbrechen
              </button>
              <button type="submit" disabled={loading || !current || !next || !confirm}
                className="flex-1 btn-primary text-sm disabled:opacity-50">
                {loading ? 'Speichern...' : 'Speichern'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

export default function ProfilePopover({ onLogout }: Props) {
  const currentUser = useCurrentUser();
  const [open, setOpen] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  return (
    <>
      <div ref={ref} className="px-2 py-3 relative" style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
        <button
          onClick={() => setOpen(o => !o)}
          className="flex items-center gap-2 w-full px-2 py-[7px] rounded-[7px] text-[12px] font-medium transition-colors hover:bg-white/5"
          style={{ color: 'rgba(248,250,252,0.55)' }}
        >
          <User size={14} className="flex-shrink-0" />
          <span className="truncate flex-1 text-left">{currentUser?.username ?? 'Profil'}</span>
        </button>

        {open && (
          <div
            className="absolute bottom-full left-2 right-2 mb-1 rounded-[10px] border border-app-border shadow-lg overflow-hidden"
            style={{ background: '#1e293b' }}
          >
            <div className="px-3 py-2 border-b border-white/5">
              <p className="text-[12px] font-medium text-slate-200 truncate">{currentUser?.username}</p>
              <p className="text-[10px] mt-0.5" style={{ color: 'rgba(248,250,252,0.35)' }}>
                {currentUser?.role === 'admin' ? 'Administrator' : 'User'}
              </p>
            </div>
            <button
              onClick={() => { setOpen(false); setShowPasswordModal(true); }}
              className="flex items-center gap-2 w-full px-3 py-2 text-[12px] text-left hover:bg-white/5 transition-colors"
              style={{ color: 'rgba(248,250,252,0.55)' }}
            >
              <KeyRound size={13} />
              Passwort ändern
            </button>
            <button
              onClick={onLogout}
              className="flex items-center gap-2 w-full px-3 py-2 text-[12px] text-left hover:bg-white/5 transition-colors"
              style={{ color: 'rgba(248,250,252,0.45)' }}
            >
              <LogOut size={13} />
              Abmelden
            </button>
          </div>
        )}
      </div>

      {showPasswordModal && <ChangePasswordModal onClose={() => setShowPasswordModal(false)} />}
    </>
  );
}
