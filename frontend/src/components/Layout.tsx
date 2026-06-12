import { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import {
  LayoutDashboard, Users, TrendingUp, FileText, Settings, Search,
  Globe, LogOut, BarChart2, Zap, BookOpen, Clock, Terminal, Menu, X, GitCommit,
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
      { to: '/admin/schedule', label: 'Automation', icon: Clock },
      { to: '/admin/logs', label: 'Logs', icon: Terminal },
      { to: '/context', label: 'Kontext', icon: Globe },
      { to: '/how-it-works', label: "Wie funktioniert's?", icon: BookOpen },
    ],
  },
];

function SidebarLogo() {
  return (
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
  );
}

function NavItems({ onNavClick }: { onNavClick?: () => void }) {
  return (
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
              onClick={onNavClick}
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
  );
}

function VersionBadge() {
  const commit = (import.meta.env.VITE_GIT_COMMIT as string | undefined) ?? 'dev';
  const buildTime = import.meta.env.VITE_BUILD_TIME as string | undefined;
  const shortHash = commit === 'dev' ? 'dev' : commit.slice(0, 7);

  let dateStr = '';
  if (buildTime) {
    const d = new Date(buildTime);
    dateStr = d.toLocaleDateString('de-DE', { day: '2-digit', month: 'short', year: 'numeric' })
      + ' · '
      + d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
  }

  return (
    <div className="px-4 pb-3" style={{ color: 'rgba(248,250,252,0.2)' }}>
      <div className="flex items-center gap-1 text-[10px]">
        <GitCommit size={10} className="flex-shrink-0" />
        <span>{shortHash}</span>
      </div>
      {dateStr && <div className="text-[10px] mt-0.5 pl-[14px]">{dateStr}</div>}
    </div>
  );
}

function LogoutButton({ onLogout }: { onLogout: () => void }) {
  return (
    <div className="px-2 py-3" style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
      <button
        onClick={onLogout}
        className="flex items-center gap-2 w-full px-2 py-[7px] rounded-[7px] text-[12px] font-medium transition-colors hover:bg-white/5"
        style={{ color: 'rgba(248,250,252,0.35)' }}
      >
        <LogOut size={14} />
        Logout
      </button>
    </div>
  );
}

export default function Layout() {
  const navigate = useNavigate();
  const [drawerOpen, setDrawerOpen] = useState(false);

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
      {/* ── Desktop Sidebar ── */}
      <nav
        className="hidden md:flex w-56 flex-col flex-shrink-0"
        style={{ background: '#0f172a' }}
      >
        <SidebarLogo />
        <NavItems />
        <LogoutButton onLogout={handleLogout} />
        <VersionBadge />
      </nav>

      {/* ── Mobile Header ── */}
      <header
        className="md:hidden fixed top-0 left-0 right-0 h-12 z-40 flex items-center px-4 gap-3"
        style={{ background: '#0f172a', borderBottom: '1px solid rgba(255,255,255,0.06)' }}
      >
        <button
          onClick={() => setDrawerOpen(true)}
          className="text-slate-400 hover:text-slate-200 p-1"
          aria-label="Navigation öffnen"
        >
          <Menu size={20} />
        </button>
        <div className="flex items-center gap-2">
          <div
            className="w-6 h-6 rounded-[6px] flex items-center justify-center text-[10px] font-extrabold text-white flex-shrink-0"
            style={{ background: 'linear-gradient(135deg, #2563eb, #7c3aed)' }}
          >
            W
          </div>
          <span className="text-[13px] font-semibold text-slate-50">WFM Intel</span>
        </div>
      </header>

      {/* ── Mobile Drawer Backdrop ── */}
      {drawerOpen && (
        <div
          className="md:hidden fixed inset-0 bg-black/60 z-40"
          onClick={() => setDrawerOpen(false)}
        />
      )}

      {/* ── Mobile Drawer ── */}
      <nav
        className={`md:hidden fixed inset-y-0 left-0 w-72 z-50 flex flex-col transition-transform duration-200 ${
          drawerOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
        style={{ background: '#0f172a' }}
      >
        <div
          className="flex items-center justify-between px-4 py-[18px]"
          style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}
        >
          <div className="flex items-center gap-2.5">
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
          <button
            onClick={() => setDrawerOpen(false)}
            className="text-slate-400 hover:text-slate-200 p-1"
            aria-label="Navigation schließen"
          >
            <X size={18} />
          </button>
        </div>
        <NavItems onNavClick={() => setDrawerOpen(false)} />
        <LogoutButton onLogout={handleLogout} />
        <VersionBadge />
      </nav>

      {/* ── Main content ── */}
      <main className="flex-1 overflow-auto pt-12 md:pt-0">
        <Outlet />
      </main>
    </div>
  );
}
