import { type ReactNode, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useSeason } from '../context/SeasonContext'

export default function SliceProLayout({ children }: { children: ReactNode }) {
  const { pathname } = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const nav = [
    { to: '/dashboard', label: 'Dashboard' },
    { to: '/explore', label: 'Explore' },
    { to: '/parlay', label: 'Parlay' },
    { to: '/bets', label: 'Bet Tracker' },
    { to: '/admin', label: 'Admin' },
  ]

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Top bar styled like Sliced Pro */}
      <header className="sticky top-0 z-40 bg-white border-b border-slate-200">
        <div className="mx-auto max-w-screen-2xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-[60px] items-center justify-between">
            <div className="flex items-center gap-2">
              <button onClick={() => setSidebarOpen(!sidebarOpen)} className="md:hidden inline-flex items-center justify-center rounded-md p-2 text-gray-600 hover:bg-gray-100" aria-label="Toggle menu">
                <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor"><path d="M4 6h16v2H4V6Zm0 5h16v2H4v-2Zm0 5h16v2H4v-2Z"/></svg>
              </button>
              <Link to="/" className="inline-flex items-center gap-2">
                <span className="text-base sm:text-lg font-bold text-slate-800">NBA Stat Spot</span>
                <span className="hidden sm:inline text-xs text-slate-500">Sliced Pro Layout</span>
              </Link>
            </div>
            <nav className="hidden md:flex items-center gap-2" role="navigation" aria-label="Primary">
              {nav.map(n => (
                <Link key={n.to} to={n.to} className={`px-3 py-2 rounded-md text-sm font-medium transition-colors ${pathname.startsWith(n.to) ? 'text-purple-700 bg-purple-50' : 'text-slate-700 hover:text-purple-700 hover:bg-purple-50'}`}>{n.label}</Link>
              ))}
            </nav>
            <div className="hidden md:block">
              <SeasonControl />
            </div>
          </div>
        </div>
      </header>

      {/* Sidebar (mobile) */}
      {sidebarOpen && (
        <div className="md:hidden fixed inset-0 z-30">
          <div className="absolute inset-0 bg-black/30" onClick={() => setSidebarOpen(false)} />
          <div className="absolute left-0 top-0 h-full w-72 bg-white shadow-xl ring-1 ring-black/5 p-4">
            <div className="flex items-center justify-between">
              <div className="text-sm font-semibold text-gray-900">Menu</div>
              <button onClick={() => setSidebarOpen(false)} className="p-2 text-gray-600 hover:bg-gray-100 rounded-md" aria-label="Close">
                <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor"><path d="M6.4 5l-.7.7L11.3 11l-5.6 5.3.7.7L12 11.7l5.6 5.6.7-.7-5.6-5.6 5.6-5.6-.7-.7L12 10.3 6.4 5z"/></svg>
              </button>
            </div>
            <div className="mt-3 space-y-1">
              {nav.map(n => (
                <Link key={n.to} to={n.to} onClick={() => setSidebarOpen(false)} className={`block px-3 py-2 rounded-md text-sm font-medium ${pathname.startsWith(n.to) ? 'text-blue-700 bg-blue-50' : 'text-gray-700 hover:text-blue-700 hover:bg-blue-50'}`}>{n.label}</Link>
              ))}
            </div>
            {/* Season Control in Mobile Sidebar */}
            <div className="mt-4 pt-4 border-t border-gray-200">
              <div className="px-3">
                <div className="text-xs font-semibold text-gray-500 mb-2">Season</div>
                <SeasonControl isMobile={true} />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Content */}
      <main className="mx-auto max-w-screen-2xl p-2 sm:p-4 space-y-4 detached-content">
        {children}
      </main>
    </div>
  )
}

function SeasonControl({ isMobile = false }: { isMobile?: boolean }) {
  const { season, setSeason } = useSeason()
  if (isMobile) {
    return (
      <input 
        value={season} 
        onChange={(e) => setSeason(e.target.value)} 
        placeholder="2025-26" 
        className="w-full px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600/20" 
      />
    )
  }
  return (
    <div className="flex items-center gap-2 ml-2 pl-2 border-l border-gray-200">
      <span className="text-xs text-gray-500">Season</span>
      <input value={season} onChange={(e) => setSeason(e.target.value)} placeholder="2025-26" className="px-3 py-2 rounded-lg border border-gray-300 text-sm w-28 focus:outline-none focus:ring-2 focus:ring-blue-600/20" />
    </div>
  )
}


