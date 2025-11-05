import { useState } from 'react'
import { Link } from 'react-router-dom'

export default function AppLayout({ children }: { children: any }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      <nav className="fixed top-0 z-30 w-full border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-screen-2xl items-center justify-between px-4 py-2.5 md:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <button aria-label="Toggle sidebar" className="inline-flex items-center rounded-lg p-2 text-gray-500 hover:bg-gray-100 focus:outline-none md:hidden" onClick={() => setOpen((v) => !v)}>
              <svg className="h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" /></svg>
            </button>
            <span className="text-base font-semibold">NBA Stat Spot</span>
          </div>
          <div className="hidden items-center gap-4 md:flex">
            <Link to="/dashboard" className="rounded px-2 py-1 hover:bg-gray-100">Dashboard</Link>
            <Link to="/explore" className="rounded px-2 py-1 hover:bg-gray-100">Explore</Link>
            <Link to="/parlay" className="rounded px-2 py-1 hover:bg-gray-100">Parlay</Link>
          </div>
        </div>
      </nav>
      <div className="flex pt-[52px] min-h-screen">
        <aside className={`${open ? 'translate-x-0' : '-translate-x-full'} fixed left-0 top-[52px] z-20 h-[calc(100vh-52px)] w-64 border-r border-gray-200 bg-white transition-transform md:translate-x-0`}>
          <div className="h-full overflow-y-auto p-3">
            <ul className="space-y-1 text-sm">
              <li><Link className="block rounded px-3 py-2 hover:bg-gray-100" to="/dashboard">Dashboard</Link></li>
              <li><Link className="block rounded px-3 py-2 hover:bg-gray-100" to="/explore">Explore</Link></li>
              <li><Link className="block rounded px-3 py-2 hover:bg-gray-100" to="/parlay">Parlay Builder</Link></li>
            </ul>
          </div>
        </aside>
        <div className="w-full md:ml-64">
          <main className="max-w-screen-2xl mx-auto w-full px-4 py-4 md:px-6 lg:px-8 overflow-x-hidden">
            {children}
          </main>
        </div>
      </div>
    </div>
  )
}


