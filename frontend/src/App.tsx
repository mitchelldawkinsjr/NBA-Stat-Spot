import './App.css'
import { Routes, Route, Link } from 'react-router-dom'
import { GoodBetsDashboard } from './components/GoodBetsDashboard'
import { PlayerSearch } from './components/PlayerSearch'
import { FiltersPanel } from './components/FiltersPanel'
import { useState } from 'react'
// Trends removed per request
import { EnhancedSuggest } from './components/EnhancedSuggest'
import { ParlayBuilder } from './components/ParlayBuilder'
import { useSeason } from './context/SeasonContext'
// Flowbite layout removed

function ExplorePage() {
  const [player, setPlayer] = useState<{ id: number; name: string } | null>(null)
  const { season } = useSeason()
  const [filters, setFilters] = useState<any>({ lastN: 10, season })
  return (
    <div>
      <h2 style={{ marginBottom: 8 }}>Explore Player Props</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <FiltersPanel value={filters} onChange={setFilters} />
          <div style={{ marginTop: 8, fontSize: 12, color: '#6b7280' }}>Tip: Enter market lines (e.g. PTS 24.5) to compute edge and confidence.</div>
        </div>
        <div>
          <PlayerSearch onSelect={setPlayer} />
          <div style={{ height: 12 }} />
          <EnhancedSuggest player={player} filters={filters} />
        </div>
      </div>
    </div>
  )
}

function App() {
  const { season, setSeason } = useSeason()
  return (
    <div className="px-4 md:px-6">
      <div style={{ position: 'sticky', top: 0, zIndex: 20, background: '#ffffff', borderBottom: '1px solid #e5e7eb', marginLeft: '-16px', marginRight: '-16px', padding: '12px 16px 10px 16px' }}>
        <div style={{ padding: '6px 8px', background: '#fff7e6', border: '1px solid #ffe58f', fontSize: 13, borderRadius: 6 }}>Disclaimer: Informational purposes only. Not financial advice.</div>
        <div className="flex flex-col md:flex-row md:items-baseline md:justify-between mt-2 gap-2">
          <div>
            <h1 style={{ margin: 0 }}>NBA Stat Spot</h1>
            <p style={{ color: '#666', margin: '2px 0 0 0', fontSize: 14 }}>Lightweight player prop analysis with transparent rationale.</p>
          </div>
          <nav className="flex gap-3 items-center">
            <Link to="/dashboard" className="px-2 py-1 rounded hover:bg-gray-100">Dashboard</Link>
            <Link to="/explore" className="px-2 py-1 rounded hover:bg-gray-100">Explore</Link>
            <Link to="/parlay" className="px-2 py-1 rounded hover:bg-gray-100">Parlay</Link>
            <div className="hidden sm:flex items-center gap-2">
              <span style={{ fontSize: 12, color: '#6b7280' }}>Season</span>
              <input value={season} onChange={(e) => setSeason(e.target.value)} placeholder="2025-26" className="px-2 py-1 rounded border border-gray-300" style={{ width: 100 }} />
            </div>
          </nav>
        </div>
      </div>
      <div className="max-w-screen-2xl mx-auto px-0 md:px-0 mt-4">
        <Routes>
          <Route path="/" element={<GoodBetsDashboard />} />
          <Route path="/dashboard" element={<GoodBetsDashboard />} />
          <Route path="/explore" element={<ExplorePage />} />
          <Route path="/parlay" element={<ParlayBuilder />} />
          {/* Back-compat alias */}
          <Route path="/suggest" element={<ExplorePage />} />
        </Routes>
      </div>
    </div>
  )
}

export default App
