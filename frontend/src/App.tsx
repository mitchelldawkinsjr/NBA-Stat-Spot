import './App.css'
import { Link, Routes, Route } from 'react-router-dom'
import { GoodBetsDashboard } from './components/GoodBetsDashboard'

function SuggestPage() {
  return <div>Suggest Props (MVP)</div>
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
