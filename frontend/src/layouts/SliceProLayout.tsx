import { type ReactNode, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useSeason } from '../context/SeasonContext'

const NAV_ITEMS = [
  { to: '/dashboard',   label: 'Dashboard',      icon: 'grid_view' },
  { to: '/explore',     label: 'Player Search',  icon: 'query_stats' },
  { to: '/over-under',  label: 'Over/Under',     icon: 'sensors' },
  { to: '/parlay',      label: 'Parlay Builder', icon: 'receipt_long' },
  { to: '/bets',        label: 'Bet Tracker',    icon: 'account_balance_wallet' },
  { to: '/accuracy',    label: 'Accuracy',       icon: 'verified' },
]

const BOTTOM_NAV = [
  { to: '/dashboard',  label: 'Home',   icon: 'grid_view' },
  { to: '/parlay',     label: 'Parlay', icon: 'receipt_long' },
  { to: '/over-under', label: 'Live',   icon: 'sensors' },
  { to: '/explore',    label: 'Player Search',  icon: 'query_stats' },
]

export default function SliceProLayout({ children }: { children: ReactNode }) {
  const { pathname } = useLocation()
  const [drawerOpen, setDrawerOpen] = useState(false)
  const { season, setSeason } = useSeason()

  const isActive = (to: string) =>
    pathname === to || (to !== '/' && pathname.startsWith(to))

  return (
    <div className="min-h-screen bg-background text-on-surface font-body">

      {/* ── Fixed Top Bar ── */}
      <header className="fixed top-0 w-full z-50 bg-[#131313] border-b border-[#353534]/30 backdrop-blur-xl flex justify-between items-center px-6 h-14">
        {/* Left: hamburger + logo */}
        <div className="flex items-center gap-4">
          <button
            onClick={() => setDrawerOpen(true)}
            className="lg:hidden p-2 hover:bg-surface-container-highest rounded transition-colors"
            aria-label="Open menu"
          >
            <span className="material-symbols-outlined text-on-surface">menu</span>
          </button>
          <Link to="/" className="text-xl font-black uppercase italic tracking-tighter text-primary-container">
            NBA Stat Spot
          </Link>
        </div>

        {/* Center: season input (desktop) */}
        <div className="hidden lg:flex items-center gap-3">
          <div className="flex items-center bg-surface-container-low px-3 py-1.5 rounded border border-[#353534]/50">
            <span className="material-symbols-outlined text-[16px] text-on-surface/50 mr-2">calendar_month</span>
            <input
              value={season}
              onChange={e => setSeason(e.target.value)}
              placeholder="2025-26"
              className="bg-transparent border-none text-xs font-bold focus:ring-0 placeholder:text-on-surface/30 w-20 p-0 text-on-surface uppercase"
            />
          </div>
        </div>

        {/* Right: search + icons */}
        <div className="flex items-center gap-1">
          <div className="hidden lg:flex items-center bg-surface-container-low px-3 py-1.5 rounded border border-[#353534]/50 mr-2">
            <span className="material-symbols-outlined text-[16px] text-on-surface/50 mr-2">search</span>
            <input
              className="bg-transparent border-none text-xs focus:ring-0 placeholder:text-on-surface/30 w-40 p-0 text-on-surface"
              placeholder="Search players, teams..."
            />
          </div>
          <Link
            to="/admin"
            className="p-2 hover:bg-surface-container-highest rounded transition-colors text-on-surface/40 hover:text-on-surface/70"
            title="Admin"
          >
            <span className="material-symbols-outlined text-[20px]">settings</span>
          </Link>
          <button className="p-2 hover:bg-surface-container-highest rounded transition-colors">
            <span className="material-symbols-outlined text-on-surface/70">notifications</span>
          </button>
          <button className="p-2 hover:bg-surface-container-highest rounded transition-colors">
            <span className="material-symbols-outlined text-on-surface/70">account_circle</span>
          </button>
        </div>
      </header>

      {/* ── Desktop Sidebar ── */}
      <aside className="hidden lg:flex flex-col fixed left-0 top-0 h-full w-64 bg-[#0e0e0e] z-40 pt-14 pb-8 shadow-2xl shadow-black/50">
        {/* Ledger branding */}
        <div className="px-6 py-6 border-b border-[#353534]/20">
          <p className="text-[10px] font-black text-primary-container uppercase tracking-widest">Performance Ledger</p>
          <p className="text-[9px] text-on-surface/40 uppercase tracking-widest mt-0.5">Pro Tier Access</p>
        </div>

        {/* Nav links */}
        <nav className="flex-1 pt-2 space-y-0.5">
          {NAV_ITEMS.map(item => (
            <Link
              key={item.to}
              to={item.to}
              className={`flex items-center gap-3 px-4 py-3 text-sm font-medium uppercase tracking-widest transition-all active:translate-x-1 ${
                isActive(item.to)
                  ? 'bg-surface-container-low text-primary-container rounded-r-lg border-l-4 border-primary-container'
                  : 'text-on-surface/50 hover:bg-surface-container-low hover:text-on-surface hover:opacity-100'
              }`}
            >
              <span className="material-symbols-outlined text-[20px]">{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          ))}
        </nav>

        {/* Bottom actions */}
        <div className="px-4 mt-auto space-y-3">
          <div className="pt-4 border-t border-[#353534]/30 space-y-1">
            <div className="flex items-center gap-2 px-4 py-2">
              <span className="text-[9px] text-on-surface/40 uppercase tracking-widest">Season</span>
              <input
                value={season}
                onChange={e => setSeason(e.target.value)}
                placeholder="2025-26"
                className="bg-transparent border-none text-[10px] font-bold text-primary-container focus:ring-0 p-0 w-16 uppercase"
              />
            </div>
            <Link
              to="/admin"
              className="flex items-center gap-3 px-4 py-2 text-[10px] text-on-surface/40 hover:text-on-surface/70 uppercase tracking-widest transition-colors"
            >
              <span className="material-symbols-outlined text-[16px]">admin_panel_settings</span>
              Admin
            </Link>
          </div>
        </div>
      </aside>

      {/* ── Mobile Drawer ── */}
      {drawerOpen && (
        <div className="fixed inset-0 z-[60] lg:hidden">
          <div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setDrawerOpen(false)}
          />
          <div className="absolute left-0 top-0 h-full w-72 bg-[#0e0e0e] flex flex-col shadow-2xl">
            {/* Drawer header */}
            <div className="flex items-center justify-between px-6 h-14 border-b border-[#353534]/30">
              <span className="text-lg font-black uppercase italic tracking-tighter text-primary-container">NBA Stat Spot</span>
              <button onClick={() => setDrawerOpen(false)} className="p-2 hover:bg-surface-container-highest rounded transition-colors">
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            <div className="px-4 py-4 border-b border-[#353534]/20">
              <p className="text-[10px] font-black text-primary-container uppercase tracking-widest">Performance Ledger</p>
              <p className="text-[9px] text-on-surface/40 uppercase tracking-widest mt-0.5">Pro Tier Access</p>
            </div>

            <nav className="flex-1 pt-2 space-y-0.5 overflow-y-auto">
              {NAV_ITEMS.map(item => (
                <Link
                  key={item.to}
                  to={item.to}
                  onClick={() => setDrawerOpen(false)}
                  className={`flex items-center gap-3 px-4 py-3 text-sm font-medium uppercase tracking-widest transition-all ${
                    isActive(item.to)
                      ? 'bg-surface-container-low text-primary-container rounded-r-lg border-l-4 border-primary-container'
                      : 'text-on-surface/50 hover:bg-surface-container-low hover:text-on-surface'
                  }`}
                >
                  <span className="material-symbols-outlined text-[20px]">{item.icon}</span>
                  <span>{item.label}</span>
                </Link>
              ))}
            </nav>

            <div className="p-4 border-t border-[#353534]/30 space-y-3">
              <div className="flex items-center gap-2 px-4 py-2">
                <span className="text-[9px] text-on-surface/40 uppercase tracking-widest">Season</span>
                <input
                  value={season}
                  onChange={e => setSeason(e.target.value)}
                  placeholder="2025-26"
                  className="bg-transparent border-none text-[10px] font-bold text-primary-container focus:ring-0 p-0 w-20 uppercase"
                />
              </div>
              <Link
                to="/admin"
                onClick={() => setDrawerOpen(false)}
                className="flex items-center gap-3 px-4 py-2 text-[10px] text-on-surface/40 hover:text-on-surface/70 uppercase tracking-widest transition-colors"
              >
                <span className="material-symbols-outlined text-[16px]">admin_panel_settings</span>
                Admin
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* ── Main Content ── */}
      <main className="lg:ml-64 pt-14 pb-20 lg:pb-0 min-h-screen bg-background">
        {children}
      </main>

      {/* ── Mobile Bottom Nav ── */}
      <nav className="fixed bottom-0 w-full flex justify-around items-center px-2 py-3 bg-[#131313]/90 backdrop-blur-md border-t border-[#353534]/30 lg:hidden z-50 shadow-[0_-4px_20px_rgba(0,0,0,0.5)]">
        {BOTTOM_NAV.map(item => {
          const active = isActive(item.to)
          return (
            <Link
              key={item.to}
              to={item.to}
              className={`flex flex-col items-center justify-center px-4 py-1.5 rounded-xl transition-all ${
                active
                  ? 'text-primary-container bg-primary-container/10 scale-110'
                  : 'text-on-surface/60'
              }`}
            >
              <span className="material-symbols-outlined text-[22px]">{item.icon}</span>
              <span className="text-[9px] font-bold uppercase tracking-widest mt-0.5">{item.label}</span>
            </Link>
          )
        })}
      </nav>
    </div>
  )
}
