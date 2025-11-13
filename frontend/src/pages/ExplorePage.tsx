import { useState, useEffect } from 'react'
import { useSeason } from '../context/SeasonContext'
import { PlayerSearch } from '../components/PlayerSearch'
import { FiltersPanel } from '../components/FiltersPanel'
import { EnhancedSuggest } from '../components/EnhancedSuggest'
import { Link } from 'react-router-dom'
import type { PropSuggestionsResponse } from '../types/api'
import { apiGet } from '../utils/api'

type Team = {
  id: number
  full_name: string
  abbreviation: string
  city: string
  nickname: string
  conference?: string
  division?: string
}

type Player = {
  id: number
  name: string
  position?: string
  jersey_number?: string
}

export default function ExplorePage() {
  const { season } = useSeason()
  const [player, setPlayer] = useState<{ id: number; name: string } | null>(null)
  const [teams, setTeams] = useState<Team[]>([])
  const [selectedTeam, setSelectedTeam] = useState<Team | null>(null)
  const [teamPlayers, setTeamPlayers] = useState<Player[]>([])
  const [loadingTeams, setLoadingTeams] = useState(false)
  const [loadingPlayers, setLoadingPlayers] = useState(false)
  const [viewMode, setViewMode] = useState<'search' | 'teams'>('search')
  const [filters, setFilters] = useState<any>({ lastN: 10, season, direction: 'over' })
  const [evaluateResult, setEvaluateResult] = useState<any>(null)

  // Fetch teams
  useEffect(() => {
    const fetchTeams = async () => {
      setLoadingTeams(true)
      try {
        const data = await apiGet('api/v1/teams')
        setTeams(data.items || [])
      } catch (error) {
        console.error('Failed to fetch teams:', error)
      } finally {
        setLoadingTeams(false)
      }
    }
    fetchTeams()
  }, [])

  // Fetch players for selected team
  useEffect(() => {
    if (!selectedTeam) {
      setTeamPlayers([])
      return
    }
    const fetchTeamPlayers = async () => {
      setLoadingPlayers(true)
      try {
        const data = await apiGet(`api/v1/teams/${selectedTeam.id}/players`)
        setTeamPlayers(data.items || [])
      } catch (error) {
        console.error('Failed to fetch team players:', error)
        setTeamPlayers([])
      } finally {
        setLoadingPlayers(false)
      }
    }
    fetchTeamPlayers()
  }, [selectedTeam])

  const handleEvaluate = async (result: PropSuggestionsResponse) => {
    setEvaluateResult(result)
  }

  return (
    <div className="p-2 sm:p-4 md:p-0">
      <div className="mb-4 sm:mb-6">
        <h2 className="text-xl sm:text-2xl md:text-3xl font-bold text-gray-900 dark:text-slate-100 mb-2 transition-colors duration-200">Explore Players & Teams</h2>
        <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400 transition-colors duration-200">Search for players or browse by team to analyze prop bets</p>
      </div>

      {/* View Mode Toggle */}
      <div className="mb-4 sm:mb-6 flex gap-2">
        <button
          onClick={() => setViewMode('search')}
          className={`px-3 sm:px-4 py-1.5 sm:py-2 rounded-lg text-sm sm:text-base font-medium transition-all ${
            viewMode === 'search'
              ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-900 dark:text-blue-300 border-2 border-blue-600 dark:border-blue-500 shadow-md'
              : 'bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-slate-600 hover:bg-gray-50 dark:hover:bg-slate-600'
          }`}
        >
          Search Players
        </button>
        <button
          onClick={() => setViewMode('teams')}
          className={`px-3 sm:px-4 py-1.5 sm:py-2 rounded-lg text-sm sm:text-base font-medium transition-all ${
            viewMode === 'teams'
              ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-900 dark:text-blue-300 border-2 border-blue-600 dark:border-blue-500 shadow-md'
              : 'bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-300 border border-gray-300 dark:border-slate-600 hover:bg-gray-50 dark:hover:bg-slate-600'
          }`}
        >
          Browse Teams
        </button>
      </div>

      {viewMode === 'search' ? (
        <div className="space-y-6">
          {/* Prominent Player Search Section */}
          <div className="card p-4 sm:p-6 bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border-2 border-blue-200 dark:border-blue-700/50 shadow-lg transition-colors duration-200">
            <div className="mb-4">
              <h3 className="text-lg sm:text-xl font-bold text-gray-900 dark:text-slate-100 mb-2 transition-colors duration-200">Find a Player</h3>
              <p className="text-xs sm:text-sm text-gray-700 dark:text-gray-300 transition-colors duration-200">Search for any NBA player to view their detailed prop analysis</p>
            </div>
            <div className="mb-4">
              <PlayerSearch onSelect={setPlayer} />
            </div>
            {player && player.id > 0 && (
              <div className="mt-4 pt-4 border-t border-blue-200 dark:border-blue-700/50 transition-colors duration-200">
                <Link
                  to={`/player/${player.id}`}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-blue-700 text-white font-medium rounded-lg hover:bg-blue-800 transition-all shadow-sm border-2 border-blue-800"
                  style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '10px 16px', background: '#1d4ed8', color: '#ffffff', borderRadius: '8px', fontWeight: 500, borderColor: '#1e40af' }}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" style={{ width: '16px', height: '16px', color: '#ffffff' }}>
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                  </svg>
                  View {player.name}'s Profile
                </Link>
              </div>
            )}
          </div>

          {/* Filters and Results */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 sm:gap-4">
            <div className="card p-3 sm:p-4">
              <FiltersPanel 
                value={filters} 
                onChange={setFilters}
                player={player}
                onEvaluate={handleEvaluate}
              />
              <p className="mt-3 text-sm text-slate-600 dark:text-slate-400 transition-colors duration-200">Tip: Enter market lines (e.g. PTS 24.5) to compute edge and confidence.</p>
            </div>
            <div className="card p-4">
              <EnhancedSuggest player={player} result={evaluateResult} />
            </div>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Teams List */}
          <div className="lg:col-span-1">
            <div className="card p-4 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg shadow-sm transition-colors duration-200">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-slate-100 mb-4 transition-colors duration-200">NBA Teams</h3>
              {loadingTeams ? (
                <div className="text-center py-8 text-gray-500 dark:text-gray-400 transition-colors duration-200">Loading teams...</div>
              ) : (
                <div className="space-y-2 max-h-[600px] overflow-y-auto">
                  {teams.map((team) => (
                    <button
                      key={team.id}
                      onClick={() => setSelectedTeam(team)}
                      className={`w-full text-left px-3 py-2 rounded-lg transition-all ${
                        selectedTeam?.id === team.id
                          ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-900 dark:text-blue-300 border-2 border-blue-600 dark:border-blue-500 font-medium shadow-md'
                          : 'bg-white dark:bg-slate-700 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-slate-600 hover:bg-gray-50 dark:hover:bg-slate-600 hover:border-blue-300 dark:hover:border-blue-500'
                      }`}
                    >
                      <div className="font-medium">{team.full_name}</div>
                      {team.conference && (
                        <div className={`text-xs transition-colors duration-200 ${selectedTeam?.id === team.id ? 'text-blue-700 dark:text-blue-400' : 'text-gray-500 dark:text-gray-400'}`}>
                          {team.conference} • {team.division}
                        </div>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Team Players */}
          <div className="lg:col-span-2">
            {selectedTeam ? (
              <div className="card p-6">
                <div className="mb-4 flex items-center justify-between">
                  <div>
                    <h3 className="text-xl font-bold text-gray-900 dark:text-slate-100 transition-colors duration-200">{selectedTeam.full_name}</h3>
                    {selectedTeam.conference && (
                      <p className="text-sm text-gray-600 dark:text-gray-400 mt-1 transition-colors duration-200">
                        {selectedTeam.conference} • {selectedTeam.division}
                      </p>
                    )}
                  </div>
                  <Link
                    to={`/team/${selectedTeam.id}`}
                    className="px-4 py-2 bg-blue-700 text-white font-medium rounded-lg hover:bg-blue-800 transition-all border-2 border-blue-800"
                    style={{ backgroundColor: '#1d4ed8', color: '#ffffff', borderColor: '#1e40af' }}
                  >
                    View Team Profile
                  </Link>
                </div>
                {loadingPlayers ? (
                  <div className="text-center py-8 text-gray-500 dark:text-gray-400 transition-colors duration-200">Loading players...</div>
                ) : teamPlayers.length > 0 ? (
                  <div>
                    <div className="mb-3 text-sm text-gray-600 dark:text-gray-400 transition-colors duration-200">
                      {teamPlayers.length} player{teamPlayers.length !== 1 ? 's' : ''} found
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {teamPlayers.map((p) => (
                        <Link
                          key={p.id}
                          to={`/player/${p.id}`}
                          className="p-3 bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:border-blue-400 dark:hover:border-blue-500 hover:shadow-md transition-all"
                        >
                          <div className="flex items-center justify-between">
                            <div>
                              <div className="font-medium text-gray-900 dark:text-slate-100 transition-colors duration-200">{p.name}</div>
                              {p.position && (
                                <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 transition-colors duration-200">{p.position}</div>
                              )}
                            </div>
                            {p.jersey_number && (
                              <div className="text-lg font-bold text-gray-400 dark:text-gray-500 transition-colors duration-200">#{p.jersey_number}</div>
                            )}
                          </div>
                        </Link>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <p className="text-gray-500 dark:text-gray-400 mb-2 transition-colors duration-200">No players found for this team</p>
                    <p className="text-xs text-gray-400 dark:text-gray-500 transition-colors duration-200">Try selecting a different team or check the browser console for details</p>
                  </div>
                )}
              </div>
            ) : (
              <div className="card p-8 text-center">
                <svg className="mx-auto h-16 w-16 text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                </svg>
                <p className="text-gray-600">Select a team from the list to view players</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
