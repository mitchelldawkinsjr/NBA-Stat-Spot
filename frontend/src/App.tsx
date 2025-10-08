import { useState } from 'react'
import './App.css'
import { Link } from 'react-router-dom'

function App() {
  return (
    <div style={{ padding: 16 }}>
      <h1>NBA Stat Spot</h1>
      <p>Good Bets for Upcoming Games (MVP)</p>
      <nav style={{ display: 'flex', gap: 12 }}>
        <Link to="/">Dashboard</Link>
        <Link to="/suggest">Suggest Props</Link>
      </nav>
    </div>
  )
}

export default App
