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
      <h2>Explore Player Props</h2>
      <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 16 }}>
        <div><FiltersPanel value={filters} onChange={setFilters} /></div>
        <div><PlayerSearch onSelect={setPlayer} />
          <div style={{ height: 12 }} />
          <EnhancedSuggest player={player} filters={filters} /></div>
      </div>
    </div>
  )
}

function App() {
  return (
    <div style={{ padding: 16 }}>
      <div style={{ padding: '8px', background: '#fff7e6', border: '1px solid #ffe58f', marginBottom: '12px', fontSize: 13 }}>Disclaimer: Informational purposes only. Not financial advice.</div>
      <h1>NBA Stat Spot</h1>
      <p style={{ color: '#666', margin: '0 0 12px 0' }}>Lightweight player prop analysis with transparent rationale.</p>
      <nav style={{ display: 'flex', gap: 12 }}>
        <Link to="/">Explore</Link>
        <Link to="/dashboard">Dashboard</Link>
        <Link to="/trends">Player Trends</Link>
      </nav>
      <div style={{ marginTop: 12 }}>
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
