import { type ReactNode, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useSeason } from '../context/SeasonContext'
import { ThemeToggle } from '../components/ThemeToggle'

export default function SliceProLayout({ children }: { children: ReactNode }) {
  const { pathname } = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const nav = [
    { to: '/dashboard', label: 'Dashboard' },
    { to: '/explore', label: 'Explore' },
    { to: '/parlay', label: 'Parlay' },
    { to: '/bets', label: 'Bet Tracker' },
    { to: '/over-under', label: 'Over/Under' },
    { to: '/admin', label: 'Admin' },
  ]

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900 transition-colors duration-200">
      {/* Top bar styled like Sliced Pro */}
      <header className="sticky top-0 z-40 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 transition-colors duration-200">
        <div className="mx-auto max-w-screen-2xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-[60px] items-center justify-between gap-4">
            <div className="flex items-center gap-2 flex-shrink-0">
              <button 
                type="button"
                onClick={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  setSidebarOpen(!sidebarOpen)
                }} 
                className="inline-flex items-center justify-center rounded-md p-2 text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-slate-700 cursor-pointer relative z-50 transition-colors duration-200" 
                aria-label="Toggle menu"
              >
                <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M4 6h16v2H4V6Zm0 5h16v2H4v-2Zm0 5h16v2H4v-2Z"/>
                </svg>
              </button>
              <Link to="/" className="inline-flex items-center gap-2">
                <span className="text-base sm:text-lg font-bold text-slate-800 dark:text-slate-100 transition-colors duration-200">NBA Stat Spot</span>
                <span className="hidden sm:inline text-xs text-slate-500 dark:text-slate-400 transition-colors duration-200">Sliced Pro Layout</span>
              </Link>
            </div>
            {/* Desktop Navigation - hidden on mobile, visible on md+ */}
            <nav className="hidden md:flex items-center gap-2 flex-1 justify-center" role="navigation" aria-label="Primary">
              {nav.map(n => (
                <Link 
                  key={n.to} 
                  to={n.to} 
                  className={`px-3 py-2 rounded-md text-sm font-medium transition-colors whitespace-nowrap ${
                    pathname.startsWith(n.to) 
                      ? 'text-purple-700 bg-purple-50 dark:text-purple-300 dark:bg-purple-900/30' 
                      : 'text-slate-700 dark:text-slate-300 hover:text-purple-700 dark:hover:text-purple-300 hover:bg-purple-50 dark:hover:bg-purple-900/20'
                  }`}
                >
                  {n.label}
                </Link>
              ))}
            </nav>
            <div className="hidden md:flex items-center gap-2 flex-shrink-0">
              <ThemeToggle />
              <SeasonControl />
            </div>
          </div>
        </div>
      </header>

      {/* Sidebar - slides in from left */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-50">
          {/* Backdrop overlay */}
          <div 
            className="absolute inset-0 bg-black/30 transition-opacity" 
            onClick={() => setSidebarOpen(false)} 
          />
          {/* Sidebar panel - slides in from left */}
          <div className="absolute left-0 top-0 h-full w-72 bg-white dark:bg-slate-800 shadow-xl ring-1 ring-black/5 dark:ring-slate-700/50 p-4 transform transition-all duration-300 ease-in-out">
            <div className="flex items-center justify-between mb-4">
              <div className="text-sm font-semibold text-gray-900 dark:text-slate-100 transition-colors duration-200">Menu</div>
              <button 
                type="button"
                onClick={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  setSidebarOpen(false)
                }} 
                className="p-2 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-md cursor-pointer transition-colors duration-200" 
                aria-label="Close menu"
              >
                <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M6.4 5l-.7.7L11.3 11l-5.6 5.3.7.7L12 11.7l5.6 5.6.7-.7-5.6-5.6 5.6-5.6-.7-.7L12 10.3 6.4 5z"/>
                </svg>
              </button>
            </div>
            <div className="space-y-1">
              {nav.map(n => (
                <Link 
                  key={n.to} 
                  to={n.to} 
                  onClick={() => setSidebarOpen(false)} 
                  className={`block px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    pathname.startsWith(n.to) 
                      ? 'text-blue-700 bg-blue-50 dark:text-blue-300 dark:bg-blue-900/30' 
                      : 'text-gray-700 dark:text-gray-300 hover:text-blue-700 dark:hover:text-blue-300 hover:bg-blue-50 dark:hover:bg-blue-900/20'
                  }`}
                >
                  {n.label}
                </Link>
              ))}
            </div>
            {/* Theme Toggle in Mobile Sidebar */}
            <div className="mt-4 pt-4 border-t border-gray-200 dark:border-slate-700">
              <div className="px-3 flex items-center justify-between">
                <div className="text-xs font-semibold text-gray-500 dark:text-gray-400">Theme</div>
                <ThemeToggle />
              </div>
            </div>
            {/* Season Control in Mobile Sidebar */}
            <div className="mt-4 pt-4 border-t border-gray-200 dark:border-slate-700">
              <div className="px-3">
                <div className="text-xs font-semibold text-gray-500 dark:text-gray-400 mb-2">Season</div>
                <SeasonControl isMobile={true} />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Content */}
      <main className="mx-auto max-w-screen-2xl p-2 sm:p-4 space-y-4 detached-content bg-transparent dark:bg-transparent">
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
        className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-blue-600/20 dark:focus:ring-blue-400/20 transition-colors duration-200" 
      />
    )
  }
  return (
    <div className="flex items-center gap-2 ml-2 pl-2 border-l border-gray-200 dark:border-slate-700">
      <span className="text-xs text-gray-500 dark:text-gray-400 transition-colors duration-200">Season</span>
      <input 
        value={season} 
        onChange={(e) => setSeason(e.target.value)} 
        placeholder="2025-26" 
        className="px-3 py-2 rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-slate-100 text-sm w-28 focus:outline-none focus:ring-2 focus:ring-blue-600/20 dark:focus:ring-blue-400/20 transition-colors duration-200" 
      />
    </div>
  )
}


