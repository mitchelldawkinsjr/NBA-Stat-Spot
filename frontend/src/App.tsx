import './App.css'
import { Link, Routes, Route } from 'react-router-dom'
import { GoodBetsDashboard } from './components/GoodBetsDashboard'
import { PlayerSearch } from './components/PlayerSearch'
import { FiltersPanel } from './components/FiltersPanel'
import { useState } from 'react'
import PlayerTrends from './pages/PlayerTrends'
import { EnhancedSuggest } from './components/EnhancedSuggest'

function ExplorePage() {
  const [player, setPlayer] = useState<{ id: number; name: string } | null>(null)
  const [filters, setFilters] = useState<any>({ lastN: 10 })
  return (
    <div>
      <h2 style={{ marginBottom: 8 }}>Explore Player Props</h2>
      <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 16 }}>
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
  return (
    <div style={{ padding: 16 }}>
      <div style={{ position: 'sticky', top: 0, zIndex: 20, background: '#ffffff', borderBottom: '1px solid #e5e7eb', margin: '-16px', padding: '12px 16px 10px 16px' }}>
        <div style={{ padding: '6px 8px', background: '#fff7e6', border: '1px solid #ffe58f', fontSize: 13, borderRadius: 6 }}>Disclaimer: Informational purposes only. Not financial advice.</div>
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginTop: 8 }}>
          <div>
            <h1 style={{ margin: 0 }}>NBA Stat Spot</h1>
            <p style={{ color: '#666', margin: '2px 0 0 0', fontSize: 14 }}>Lightweight player prop analysis with transparent rationale.</p>
          </div>
          <nav style={{ display: 'flex', gap: 12 }}>
            <Link to="/">Explore</Link>
            <Link to="/dashboard">Dashboard</Link>
            <Link to="/trends">Player Trends</Link>
          </nav>
        </div>
      </div>
      <div style={{ marginTop: 16 }}>
        <Routes>
          <Route path="/" element={<ExplorePage />} />
          <Route path="/dashboard" element={<GoodBetsDashboard />} />
          <Route path="/trends" element={<PlayerTrends />} />
          {/* Back-compat alias */}
          <Route path="/suggest" element={<ExplorePage />} />
        </Routes>
      </div>
    </div>
  )
}

export default App
