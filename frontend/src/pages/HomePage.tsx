import { Link } from 'react-router-dom'

export default function HomePage() {
  return (
    <div className="p-4 sm:p-6 md:p-8">
      <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-slate-100 mb-3 transition-colors duration-200">NBA Prop Bet Analyzer</h2>
      <p className="text-base sm:text-lg text-gray-700 dark:text-gray-300 mb-4 transition-colors duration-200">Explore player props, trends, and today's suggestions.</p>
      <div className="flex flex-wrap gap-3 sm:gap-4">
        <Link to="/explore" className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors duration-200">Explore</Link>
        <Link to="/dashboard" className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors duration-200">Daily Props</Link>
        <Link to="/trends" className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors duration-200">Player Trends</Link>
      </div>
    </div>
  )
}
