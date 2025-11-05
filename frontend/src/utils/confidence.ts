// Simple confidence heuristic based on recent average vs line and hit rate
export function calculateConfidenceBasic(values: number[], line: number): number {
  if (!values.length || !isFinite(line)) return 50
  const avg = values.reduce((a, b) => a + b, 0) / values.length
  const hitRate = values.filter(v => v > line).length / values.length
  // Base from hit rate
  let score = hitRate * 100
  // Boost by differential magnitude
  const differential = avg - line
  const boost = Math.max(0, Math.min(20, Math.abs(differential) * 4))
  score = Math.max(0, Math.min(100, score + boost))
  return Math.round(score)
}


