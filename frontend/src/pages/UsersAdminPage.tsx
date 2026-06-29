import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Trash2 } from 'lucide-react';
import { apiGet, apiPost, apiPut, apiDelete } from '../api/client';

interface User {
  id: number;
  username: string;
  role: 'admin' | 'user';
  is_active: boolean;
  created_at: string;
}

interface CreateUserPayload {
  username: string;
  password: string;
  role: 'admin' | 'user';
}

function useUsers() {
  return useQuery<User[]>({ queryKey: ['users'], queryFn: () => apiGet('/users') });
}

function CreateUserModal({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<'admin' | 'user'>('user');
  const [error, setError] = useState('');

  const create = useMutation({
    mutationFn: (payload: CreateUserPayload) => apiPost<User>('/users', payload),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['users'] }); onClose(); },
    onError: (e: Error) => setError(e.message),
  });

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center px-4">
      <div className="bg-app-card border border-app-border rounded-2xl p-6 w-full max-w-sm shadow-lg">
        <h2 className="text-base font-semibold text-ink mb-4">Neuer Benutzer</h2>
        <form onSubmit={e => { e.preventDefault(); create.mutate({ username, password, role }); }} className="space-y-3">
          <div>
            <label className="block text-xs text-ink-muted mb-1">Benutzername</label>
            <input value={username} onChange={e => setUsername(e.target.value)} className="input-field w-full" />
          </div>
          <div>
            <label className="block text-xs text-ink-muted mb-1">Passwort</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} className="input-field w-full" />
          </div>
          <div>
            <label className="block text-xs text-ink-muted mb-1">Rolle</label>
            <select value={role} onChange={e => setRole(e.target.value as 'admin' | 'user')} className="input-field w-full">
              <option value="user">User</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          {error && <p className="text-xs text-signal-low">{error}</p>}
          <div className="flex gap-2 pt-1">
            <button type="button" onClick={onClose}
              className="flex-1 px-3 py-2 text-sm rounded-lg border border-app-border text-ink-muted hover:bg-white/5">
              Abbrechen
            </button>
            <button type="submit" disabled={!username || !password || create.isPending}
              className="flex-1 btn-primary text-sm disabled:opacity-50">
              {create.isPending ? 'Erstellen...' : 'Erstellen'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function UsersAdminPage() {
  const { data: users = [], isLoading } = useUsers();
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [error, setError] = useState('');

  const updateRole = useMutation({
    mutationFn: ({ id, role }: { id: number; role: string }) => apiPut<User>(`/users/${id}`, { role }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
    onError: (e: Error) => setError(e.message),
  });

  const toggleActive = useMutation({
    mutationFn: ({ id, is_active }: { id: number; is_active: boolean }) =>
      apiPut<User>(`/users/${id}`, { is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
    onError: (e: Error) => setError(e.message),
  });

  const deleteUser = useMutation({
    mutationFn: (id: number) => apiDelete(`/users/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
    onError: (e: Error) => setError(e.message),
  });

  return (
    <div className="p-4 md:p-6 max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-ink">Benutzerverwaltung</h1>
        <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2">
          <Plus size={16} /> Neuer Benutzer
        </button>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded bg-signal-low/10 text-signal-low text-sm">{error}</div>
      )}

      {isLoading ? (
        <p className="text-ink-muted text-sm">Lade...</p>
      ) : (
        <div className="bg-app-card border border-app-border rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-app-border">
                <th className="text-left px-4 py-3 text-xs font-semibold text-ink-muted uppercase tracking-wider">Benutzer</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-ink-muted uppercase tracking-wider">Rolle</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-ink-muted uppercase tracking-wider">Status</th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-ink-muted uppercase tracking-wider">Erstellt</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {users.map(user => (
                <tr key={user.id} className="border-b border-app-border last:border-0 hover:bg-white/2">
                  <td className="px-4 py-3 font-medium text-ink">{user.username}</td>
                  <td className="px-4 py-3">
                    <select
                      value={user.role}
                      onChange={e => updateRole.mutate({ id: user.id, role: e.target.value })}
                      className="text-xs bg-transparent border border-app-border rounded px-2 py-1 text-ink"
                    >
                      <option value="user">User</option>
                      <option value="admin">Admin</option>
                    </select>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => toggleActive.mutate({ id: user.id, is_active: !user.is_active })}
                      className={`text-xs px-2 py-1 rounded font-medium ${
                        user.is_active
                          ? 'bg-green-900/30 text-green-400'
                          : 'bg-red-900/30 text-red-400'
                      }`}
                    >
                      {user.is_active ? 'Aktiv' : 'Inaktiv'}
                    </button>
                  </td>
                  <td className="px-4 py-3 text-ink-muted text-xs">
                    {new Date(user.created_at).toLocaleDateString('de-DE')}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => { if (confirm(`${user.username} löschen?`)) deleteUser.mutate(user.id); }}
                      className="text-ink-muted hover:text-signal-low transition-colors"
                    >
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && <CreateUserModal onClose={() => setShowCreate(false)} />}
    </div>
  );
}
