import { NavLink, Outlet } from 'react-router-dom';
import {
  BarChart3,
  Users,
  TrendingUp,
  Calendar,
  Search,
  Settings,
  Globe,
  LogOut,
} from 'lucide-react';
import { hasCredentials, clearCredentials } from '../api/client';
import { useNavigate } from 'react-router-dom';

const navItems = [
  { to: '/', label: 'Dashboard', icon: BarChart3 },
  { to: '/competitors', label: 'Competitors', icon: Users },
  { to: '/trends', label: 'Market Trends', icon: TrendingUp },
  { to: '/digest', label: 'Weekly Digest', icon: Calendar },
  { to: '/search', label: 'Search', icon: Search },
  { to: '/admin/sources', label: 'Sources Admin', icon: Settings },
  { to: '/context', label: 'Company Context', icon: Globe },
];

export default function Layout() {
  const navigate = useNavigate();

  function handleLogout() {
    clearCredentials();
    navigate('/login');
  }

  if (!hasCredentials()) {
    navigate('/login');
    return null;
  }

  return (
    <div className="flex h-screen">
      <nav className="w-56 bg-dark-card border-r border-dark-border flex flex-col">
        <div className="p-4 border-b border-dark-border">
          <h1 className="text-lg font-bold text-dark-text">WFM Intel</h1>
          <p className="text-xs text-dark-muted">Market Intelligence Hub</p>
        </div>
        <div className="flex-1 py-2">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-2.5 text-sm transition-colors ${
                  isActive
                    ? 'bg-dark-accent/10 text-dark-accent border-r-2 border-dark-accent'
                    : 'text-dark-muted hover:text-dark-text hover:bg-dark-bg'
                }`
              }
            >
              <Icon size={18} />
              {label}
            </NavLink>
          ))}
        </div>
        <div className="p-4 border-t border-dark-border">
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 text-sm text-dark-muted hover:text-dark-text transition-colors"
          >
            <LogOut size={16} />
            Logout
          </button>
        </div>
      </nav>
      <main className="flex-1 overflow-auto p-6">
        <Outlet />
      </main>
    </div>
  );
}
