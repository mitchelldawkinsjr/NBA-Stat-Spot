import './App.css'
import { Link, Routes, Route } from 'react-router-dom'
import { GoodBetsDashboard } from './components/GoodBetsDashboard'
import { PlayerSearch } from './components/PlayerSearch'
import { SuggestionsTable } from './components/SuggestionsTable'
import { useState } from 'react'

function SuggestPage() {
  const [player, setPlayer] = useState<{ id: number; name: string } | null>(null)
  return (
    <div>
      <h2>Suggest Props</h2>
      <PlayerSearch onSelect={setPlayer} />
      <div style={{ marginTop: 12 }} />
      <SuggestionsTable player={player} />
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
        <Link to="/">Dashboard</Link>
        <Link to="/suggest">Suggest Props</Link>
      </nav>
      <div style={{ marginTop: 12 }}>
        <Routes>
          <Route path="/" element={<GoodBetsDashboard />} />
          <Route path="/suggest" element={<SuggestPage />} />
        </Routes>
      </div>
    </div>
  )
}

export default App
