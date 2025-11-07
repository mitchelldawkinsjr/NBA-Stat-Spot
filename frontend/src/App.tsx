import { Routes, Route } from 'react-router-dom'
import { GoodBetsDashboard } from './components/GoodBetsDashboard'
import { ParlayBuilder } from './components/ParlayBuilder'
import { BetTracker } from './components/BetTracker'
import PlayerProfile from './pages/PlayerProfile'
import TeamProfile from './pages/TeamProfile'
import ExplorePage from './pages/ExplorePage'
import AdminDashboard from './pages/AdminDashboard'
import SliceProLayout from './layouts/SliceProLayout'
import { SnackbarProvider } from './context/SnackbarContext'
// Flowbite layout removed

function App() {
  return (
    <SnackbarProvider>
      <SliceProLayout>
          <Routes>
            <Route path="/" element={<GoodBetsDashboard />} />
            <Route path="/dashboard" element={<GoodBetsDashboard />} />
            <Route path="/explore" element={<ExplorePage />} />
            <Route path="/parlay" element={<ParlayBuilder />} />
            <Route path="/bets" element={<BetTracker />} />
            <Route path="/player/:id" element={<PlayerProfile />} />
            <Route path="/team/:id" element={<TeamProfile />} />
            <Route path="/admin" element={<AdminDashboard />} />
            {/* Back-compat alias */}
            <Route path="/suggest" element={<ExplorePage />} />
          </Routes>
      </SliceProLayout>
    </SnackbarProvider>
  )
}

export default App
