import { Link } from 'react-router-dom'

export default function HomePage() {
  return (
    <div style={{ padding: 16 }}>
      <h2>NBA Prop Bet Analyzer</h2>
      <p style={{ color: '#111827' }}>Explore player props, trends, and today's suggestions.</p>
      <div style={{ display: 'flex', gap: 12, marginTop: 12 }}>
        <Link to="/">Explore</Link>
        <Link to="/dashboard">Daily Props</Link>
        <Link to="/trends">Player Trends</Link>
      </div>
    </div>
  )
}
