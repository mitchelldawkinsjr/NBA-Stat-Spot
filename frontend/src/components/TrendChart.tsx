import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine } from 'recharts'

export function TrendChart({ title, data, color = '#2563eb', yLabel, ariaLabel }: { title: string; data: Array<{ idx: number; value: number; propLine: number }>; color?: string; yLabel?: string; ariaLabel?: string }) {
  return (
    <div style={{ border: '1px solid #e5e7eb', borderRadius: 10, background: '#fff', padding: 12 }}>
      <div style={{ fontWeight: 600, marginBottom: 8 }}>{title}</div>
      <div style={{ height: 260 }}>
        <div role="img" aria-label={ariaLabel || title} style={{ width: '100%', height: '100%' }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="idx" tick={false} axisLine={false} tickLine={false} />
            <YAxis allowDecimals label={yLabel ? { value: yLabel, angle: -90, position: 'insideLeft' } : undefined} />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="value" stroke={color} strokeWidth={2} dot={{ r: 3 }} name="Actual" />
            <ReferenceLine y={Number(data?.[0]?.propLine ?? 0)} stroke="#ef4444" strokeDasharray="8 4" label={{ value: 'Line', position: 'right', fill: '#ef4444' }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}


