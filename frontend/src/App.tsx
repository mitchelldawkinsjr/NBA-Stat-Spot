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
      <h1>NBA Stat Spot</h1>
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
