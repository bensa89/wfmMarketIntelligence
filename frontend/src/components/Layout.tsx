import { NavLink, Outlet } from 'react-router-dom';
import {
  LayoutDashboard,
  Users,
  TrendingUp,
  FileText,
  Settings,
  Search,
  Globe,
  LogOut,
  BarChart2,
  Zap,
} from 'lucide-react';
import { hasCredentials, clearCredentials } from '../api/client';
import { useNavigate } from 'react-router-dom';

const navSections = [
  {
    label: 'Intelligence',
    items: [
      { to: '/overview', label: 'Overview', icon: BarChart2 },
      { to: '/competitors', label: 'Competitors', icon: Users },
      { to: '/signals', label: 'Signals Feed', icon: Zap },
    ],
  },
  {
    label: 'Übersicht',
    items: [
      { to: '/', label: 'Dashboard', icon: LayoutDashboard },
      { to: '/trends', label: 'Markt-Trends', icon: TrendingUp },
    ],
  },
  {
    label: 'Berichte',
    items: [
      { to: '/digest', label: 'Weekly Digest', icon: FileText },
      { to: '/search', label: 'Suche', icon: Search },
    ],
  },
  {
    label: 'Admin',
    items: [
      { to: '/admin/sources', label: 'Quellen', icon: Settings },
      { to: '/context', label: 'Kontext', icon: Globe },
    ],
  },
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
    <div className="flex h-screen bg-app-bg">
      {/* ── Sidebar ── */}
      <nav
        className="w-56 flex flex-col flex-shrink-0"
        style={{ background: '#0f172a' }}
      >
        {/* Logo */}
        <div
          className="flex items-center gap-2.5 px-4 py-[18px]"
          style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}
        >
          <div
            className="w-7 h-7 rounded-[7px] flex items-center justify-center text-[11px] font-extrabold text-white flex-shrink-0"
            style={{ background: 'linear-gradient(135deg, #2563eb, #7c3aed)' }}
          >
            W
          </div>
          <div>
            <div className="text-[13px] font-semibold leading-none text-slate-50">WFM Intel</div>
            <div className="text-[9px] mt-0.5" style={{ color: 'rgba(248,250,252,0.3)' }}>
              Market Intelligence
            </div>
          </div>
        </div>

        {/* Nav sections */}
        <div className="flex-1 overflow-y-auto">
          {navSections.map((section) => (
            <div key={section.label} className="pt-3.5 pb-1 px-2">
              <p
                className="text-[9px] font-semibold uppercase px-2 mb-1 tracking-widest"
                style={{ color: 'rgba(248,250,252,0.20)' }}
              >
                {section.label}
              </p>
              {section.items.map(({ to, label, icon: Icon }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={to === '/'}
                  className={({ isActive }) =>
                    `flex items-center gap-2 px-2 py-[7px] rounded-[7px] text-[13px] font-medium mb-px transition-colors ${
                      isActive
                        ? 'text-[#93c5fd]'
                        : 'hover:bg-white/5 hover:text-slate-200'
                    }`
                  }
                  style={({ isActive }) => ({
                    background: isActive ? 'rgba(37,99,235,0.18)' : undefined,
                    color: isActive ? '#93c5fd' : 'rgba(248,250,252,0.45)',
                  })}
                >
                  <Icon size={15} className="flex-shrink-0" />
                  {label}
                </NavLink>
              ))}
            </div>
          ))}
        </div>

        {/* User footer */}
        <div
          className="px-2 py-3"
          style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}
        >
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 w-full px-2 py-[7px] rounded-[7px] text-[12px] font-medium transition-colors hover:bg-white/5"
            style={{ color: 'rgba(248,250,252,0.35)' }}
          >
            <LogOut size={14} />
            Logout
          </button>
        </div>
      </nav>

      {/* ── Main content ── */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
