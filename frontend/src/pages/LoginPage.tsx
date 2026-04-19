import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { setCredentials, clearCredentials } from '../api/client';
import { useQueryClient } from '@tanstack/react-query';

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const qc = useQueryClient();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError('');

    setCredentials(username, password);

    try {
      const res = await fetch('/api/health', {
        headers: {
          Authorization: `Basic ${btoa(`${username}:${password}`)}`,
        },
      });
      if (res.ok) {
        qc.invalidateQueries();
        navigate('/');
      } else {
        clearCredentials();
        setError('Invalid credentials');
      }
    } catch {
      setError('Cannot connect to server');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-dark-bg flex items-center justify-center">
      <div className="card w-96">
        <h1 className="text-xl font-bold mb-1">WFM Intel</h1>
        <p className="text-sm text-dark-muted mb-6">Market Intelligence Hub</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-dark-muted mb-1">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="input-field w-full"
              autoComplete="username"
            />
          </div>
          <div>
            <label className="block text-sm text-dark-muted mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input-field w-full"
              autoComplete="current-password"
            />
          </div>
          {error && <p className="text-sm text-signal-low">{error}</p>}
          <button
            type="submit"
            disabled={loading || !username || !password}
            className="btn-primary w-full disabled:opacity-50"
          >
            {loading ? 'Connecting...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
}
