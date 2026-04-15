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
    <div className="bg-background min-h-screen p-4 md:p-6">
      <div className="mb-6">
        <h1 className="text-4xl font-black uppercase italic tracking-tighter text-on-surface">
          PROP <span className="text-primary-container">EXPLORER</span>
        </h1>
        <p className="text-on-surface-variant text-sm mt-1 border-l-2 border-primary-container pl-3">Search for players or browse by team to analyze prop bets</p>
      </div>

      {/* View Mode Toggle */}
      <div className="mb-6 flex gap-2">
        <button
          onClick={() => setViewMode('search')}
          className={`px-4 py-2 text-[10px] font-black uppercase tracking-widest rounded transition-all ${
            viewMode === 'search'
              ? 'bg-primary-container text-on-primary'
              : 'bg-surface-container text-on-surface-variant border border-outline-variant/30 hover:bg-surface-container-high'
          }`}
        >
          Search Players
        </button>
        <button
          onClick={() => setViewMode('teams')}
          className={`px-4 py-2 text-[10px] font-black uppercase tracking-widest rounded transition-all ${
            viewMode === 'teams'
              ? 'bg-primary-container text-on-primary'
              : 'bg-surface-container text-on-surface-variant border border-outline-variant/30 hover:bg-surface-container-high'
          }`}
        >
          Browse Teams
        </button>
      </div>

      {viewMode === 'search' ? (
        <div className="space-y-6">
          {/* Prominent Player Search Section */}
          <div className="card p-4 sm:p-6 bg-surface-container border border-outline/20 shadow-sm transition-colors duration-200">
            <div className="mb-4">
              <h3 className="text-lg sm:text-xl font-bold text-on-surface mb-2 transition-colors duration-200">Find a Player</h3>
              <p className="text-xs sm:text-sm text-on-surface-variant transition-colors duration-200">Search for any NBA player to view their detailed prop analysis</p>
            </div>
            <div className="mb-4">
              <PlayerSearch onSelect={setPlayer} />
            </div>
            {player && player.id > 0 && (
              <div className="mt-4 pt-4 border-t border-outline/20 transition-colors duration-200">
                <Link
                  to={`/player/${player.id}`}
                  className="inline-flex items-center gap-2 px-4 py-2 bg-primary-container text-on-primary font-medium rounded-lg hover:opacity-90 transition-all shadow-sm border border-primary-container/40"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
              <p className="mt-3 text-sm text-on-surface-variant transition-colors duration-200">Tip: Enter market lines (e.g. PTS 24.5) to compute edge and confidence.</p>
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
            <div className="card p-4 bg-surface-container border border-outline/20 rounded-lg shadow-sm transition-colors duration-200">
              <h3 className="text-lg font-semibold text-on-surface mb-4 transition-colors duration-200">NBA Teams</h3>
              {loadingTeams ? (
                <div className="text-center py-8 text-on-surface-variant transition-colors duration-200">Loading teams...</div>
              ) : (
                <div className="space-y-2 max-h-[600px] overflow-y-auto">
                  {teams.map((team) => (
                    <button
                      key={team.id}
                      onClick={() => setSelectedTeam(team)}
                      className={`w-full text-left px-3 py-2 rounded-lg transition-all ${
                        selectedTeam?.id === team.id
                          ? 'bg-primary-container/15 text-primary-container border-2 border-primary-container/50 font-medium shadow-sm'
                          : 'bg-surface-container-high text-on-surface border border-outline/20 hover:bg-surface-container-highest hover:border-primary-container/30'
                      }`}
                    >
                      <div className="font-medium">{team.full_name}</div>
                      {team.conference && (
                        <div className={`text-xs transition-colors duration-200 ${selectedTeam?.id === team.id ? 'text-blue-700 dark:text-blue-400' : 'text-on-surface-variant'}`}>
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
                    <h3 className="text-xl font-bold text-on-surface transition-colors duration-200">{selectedTeam.full_name}</h3>
                    {selectedTeam.conference && (
                      <p className="text-sm text-on-surface-variant mt-1 transition-colors duration-200">
                        {selectedTeam.conference} • {selectedTeam.division}
                      </p>
                    )}
                  </div>
                  <Link
                    to={`/team/${selectedTeam.id}`}
                    className="px-4 py-2 bg-primary-container text-on-primary font-medium rounded-lg hover:opacity-90 transition-all border border-primary-container/40"
                  >
                    View Team Profile
                  </Link>
                </div>
                {loadingPlayers ? (
                  <div className="text-center py-8 text-on-surface-variant transition-colors duration-200">Loading players...</div>
                ) : teamPlayers.length > 0 ? (
                  <div>
                    <div className="mb-3 text-sm text-on-surface-variant transition-colors duration-200">
                      {teamPlayers.length} player{teamPlayers.length !== 1 ? 's' : ''} found
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {teamPlayers.map((p) => (
                        <Link
                          key={p.id}
                          to={`/player/${p.id}`}
                          className="p-3 bg-surface-container-high border border-outline/20 rounded-lg hover:border-primary-container/35 hover:shadow-sm transition-all"
                        >
                          <div className="flex items-center justify-between">
                            <div>
                              <div className="font-medium text-on-surface transition-colors duration-200">{p.name}</div>
                              {p.position && (
                                <div className="text-xs text-on-surface-variant mt-0.5 transition-colors duration-200">{p.position}</div>
                              )}
                            </div>
                            {p.jersey_number && (
                              <div className="text-lg font-bold text-on-surface-variant/70 transition-colors duration-200">#{p.jersey_number}</div>
                            )}
                          </div>
                        </Link>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="text-center py-8">
                    <p className="text-on-surface-variant mb-2 transition-colors duration-200">No players found for this team</p>
                    <p className="text-xs text-on-surface-variant/70 transition-colors duration-200">Try selecting a different team or check the browser console for details</p>
                  </div>
                )}
              </div>
            ) : (
              <div className="card p-8 text-center">
                <svg className="mx-auto h-16 w-16 text-on-surface-variant mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                </svg>
                <p className="text-on-surface-variant">Select a team from the list to view players</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
