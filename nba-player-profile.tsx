import React from 'react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

// Type Definitions
interface GameData {
  game: string;
  points?: number;
  assists?: number;
  line: number;
}

interface ShotDistribution {
  name: string;
  value: number;
  color: string;
}

interface QuarterData {
  quarter: string;
  points: number;
}

interface PropCardProps {
  label: string;
  value: string;
  trend: 'up' | 'down' | 'neutral';
  trendText: string;
  confidence: number;
  recommendation: string;
}

interface StatRowProps {
  label: string;
  games: number;
  pts: number;
  ast: number;
  reb: number;
  threes: number;
  pra: number;
  highlight?: 'blue' | 'green' | 'purple';
}

interface StatEntry {
  label: string;
  value: string;
  valueColor?: string;
}

interface MatchupCardProps {
  title: string;
  stats: StatEntry[];
  tags?: string[];
}

interface PropHistoryRowProps {
  prop: string;
  hitRate: string;
  last5: boolean[];
  margin: string;
  trend: string;
  trendColor: 'green' | 'yellow' | 'red';
}

interface OddsEntry {
  book: string;
  over: string;
  under: string;
}

interface OddsCardProps {
  title: string;
  color: 'blue' | 'green';
  odds: OddsEntry[];
  bestOver: string;
  bestUnder: string;
}

export default function NBAPlayerProfile(): JSX.Element {
  const pointsData: GameData[] = [
    { game: 'G1', points: 24, line: 25.5 },
    { game: 'G2', points: 28, line: 25.5 },
    { game: 'G3', points: 31, line: 25.5 },
    { game: 'G4', points: 22, line: 25.5 },
    { game: 'G5', points: 29, line: 25.5 },
    { game: 'G6', points: 26, line: 25.5 },
    { game: 'G7', points: 33, line: 25.5 },
    { game: 'G8', points: 25, line: 25.5 },
    { game: 'G9', points: 27, line: 25.5 },
    { game: 'G10', points: 30, line: 25.5 },
    { game: 'G11', points: 26, line: 25.5 },
    { game: 'G12', points: 28, line: 25.5 },
    { game: 'G13', points: 29, line: 25.5 },
    { game: 'G14', points: 31, line: 25.5 },
    { game: 'G15', points: 27, line: 25.5 },
  ];

  const assistsData: GameData[] = [
    { game: 'G1', assists: 7, line: 7.5 },
    { game: 'G2', assists: 9, line: 7.5 },
    { game: 'G3', assists: 8, line: 7.5 },
    { game: 'G4', assists: 6, line: 7.5 },
    { game: 'G5', assists: 10, line: 7.5 },
    { game: 'G6', assists: 8, line: 7.5 },
    { game: 'G7', assists: 9, line: 7.5 },
    { game: 'G8', assists: 7, line: 7.5 },
    { game: 'G9', assists: 8, line: 7.5 },
    { game: 'G10', assists: 9, line: 7.5 },
    { game: 'G11', assists: 7, line: 7.5 },
    { game: 'G12', assists: 10, line: 7.5 },
    { game: 'G13', assists: 8, line: 7.5 },
    { game: 'G14', assists: 9, line: 7.5 },
    { game: 'G15', assists: 8, line: 7.5 },
  ];

  const shotDistribution: ShotDistribution[] = [
    { name: 'Paint', value: 42, color: '#3b82f6' },
    { name: 'Mid-Range', value: 23, color: '#8b5cf6' },
    { name: '3-Pointers', value: 15, color: '#f59e0b' },
    { name: 'Free Throws', value: 20, color: '#10b981' },
  ];

  const quarterData: QuarterData[] = [
    { quarter: 'Q1', points: 7.2 },
    { quarter: 'Q2', points: 6.8 },
    { quarter: 'Q3', points: 7.1 },
    { quarter: 'Q4', points: 5.7 },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-600 via-purple-600 to-purple-800 p-4 md:p-8">
      <div className="max-w-7xl mx-auto bg-white rounded-3xl shadow-[0_20px_60px_rgba(0,0,0,0.3)] overflow-hidden">
        
        {/* Header with Gradient */}
        <div className="bg-gradient-to-r from-blue-900 via-blue-800 to-blue-600 text-white p-8 md:p-10">
          <div className="flex flex-col md:flex-row items-center gap-8">
            <div className="w-32 h-32 rounded-full border-4 border-white bg-gradient-to-br from-gray-100 to-gray-300 flex items-center justify-center text-6xl font-bold text-gray-700 shadow-xl">
              LJ
            </div>
            <div className="flex-1 text-center md:text-left">
              <h1 className="text-5xl font-extrabold mb-3 tracking-tight">LeBron James</h1>
              <div className="flex flex-wrap gap-4 text-sm justify-center md:justify-start">
                <span className="bg-white/20 backdrop-blur-sm px-5 py-2 rounded-full font-medium shadow-lg">LA Lakers • #23 • SF/PF</span>
                <span className="bg-white/20 backdrop-blur-sm px-5 py-2 rounded-full font-medium shadow-lg">vs Boston Celtics • Tonight 7:30 PM</span>
                <span className="bg-white/20 backdrop-blur-sm px-5 py-2 rounded-full font-medium shadow-lg">🏠 Home</span>
              </div>
            </div>
          </div>
        </div>

        <div className="p-6 md:p-10">
          
          {/* Prop Highlights - Enhanced Design */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-10">
            <PropCard
              label="Points Prop Line"
              value="25.5"
              trend="up"
              trendText="L10 Avg: 27.3 (+1.8)"
              confidence={78}
              recommendation="OVER"
            />
            <PropCard
              label="Assists Prop Line"
              value="7.5"
              trend="up"
              trendText="L10 Avg: 8.2 (+0.7)"
              confidence={65}
              recommendation="OVER"
            />
            <PropCard
              label="Rebounds Prop Line"
              value="8.5"
              trend="neutral"
              trendText="L10 Avg: 8.4 (-0.1)"
              confidence={52}
              recommendation="UNDER"
            />
            <PropCard
              label="3-Pointers Made"
              value="1.5"
              trend="down"
              trendText="L10 Avg: 1.1 (-0.4)"
              confidence={71}
              recommendation="UNDER"
            />
            <PropCard
              label="Pts + Reb + Ast"
              value="42.5"
              trend="up"
              trendText="L10 Avg: 43.9 (+1.4)"
              confidence={82}
              recommendation="OVER"
            />
            <PropCard
              label="Double-Double"
              value="Yes"
              trend="up"
              trendText="7 of last 10 games"
              confidence={70}
              recommendation="YES"
            />
          </div>

          {/* Performance Trends */}
          <div className="mb-10">
            <h2 className="text-3xl font-bold text-blue-900 mb-6 flex items-center gap-3">
              <span className="text-4xl">📊</span> 
              <span>Performance Trends</span>
            </h2>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-gradient-to-br from-gray-50 to-white rounded-2xl p-6 border border-gray-200 shadow-lg">
                <h3 className="text-sm font-bold mb-4 text-gray-700 uppercase tracking-wide">Last 15 Games - Points Scored</h3>
                <ResponsiveContainer width="100%" height={280}>
                  <LineChart data={pointsData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="game" tick={{ fontSize: 12 }} />
                    <YAxis domain={[20, 35]} tick={{ fontSize: 12 }} />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'white', 
                        border: '1px solid #e5e7eb',
                        borderRadius: '8px',
                        boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
                      }} 
                    />
                    <Legend />
                    <Line 
                      type="monotone" 
                      dataKey="points" 
                      stroke="#3b82f6" 
                      strokeWidth={3} 
                      name="Points"
                      dot={{ fill: '#3b82f6', r: 5 }}
                      activeDot={{ r: 7 }}
                    />
                    <Line 
                      type="monotone" 
                      dataKey="line" 
                      stroke="#ef4444" 
                      strokeDasharray="8 4" 
                      strokeWidth={2} 
                      name="Prop Line"
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <div className="bg-gradient-to-br from-gray-50 to-white rounded-2xl p-6 border border-gray-200 shadow-lg">
                <h3 className="text-sm font-bold mb-4 text-gray-700 uppercase tracking-wide">Last 15 Games - Assists</h3>
                <ResponsiveContainer width="100%" height={280}>
                  <LineChart data={assistsData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="game" tick={{ fontSize: 12 }} />
                    <YAxis domain={[5, 12]} tick={{ fontSize: 12 }} />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'white', 
                        border: '1px solid #e5e7eb',
                        borderRadius: '8px',
                        boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
                      }} 
                    />
                    <Legend />
                    <Line 
                      type="monotone" 
                      dataKey="assists" 
                      stroke="#10b981" 
                      strokeWidth={3} 
                      name="Assists"
                      dot={{ fill: '#10b981', r: 5 }}
                      activeDot={{ r: 7 }}
                    />
                    <Line 
                      type="monotone" 
                      dataKey="line" 
                      stroke="#ef4444" 
                      strokeDasharray="8 4" 
                      strokeWidth={2} 
                      name="Prop Line"
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Statistical Splits */}
          <div className="mb-10">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between mb-6 gap-4">
              <h2 className="text-3xl font-bold text-blue-900 flex items-center gap-3">
                <span className="text-4xl">📈</span> 
                <span>Key Statistical Splits</span>
              </h2>
              <div className="flex gap-5 text-xs">
                <span className="flex items-center gap-2 font-medium">
                  <span className="w-3 h-3 rounded-full bg-green-500 shadow-sm"></span>
                  Above Line
                </span>
                <span className="flex items-center gap-2 font-medium">
                  <span className="w-3 h-3 rounded-full bg-yellow-500 shadow-sm"></span>
                  Near Line
                </span>
                <span className="flex items-center gap-2 font-medium">
                  <span className="w-3 h-3 rounded-full bg-red-500 shadow-sm"></span>
                  Below Line
                </span>
              </div>
            </div>
            <div className="overflow-x-auto rounded-2xl border border-gray-200 shadow-lg">
              <table className="w-full">
                <thead className="bg-gradient-to-r from-gray-100 to-gray-50">
                  <tr>
                    <th className="text-left p-4 text-xs font-bold text-gray-700 uppercase tracking-wider">Split Category</th>
                    <th className="text-left p-4 text-xs font-bold text-gray-700 uppercase tracking-wider">Games</th>
                    <th className="text-left p-4 text-xs font-bold text-gray-700 uppercase tracking-wider">PTS</th>
                    <th className="text-left p-4 text-xs font-bold text-gray-700 uppercase tracking-wider">AST</th>
                    <th className="text-left p-4 text-xs font-bold text-gray-700 uppercase tracking-wider">REB</th>
                    <th className="text-left p-4 text-xs font-bold text-gray-700 uppercase tracking-wider">3PM</th>
                    <th className="text-left p-4 text-xs font-bold text-gray-700 uppercase tracking-wider">PRA</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-100">
                  <StatRow label="Season Average" games={45} pts={26.8} ast={7.9} reb={8.3} threes={1.2} pra={43.0} />
                  <StatRow label="Last 10 Games" games={10} pts={27.3} ast={8.2} reb={8.4} threes={1.1} pra={43.9} />
                  <StatRow label="Last 5 Games" games={5} pts={28.6} ast={8.8} reb={9.2} threes={1.4} pra={46.6} highlight="blue" />
                  <StatRow label="Home Games" games={23} pts={28.1} ast={8.4} reb={8.7} threes={1.3} pra={45.2} highlight="green" />
                  <StatRow label="Away Games" games={22} pts={25.4} ast={7.4} reb={7.8} threes={1.1} pra={40.6} />
                  <StatRow label="vs Boston (L3)" games={3} pts={29.3} ast={9.0} reb={8.7} threes={0.7} pra={47.0} highlight="purple" />
                  <StatRow label="Rest = 1 Day" games={28} pts={27.5} ast={8.1} reb={8.6} threes={1.3} pra={44.2} />
                  <StatRow label="Back-to-Back" games={8} pts={24.1} ast={7.3} reb={7.1} threes={0.9} pra={38.5} />
                </tbody>
              </table>
            </div>
          </div>

          {/* Matchup Impact */}
          <div className="mb-10">
            <h2 className="text-3xl font-bold text-blue-900 mb-6 flex items-center gap-3">
              <span className="text-4xl">⚔️</span> 
              <span>Matchup Impact Analysis</span>
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <MatchupCard
                title="Opponent Defense Rank"
                stats={[
                  { label: 'Points Allowed to SF:', value: '18th (Favorable)' },
                  { label: 'Assists Allowed:', value: '22nd (Favorable)' },
                  { label: 'Rebounds Allowed:', value: '8th (Tough)' },
                ]}
              />
              <MatchupCard
                title="Pace & Style"
                stats={[
                  { label: 'Game Pace:', value: '102.3 (Fast)' },
                  { label: 'Expected Possessions:', value: '98 (+4 avg)' },
                  { label: '3PT Rate vs BOS:', value: '34% (Low)' },
                ]}
              />
              <MatchupCard
                title="Recent Form"
                stats={[
                  { label: 'Last 5 Games:', value: '4-1' },
                ]}
                tags={['4G PTS OVER', '3G AST OVER']}
              />
              <MatchupCard
                title="Game Context"
                stats={[
                  { label: 'Rest Days:', value: '1 Day (Normal)' },
                  { label: 'Injury Report:', value: 'Healthy', valueColor: 'text-green-600' },
                  { label: 'Minutes Trend:', value: '35.2 (Up 2.1)' },
                ]}
              />
            </div>
          </div>

          {/* Shot Distribution */}
          <div className="mb-10">
            <h2 className="text-3xl font-bold text-blue-900 mb-6 flex items-center gap-3">
              <span className="text-4xl">🎯</span> 
              <span>Shot Distribution & Usage</span>
            </h2>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-gradient-to-br from-gray-50 to-white rounded-2xl p-6 border border-gray-200 shadow-lg">
                <h3 className="text-sm font-bold mb-4 text-gray-700 uppercase tracking-wide">Shot Type Distribution (Last 10 Games)</h3>
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie
                      data={shotDistribution}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percent }: { name: string; percent: number }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      outerRadius={90}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {shotDistribution.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="bg-gradient-to-br from-gray-50 to-white rounded-2xl p-6 border border-gray-200 shadow-lg">
                <h3 className="text-sm font-bold mb-4 text-gray-700 uppercase tracking-wide">Points by Quarter (Season Average)</h3>
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={quarterData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis dataKey="quarter" tick={{ fontSize: 12 }} />
                    <YAxis domain={[0, 10]} tick={{ fontSize: 12 }} />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: 'white', 
                        border: '1px solid #e5e7eb',
                        borderRadius: '8px',
                        boxShadow: '0 4px 6px rgba(0,0,0,0.1)'
                      }} 
                    />
                    <Bar dataKey="points" fill="#3b82f6" radius={[8, 8, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {/* Historical Prop Performance */}
          <div className="mb-10">
            <h2 className="text-3xl font-bold text-blue-900 mb-6 flex items-center gap-3">
              <span className="text-4xl">📜</span> 
              <span>Historical Prop Performance</span>
              <span className="ml-auto text-sm font-normal text-gray-500">Last 20 Games</span>
            </h2>
            <div className="bg-white border border-gray-200 rounded-2xl overflow-hidden shadow-lg">
              <div className="grid grid-cols-5 bg-gradient-to-r from-gray-100 to-gray-50 text-xs font-bold text-gray-700 uppercase">
                <div className="p-5 border-r border-gray-200">Prop Type</div>
                <div className="p-5 border-r border-gray-200">Hit Rate</div>
                <div className="p-5 border-r border-gray-200">Last 5</div>
                <div className="p-5 border-r border-gray-200">Avg Margin</div>
                <div className="p-5">Trend</div>
              </div>
              <div className="divide-y divide-gray-100">
                <PropHistoryRow
                  prop="Over 25.5 PTS"
                  hitRate="14/20 (70%)"
                  last5={[true, true, true, true, false]}
                  margin="+1.8 pts"
                  trend="Hot"
                  trendColor="green"
                />
                <PropHistoryRow
                  prop="Over 7.5 AST"
                  hitRate="13/20 (65%)"
                  last5={[true, true, true, false, true]}
                  margin="+0.7 ast"
                  trend="Hot"
                  trendColor="green"
                />
                <PropHistoryRow
                  prop="Over 8.5 REB"
                  hitRate="10/20 (50%)"
                  last5={[true, false, false, true, false]}
                  margin="-0.1 reb"
                  trend="Neutral"
                  trendColor="yellow"
                />
                <PropHistoryRow
                  prop="Over 1.5 3PM"
                  hitRate="7/20 (35%)"
                  last5={[false, false, false, false, true]}
                  margin="-0.4 3pm"
                  trend="Cold"
                  trendColor="red"
                />
                <PropHistoryRow
                  prop="Over 42.5 PRA"
                  hitRate="16/20 (80%)"
                  last5={[true, true, true, true, true]}
                  margin="+1.4 total"
                  trend="Fire"
                  trendColor="green"
                />
                <PropHistoryRow
                  prop="Double-Double"
                  hitRate="14/20 (70%)"
                  last5={[true, true, true, false, true]}
                  margin="-"
                  trend="Hot"
                  trendColor="green"
                />
              </div>
            </div>
          </div>

          {/* Live Odds Comparison */}
          <div className="mb-10">
            <h2 className="text-3xl font-bold text-blue-900 mb-6 flex items-center gap-3">
              <span className="text-4xl">💰</span> 
              <span>Live Odds Comparison</span>
              <span className="ml-auto text-sm font-normal text-gray-500">Updated 2 minutes ago</span>
            </h2>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <OddsCard
                title="Points - Over/Under 25.5"
                color="blue"
                odds={[
                  { book: 'DraftKings', over: '-115', under: '-105' },
                  { book: 'FanDuel', over: '-120', under: '+100' },
                  { book: 'BetMGM', over: '-110', under: '-110' },
                ]}
                bestOver="-110"
                bestUnder="+100"
              />
              <OddsCard
                title="Assists - Over/Under 7.5"
                color="green"
                odds={[
                  { book: 'DraftKings', over: '-105', under: '-115' },
                  { book: 'FanDuel', over: '-108', under: '-112' },
                  { book: 'BetMGM', over: '+100', under: '-120' },
                ]}
                bestOver="+100"
                bestUnder="-112"
              />
            </div>
          </div>

          {/* Advanced Metrics */}
          <div className="mb-10">
            <h2 className="text-3xl font-bold text-blue-900 mb-6 flex items-center gap-3">
              <span className="text-4xl">🔬</span> 
              <span>Advanced Metrics & Correlations</span>
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-2xl p-6 border-2 border-purple-200 shadow-lg">
                <h3 className="font-bold text-purple-900 mb-4 text-lg">Usage Rate Analysis</h3>
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between items-center">
                    <span className="text-purple-700 font-medium">Season Usage %:</span>
                    <span className="font-bold text-purple-900 text-base">28.4%</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-purple-700 font-medium">Last 10 Games:</span>
                    <span className="font-bold text-purple-900 text-base">30.2% <span className="text-green-600 text-lg">↑</span></span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-purple-700 font-medium">True Shooting %:</span>
                    <span className="font-bold text-purple-900 text-base">61.3%</span>
                  </div>
                  <div className="mt-4 p-4 bg-white rounded-xl shadow-sm">
                    <p className="text-xs text-purple-800 leading-relaxed">High usage trending up suggests more scoring opportunities and ball control</p>
                  </div>
                </div>
              </div>
              <div className="bg-gradient-to-br from-orange-50 to-orange-100 rounded-2xl p-6 border-2 border-orange-200 shadow-lg">
                <h3 className="font-bold text-orange-900 mb-4 text-lg">Prop Correlations</h3>
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between items-center">
                    <span className="text-orange-700 font-medium">PTS ↔ AST:</span>
                    <span className="font-bold text-orange-900 text-base">-0.32 (Inverse)</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-orange-700 font-medium">PTS ↔ REB:</span>
                    <span className="font-bold text-orange-900 text-base">+0.18 (Weak)</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-orange-700 font-medium">AST ↔ REB:</span>
                    <span className="font-bold text-orange-900 text-base">+0.45 (Moderate)</span>
                  </div>
                  <div className="mt-4 p-4 bg-white rounded-xl shadow-sm">
                    <p className="text-xs text-orange-800 leading-relaxed">When LeBron scores more, he assists less. Consider parlay implications carefully.</p>
                  </div>
                </div>
              </div>
              <div className="bg-gradient-to-br from-teal-50 to-teal-100 rounded-2xl p-6 border-2 border-teal-200 shadow-lg">
                <h3 className="font-bold text-teal-900 mb-4 text-lg">Defensive Matchup</h3>
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between items-center">
                    <span className="text-teal-700 font-medium">Primary Defender:</span>
                    <span className="font-bold text-teal-900 text-base">J. Tatum</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-teal-700 font-medium">Defender Rating:</span>
                    <span className="font-bold text-teal-900 text-base">108.4 (Good)</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-teal-700 font-medium">Historical vs Tatum:</span>
                    <span className="font-bold text-teal-900 text-base">24.7 PPG</span>
                  </div>
                  <div className="mt-4 p-4 bg-white rounded-xl shadow-sm">
                    <p className="text-xs text-teal-800 leading-relaxed">Solid defender, but LeBron historically performs at or near his average</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Parlay Builder */}
          <div className="mb-10">
            <h2 className="text-3xl font-bold text-blue-900 mb-6 flex items-center gap-3">
              <span className="text-4xl">🎲</span> 
              <span>Parlay Builder</span>
            </h2>
            <div className="bg-gradient-to-br from-indigo-50 via-indigo-100 to-purple-100 rounded-2xl p-8 border-2 border-indigo-300 shadow-xl">
              <div className="flex flex-col lg:flex-row items-start gap-8">
                <div className="flex-1 w-full">
                  <h3 className="font-bold text-indigo-900 mb-6 text-xl">Suggested Parlay (3-Leg)</h3>
                  <div className="space-y-4">
                    <div className="bg-white rounded-xl p-5 flex justify-between items-center shadow-md hover:shadow-lg transition-shadow">
                      <div>
                        <div className="font-bold text-gray-900 text-lg">LeBron OVER 25.5 Points</div>
                        <div className="text-xs text-gray-600 mt-2">78% confidence • -115 odds</div>
                      </div>
                      <button className="text-red-500 hover:text-red-700 text-2xl font-bold transition-colors">✕</button>
                    </div>
                    <div className="bg-white rounded-xl p-5 flex justify-between items-center shadow-md hover:shadow-lg transition-shadow">
                      <div>
                        <div className="font-bold text-gray-900 text-lg">LeBron OVER 7.5 Assists</div>
                        <div className="text-xs text-gray-600 mt-2">65% confidence • +100 odds</div>
                      </div>
                      <button className="text-red-500 hover:text-red-700 text-2xl font-bold transition-colors">✕</button>
                    </div>
                    <div className="bg-white rounded-xl p-5 flex justify-between items-center shadow-md hover:shadow-lg transition-shadow">
                      <div>
                        <div className="font-bold text-gray-900 text-lg">LeBron UNDER 1.5 3-Pointers</div>
                        <div className="text-xs text-gray-600 mt-2">71% confidence • -110 odds</div>
                      </div>
                      <button className="text-red-500 hover:text-red-700 text-2xl font-bold transition-colors">✕</button>
                    </div>
                  </div>
                </div>
                <div className="w-full lg:w-72 bg-white rounded-2xl p-8 shadow-2xl border-2 border-indigo-200">
                  <div className="text-center mb-6">
                    <div className="text-sm text-gray-600 mb-2 font-medium">Combined Odds</div>
                    <div className="text-5xl font-extrabold text-indigo-900">+387</div>
                  </div>
                  <div className="space-y-3 text-sm mb-6 border-t border-b border-gray-200 py-4">
                    <div className="flex justify-between items-center">
                      <span className="text-gray-600 font-medium">Risk:</span>
                      <span className="font-bold text-lg">$100</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-600 font-medium">To Win:</span>
                      <span className="font-bold text-green-600 text-lg">$387</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-gray-600 font-medium">Total Payout:</span>
                      <span className="font-extrabold text-indigo-900 text-xl">$487</span>
                    </div>
                  </div>
                  <button className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white font-bold py-4 rounded-xl transition-all shadow-lg hover:shadow-xl transform hover:-translate-y-0.5">
                    Place Bet
                  </button>
                  <div className="mt-4 text-xs text-center text-gray-500 font-medium">
                    Combined probability: ~37%
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Betting Recommendation */}
          <div className="bg-gradient-to-br from-yellow-50 via-yellow-100 to-amber-100 border-l-4 border-yellow-500 rounded-2xl p-8 shadow-xl">
            <h2 className="text-2xl font-bold text-yellow-900 mb-4 flex items-center gap-2">
              <span className="text-3xl">🤖</span> Prop Betting Analysis Summary
            </h2>
            <div className="text-yellow-900 space-y-5">
              <div>
                <h3 className="font-bold mb-3 text-lg">High Confidence Plays:</h3>
                <ul className="space-y-3 text-sm ml-2">
                  <li className="flex gap-2">
                    <span className="text-yellow-600 font-bold">•</span>
                    <span><span className="font-bold">LeBron OVER 25.5 Points (82% confidence)</span> - Trending up in last 10, excellent matchup vs Boston's 18th ranked SF defense, home game advantage (+2.7 PTS at home)</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-yellow-600 font-bold">•</span>
                    <span><span className="font-bold">LeBron OVER 42.5 PRA (85% confidence)</span> - Strong across all categories, historically performs well vs Boston (47.0 avg), increased minutes trend</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-yellow-600 font-bold">•</span>
                    <span><span className="font-bold">LeBron UNDER 1.5 3PM (71% confidence)</span> - Below average L10 (1.1), historically low vs Boston (0.7), team plays inside more vs BOS</span>
                  </li>
                </ul>
              </div>
              <div>
                <h3 className="font-bold mb-3 text-lg">Risk Factors:</h3>
                <ul className="space-y-3 text-sm ml-2">
                  <li className="flex gap-2">
                    <span className="text-yellow-600 font-bold">•</span>
                    <span>Only 1 day rest (not back-to-back, but watch load management)</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-yellow-600 font-bold">•</span>
                    <span>Boston's strong rebounding defense (8th) could limit REB opportunities</span>
                  </li>
                  <li className="flex gap-2">
                    <span className="text-yellow-600 font-bold">•</span>
                    <span>Game pace is critical - if Boston slows it down, volume stats could suffer</span>
                  </li>
                </ul>
              </div>
              <div className="flex flex-wrap gap-2 mt-6">
                <span className="bg-green-100 text-green-800 text-xs font-bold px-4 py-2 rounded-full shadow-sm">CONSISTENT SCORER</span>
                <span className="bg-red-100 text-red-800 text-xs font-bold px-4 py-2 rounded-full shadow-sm">HOT STREAK</span>
                <span className="bg-red-100 text-red-800 text-xs font-bold px-4 py-2 rounded-full shadow-sm">FAVORABLE MATCHUP</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Component Definitions with TypeScript
function PropCard({ label, value, trend, trendText, confidence, recommendation }: PropCardProps): JSX.Element {
  const trendColor = trend === 'up' ? 'text-green-600' : trend === 'down' ? 'text-red-600' : 'text-yellow-600';
  const trendArrow = trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→';

  return (
    <div className="bg-gradient-to-br from-white via-gray-50 to-gray-100 rounded-2xl p-6 border-l-4 border-blue-600 shadow-lg hover:shadow-2xl transition-all hover:-translate-y-2 duration-300">
      <div className="text-xs font-bold text-gray-500 uppercase tracking-widest mb-2">{label}</div>
      <div className="text-5xl font-extrabold text-blue-900 mb-2">{value}</div>
      <div className={`flex items-center gap-2 text-sm font-bold mb-4 ${trendColor}`}>
        <span className="text-xl">{trendArrow}</span>
        <span>{trendText}</span>
      </div>
      <div className="h-2.5 bg-gray-200 rounded-full overflow-hidden mb-3 shadow-inner">
        <div 
          className="h-full bg-gradient-to-r from-green-500 via-blue-500 to-purple-500 rounded-full transition-all duration-500" 
          style={{ width: `${confidence}%` }}
        ></div>
      </div>
      <div className="text-xs text-gray-700 font-semibold">{confidence}% confidence {recommendation}</div>
    </div>
  );
}

function StatRow({ label, games, pts, ast, reb, threes, pra, highlight }: StatRowProps): JSX.Element {
  const getIndicator = (value: number, threshold: number): string => {
    if (value >= threshold + 1) return 'bg-green-500 shadow-sm';
    if (value >= threshold - 0.5 && value < threshold + 1) return 'bg-yellow-500 shadow-sm';
    return 'bg-red-500 shadow-sm';
  };

  const highlightColors: Record<string, string> = {
    blue: 'bg-blue-50/50',
    green: 'bg-green-50/50',
    purple: 'bg-purple-50/50',
  };

  const rowClass = highlight ? `hover:bg-gray-50 transition-colors ${highlightColors[highlight]}` : 'hover:bg-gray-50 transition-colors';

  return (
    <tr className={rowClass}>
      <td className="p-4 font-bold text-gray-800">{label}</td>
      <td className="p-4 text-gray-700">{games}</td>
      <td className="p-4">
        <span className="flex items-center gap-2">
          <span className={`w-2.5 h-2.5 rounded-full ${getIndicator(pts, 25.5)}`}></span>
          <span className="font-semibold text-gray-800">{pts}</span>
        </span>
      </td>
      <td className="p-4">
        <span className="flex items-center gap-2">
          <span className={`w-2.5 h-2.5 rounded-full ${getIndicator(ast, 7.5)}`}></span>
          <span className="font-semibold text-gray-800">{ast}</span>
        </span>
      </td>
      <td className="p-4">
        <span className="flex items-center gap-2">
          <span className={`w-2.5 h-2.5 rounded-full ${getIndicator(reb, 8.5)}`}></span>
          <span className="font-semibold text-gray-800">{reb}</span>
        </span>
      </td>
      <td className="p-4">
        <span className="flex items-center gap-2">
          <span className={`w-2.5 h-2.5 rounded-full ${getIndicator(threes, 1.5)}`}></span>
          <span className="font-semibold text-gray-800">{threes}</span>
        </span>
      </td>
      <td className="p-4">
        <span className="flex items-center gap-2">
          <span className={`w-2.5 h-2.5 rounded-full ${getIndicator(pra, 42.5)}`}></span>
          <span className="font-semibold text-gray-800">{pra}</span>
        </span>
      </td>
    </tr>
  );
}

function MatchupCard({ title, stats, tags }: MatchupCardProps): JSX.Element {
  return (
    <div className="bg-white border-2 border-gray-200 rounded-2xl p-6 shadow-lg hover:shadow-xl transition-shadow">
      <h3 className="font-bold mb-5 text-gray-900 text-lg">{title}</h3>
      <div className="space-y-4">
        {stats.map((stat, idx) => (
          <div key={idx} className="flex justify-between text-sm items-center">
            <span className="text-gray-600 font-medium">{stat.label}</span>
            <span className={`font-bold ${stat.valueColor || 'text-blue-900'}`}>{stat.value}</span>
          </div>
        ))}
        {tags && (
          <div className="text-sm pt-3 border-t border-gray-200">
            <span className="text-gray-600 font-medium">Hot Streaks:</span>
            <div className="flex flex-wrap gap-2 mt-3">
              {tags.map((tag, idx) => (
                <span key={idx} className="bg-red-100 text-red-800 text-xs font-bold px-3 py-1.5 rounded-full shadow-sm">{tag}</span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function PropHistoryRow({ prop, hitRate, last5, margin, trend, trendColor }: PropHistoryRowProps): JSX.Element {
  const colorMap: Record<string, { bg: string; text: string; hit: string }> = {
    green: { bg: 'bg-green-100', text: 'text-green-800', hit: 'text-green-600' },
    yellow: { bg: 'bg-yellow-100', text: 'text-yellow-800', hit: 'text-yellow-600' },
    red: { bg: 'bg-red-100', text: 'text-red-800', hit: 'text-red-600' },
  };

  const colors = colorMap[trendColor];

  return (
    <div className="grid grid-cols-5 hover:bg-gray-50 transition-colors">
      <div className="p-5 font-bold text-gray-800 border-r border-gray-100">{prop}</div>
      <div className="p-5 border-r border-gray-100">
        <span className={`font-bold text-lg ${colors.hit}`}>{hitRate}</span>
      </div>
      <div className="p-5 border-r border-gray-100">
        <div className="flex gap-1.5">
          {last5.map((hit, idx) => (
            <span
              key={idx}
              className={`w-7 h-7 ${hit ? 'bg-green-500' : 'bg-red-500'} rounded-lg text-white text-xs flex items-center justify-center font-bold shadow-sm`}
            >
              {hit ? '✓' : '✗'}
            </span>
          ))}
        </div>
      </div>
      <div className="p-5 border-r border-gray-100">
        <span className={`font-bold ${colors.hit}`}>{margin}</span>
      </div>
      <div className="p-5">
        <span className={`${colors.bg} ${colors.text} text-xs font-bold px-4 py-2 rounded-full shadow-sm inline-block`}>
          {trend === 'Fire' ? '🔥' : trend === 'Hot' ? '📈' : trend === 'Neutral' ? '→' : '📉'} {trend}
        </span>
      </div>
    </div>
  );
}

function OddsCard({ title, color, odds, bestOver, bestUnder }: OddsCardProps): JSX.Element {
  const colorMap: Record<string, { from: string; to: string; text: string; bg: string; btn: string }> = {
    blue: { from: 'from-blue-50', to: 'to-blue-100', text: 'text-blue-900', bg: 'bg-blue-50', btn: 'bg-blue-600' },
    green: { from: 'from-green-50', to: 'to-green-100', text: 'text-green-900', bg: 'bg-green-50', btn: 'bg-green-600' },
  };

  const colors = colorMap[color];

  return (
    <div className="bg-white border border-gray-200 rounded-2xl overflow-hidden shadow-lg">
      <div className={`bg-gradient-to-r ${colors.from} ${colors.to} p-5 border-b border-gray-200`}>
        <h3 className={`font-bold ${colors.text} text-lg`}>{title}</h3>
      </div>
      <div className="divide-y divide-gray-100">
        {odds.map((odd, idx) => (
          <div key={idx} className="grid grid-cols-3 p-5 hover:bg-gray-50 transition-colors">
            <div className="font-bold text-gray-800">{odd.book}</div>
            <div className="text-center">
              <span className="bg-green-100 text-green-800 font-bold px-4 py-2 rounded-lg text-sm shadow-sm">O {odd.over}</span>
            </div>
            <div className="text-center">
              <span className="bg-gray-100 text-gray-800 font-bold px-4 py-2 rounded-lg text-sm shadow-sm">U {odd.under}</span>
            </div>
          </div>
        ))}
        <div className={`grid grid-cols-3 p-5 ${colors.bg}`}>
          <div className="font-extrabold text-gray-900">Best Odds</div>
          <div className="text-center">
            <span className={`${colors.btn} text-white font-bold px-4 py-2 rounded-lg text-sm shadow-md`}>O {bestOver} ⭐</span>
          </div>
          <div className="text-center">
            <span className={`${colors.btn} text-white font-bold px-4 py-2 rounded-lg text-sm shadow-md`}>U {bestUnder} ⭐</span>
          </div>
        </div>
      </div>
    </div>
  );
}