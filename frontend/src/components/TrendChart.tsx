import { ResponsiveContainer, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine, Area, ComposedChart } from 'recharts'

interface TrendChartProps {
  title: string
  data: Array<{ idx: number; value: number; propLine: number; date?: string; matchup?: string }>
  color?: string
  yLabel?: string
  ariaLabel?: string
  showRollingAverages?: boolean
}

interface TooltipData {
  active?: boolean
  payload?: Array<{
    payload: {
      idx: number
      value: number
      propLine: number
      date?: string
      matchup?: string
      rolling5?: number | null
      rolling10?: number | null
      isOver: boolean
    }
  }>
}

export function TrendChart({ title, data, color, yLabel, ariaLabel, showRollingAverages = true }: TrendChartProps) {
  const root = typeof window !== 'undefined' ? getComputedStyle(document.documentElement) : null
  const primary = color || (root ? root.getPropertyValue('--chart-primary').trim() : '#2D68F8')
  const danger = root ? root.getPropertyValue('--chart-danger').trim() : '#EF4444'
  const warning = '#f59e0b'

  // Calculate rolling averages
  const enrichedData = data.map((d, idx) => {
    const rolling5 = idx >= 4 
      ? data.slice(idx - 4, idx + 1).reduce((sum, item) => sum + item.value, 0) / 5
      : null
    const rolling10 = idx >= 9
      ? data.slice(idx - 9, idx + 1).reduce((sum, item) => sum + item.value, 0) / 10
      : null
    
    return {
      ...d,
      rolling5: rolling5 !== null ? Number(rolling5.toFixed(1)) : null,
      rolling10: rolling10 !== null ? Number(rolling10.toFixed(1)) : null,
      isOver: d.value >= d.propLine,
    }
  })

  // Calculate overall average
  const overallAvg = data.length > 0
    ? data.reduce((sum, d) => sum + d.value, 0) / data.length
    : 0

  // Custom tooltip
  const CustomTooltip = ({ active, payload }: TooltipData) => {
    if (active && payload && payload.length && payload[0]?.payload) {
      const data = payload[0].payload
      return (
        <div className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg shadow-lg p-3 transition-colors duration-200">
          <p className="text-xs font-semibold text-gray-900 dark:text-slate-100 mb-1 transition-colors duration-200">
            Game {data.idx}
          </p>
          {data.date && (
            <p className="text-xs text-gray-600 dark:text-gray-400 mb-2 transition-colors duration-200">{data.date}</p>
          )}
          {data.matchup && (
            <p className="text-xs text-gray-600 dark:text-gray-400 mb-2 transition-colors duration-200">{data.matchup}</p>
          )}
          <div className="space-y-1">
            <div className="flex items-center justify-between gap-4">
              <span className="text-xs text-gray-600 dark:text-gray-400 transition-colors duration-200">Actual:</span>
              <span className="text-xs font-bold" style={{ color: primary }}>
                {data.value}
              </span>
            </div>
            {data.rolling5 !== null && (
              <div className="flex items-center justify-between gap-4">
                <span className="text-xs text-gray-600 dark:text-gray-400 transition-colors duration-200">5-Game Avg:</span>
                <span className="text-xs font-medium text-amber-600 dark:text-amber-400 transition-colors duration-200">
                  {data.rolling5}
                </span>
              </div>
            )}
            {data.rolling10 !== null && (
              <div className="flex items-center justify-between gap-4">
                <span className="text-xs text-gray-600 dark:text-gray-400 transition-colors duration-200">10-Game Avg:</span>
                <span className="text-xs font-medium text-purple-600 dark:text-purple-400 transition-colors duration-200">
                  {data.rolling10}
                </span>
              </div>
            )}
            <div className="flex items-center justify-between gap-4">
              <span className="text-xs text-gray-600 dark:text-gray-400 transition-colors duration-200">Prop Line:</span>
              <span className="text-xs font-bold" style={{ color: danger }}>
                {data.propLine}
              </span>
            </div>
            <div className="flex items-center justify-between gap-4 pt-1 border-t border-gray-200 dark:border-slate-700 transition-colors duration-200">
              <span className="text-xs text-gray-600 dark:text-gray-400 transition-colors duration-200">Result:</span>
              <span className={`text-xs font-bold ${data.isOver ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'} transition-colors duration-200`}>
                {data.isOver ? 'OVER' : 'UNDER'} ({data.isOver ? '+' : ''}{(data.value - data.propLine).toFixed(1)})
              </span>
            </div>
          </div>
        </div>
      )
    }
    return null
  }

  return (
    <div className="rounded-2xl bg-white dark:bg-slate-800 ring-1 ring-gray-100 dark:ring-slate-700 p-4 shadow-sm transition-colors duration-200">
      <div className="flex items-center justify-between mb-3">
        <div className="text-sm font-semibold text-gray-900 dark:text-slate-100 transition-colors duration-200">{title}</div>
        <div className="flex items-center gap-3 text-xs text-gray-600 dark:text-gray-400 transition-colors duration-200">
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: primary }}></div>
            <span>Actual</span>
          </div>
          {showRollingAverages && (
            <>
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 rounded-full bg-amber-500"></div>
                <span>5G Avg</span>
              </div>
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 rounded-full bg-purple-500"></div>
                <span>10G Avg</span>
              </div>
            </>
          )}
          <div className="flex items-center gap-1">
            <div className="w-2 h-0.5 border-t-2 border-dashed" style={{ borderColor: danger, width: '12px' }}></div>
            <span>Line</span>
          </div>
        </div>
      </div>
      <div className="h-[280px] w-full">
        <div role="img" aria-label={ariaLabel || title} className="w-full h-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={enrichedData} margin={{ top: 10, right: 12, left: 8, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis 
                dataKey="idx" 
                tick={{ fontSize: 11, fill: '#6b7280' }}
                axisLine={{ stroke: '#e5e7eb' }}
                tickLine={{ stroke: '#e5e7eb' }}
                label={{ value: 'Game', position: 'insideBottom', offset: -5, style: { textAnchor: 'middle', fill: '#6b7280', fontSize: 11 } }}
              />
              <YAxis 
                allowDecimals 
                tick={{ fontSize: 11, fill: '#6b7280' }}
                axisLine={{ stroke: '#e5e7eb' }}
                tickLine={{ stroke: '#e5e7eb' }}
                label={yLabel ? { value: yLabel, angle: -90, position: 'insideLeft', style: { textAnchor: 'middle', fill: '#6b7280', fontSize: 11 } } : undefined} 
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend 
                wrapperStyle={{ fontSize: '11px', paddingTop: '10px' }}
                iconType="line"
              />
              
              {/* Area fill for over/under line */}
              <Area
                type="monotone"
                dataKey="propLine"
                stroke="none"
                fill={danger}
                fillOpacity={0.05}
                name="Line Zone"
                hide
              />
              
              {/* Reference line for prop line */}
              <ReferenceLine 
                y={Number(data?.[0]?.propLine ?? 0)} 
                stroke={danger} 
                strokeDasharray="6 4" 
                strokeWidth={2}
                label={{ 
                  value: `Line: ${data?.[0]?.propLine ?? 0}`, 
                  position: 'right', 
                  fill: danger,
                  fontSize: 11,
                  offset: 5
                }} 
              />
              
              {/* Reference line for average */}
              <ReferenceLine 
                y={overallAvg} 
                stroke={warning} 
                strokeDasharray="4 4" 
                strokeWidth={1.5}
                strokeOpacity={0.6}
                label={{ 
                  value: `Avg: ${overallAvg.toFixed(1)}`, 
                  position: 'left', 
                  fill: warning,
                  fontSize: 10,
                  offset: 5
                }} 
              />
              
              {/* 10-game rolling average */}
              {showRollingAverages && (
                <Line 
                  type="monotone" 
                  dataKey="rolling10" 
                  stroke="#a855f7" 
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  dot={false}
                  name="10-Game Avg"
                  connectNulls={false}
                />
              )}
              
              {/* 5-game rolling average */}
              {showRollingAverages && (
                <Line 
                  type="monotone" 
                  dataKey="rolling5" 
                  stroke="#f59e0b" 
                  strokeWidth={2.5}
                  strokeDasharray="3 3"
                  dot={false}
                  name="5-Game Avg"
                  connectNulls={false}
                />
              )}
              
              {/* Main value line */}
              <Line 
                type="monotone" 
                dataKey="value" 
                stroke={primary} 
                strokeWidth={3} 
                dot={{ 
                  r: 4, 
                  fill: primary,
                  strokeWidth: 2,
                  stroke: '#fff'
                }}
                activeDot={{ 
                  r: 6, 
                  fill: primary,
                  strokeWidth: 2,
                  stroke: '#fff'
                }}
                name="Actual"
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>
      {/* Stats summary */}
      <div className="mt-3 pt-3 border-t border-gray-100 dark:border-slate-700 grid grid-cols-3 gap-2 text-xs transition-colors duration-200">
        <div>
          <div className="text-gray-500 dark:text-gray-400 transition-colors duration-200">Avg</div>
          <div className="font-semibold text-gray-900 dark:text-slate-100 transition-colors duration-200">{overallAvg.toFixed(1)}</div>
        </div>
        <div>
          <div className="text-gray-500 dark:text-gray-400 transition-colors duration-200">Over Line</div>
          <div className="font-semibold text-green-600 dark:text-green-400 transition-colors duration-200">
            {enrichedData.filter(d => d.isOver).length}/{enrichedData.length}
          </div>
        </div>
        <div>
          <div className="text-gray-500 dark:text-gray-400 transition-colors duration-200">Hit Rate</div>
          <div className="font-semibold text-blue-600 dark:text-blue-400 transition-colors duration-200">
            {((enrichedData.filter(d => d.isOver).length / enrichedData.length) * 100).toFixed(0)}%
          </div>
        </div>
      </div>
    </div>
  )
}


