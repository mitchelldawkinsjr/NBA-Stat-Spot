import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'

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

export default function TeamProfile() {
  const { id } = useParams()
  const [team, setTeam] = useState<Team | null>(null)
  const [roster, setRoster] = useState<Player[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchTeam = async () => {
      if (!id) return
      setLoading(true)
      setError(null)
      try {
        const res = await fetch(`/api/v1/teams/${id}`)
        if (!res.ok) {
          if (res.status === 404) {
            setError('Team not found')
          } else {
            setError('Failed to load team')
          }
          return
        }
        const data = await res.json()
        setTeam(data.team)
        setRoster(data.roster || [])
      } catch (e: any) {
        setError(e?.message || 'Error loading team')
      } finally {
        setLoading(false)
      }
    }
    fetchTeam()
  }, [id])

  if (loading) {
    return (
      <div className="container mx-auto px-3 md:px-4 max-w-7xl">
        <div className="text-center py-12">
          <div className="text-gray-500 dark:text-gray-400 transition-colors duration-200">Loading team...</div>
        </div>
      </div>
    )
  }

  if (error || !team) {
    return (
      <div className="container mx-auto px-3 md:px-4 max-w-7xl">
        <div className="text-center py-12">
          <div className="text-red-600 dark:text-red-400 mb-4 transition-colors duration-200">{error || 'Team not found'}</div>
          <Link to="/explore" className="text-blue-600 dark:text-blue-400 hover:underline transition-colors duration-200">
            Return to Explore
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-3 md:px-4 max-w-7xl">
      {/* Breadcrumbs */}
      <nav className="relative z-10 mt-3" aria-label="Breadcrumb">
        <ol className="min-w-0 flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 overflow-hidden transition-colors duration-200">
          <li>
            <Link to="/" className="hover:text-gray-700 dark:hover:text-gray-300 transition-colors duration-200">Home</Link>
          </li>
          <li aria-hidden="true" className="px-1">/</li>
          <li>
            <Link to="/explore" className="hover:text-gray-700 dark:hover:text-gray-300 transition-colors duration-200">Explore</Link>
          </li>
          <li aria-hidden="true" className="px-1">/</li>
          <li className="flex-1 min-w-0 text-gray-700 dark:text-gray-300 font-medium truncate transition-colors duration-200">{team.full_name}</li>
        </ol>
      </nav>

      {/* Team Header */}
      <div className="relative overflow-hidden rounded-2xl bg-white dark:bg-slate-800 shadow-xl ring-1 ring-gray-200 dark:ring-slate-700 mt-3 mb-6 transition-colors duration-200">
        <div className="px-6 py-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-slate-100 mb-2 transition-colors duration-200">{team.full_name}</h1>
              {team.conference && (
                <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400 transition-colors duration-200">
                  <span>{team.conference}</span>
                  {team.division && (
                    <>
                      <span>•</span>
                      <span>{team.division}</span>
                    </>
                  )}
                </div>
              )}
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-gray-400 dark:text-gray-500 transition-colors duration-200">{team.abbreviation}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Roster Section */}
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm ring-1 ring-gray-200 dark:ring-slate-700 p-6 transition-colors duration-200">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-slate-100 transition-colors duration-200">Roster</h2>
          <div className="text-sm text-gray-600 dark:text-gray-400 transition-colors duration-200">{roster.length} players</div>
        </div>
        {roster.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {roster.map((player) => (
              <Link
                key={player.id}
                to={`/player/${player.id}`}
                className="p-4 bg-gray-50 dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:border-blue-400 dark:hover:border-blue-500 hover:shadow-md transition-all group"
              >
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="font-semibold text-gray-900 dark:text-slate-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                      {player.name}
                    </div>
                    {player.position && (
                      <div className="text-xs text-gray-500 dark:text-gray-400 mt-1 transition-colors duration-200">{player.position}</div>
                    )}
                  </div>
                  {player.jersey_number && (
                    <div className="text-2xl font-bold text-gray-300 dark:text-gray-600 ml-3 transition-colors duration-200">#{player.jersey_number}</div>
                  )}
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500 dark:text-gray-400 transition-colors duration-200">No players found</div>
        )}
      </div>
    </div>
  )
}

