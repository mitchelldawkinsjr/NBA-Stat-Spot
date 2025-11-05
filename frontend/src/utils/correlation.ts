export function pearsonCorrelation(xs: number[], ys: number[]): number {
  const n = Math.min(xs.length, ys.length)
  if (n < 3) return 0
  const x = xs.slice(-n)
  const y = ys.slice(-n)
  const mean = (arr: number[]) => arr.reduce((a, b) => a + b, 0) / arr.length
  const mx = mean(x)
  const my = mean(y)
  let num = 0
  let dx = 0
  let dy = 0
  for (let i = 0; i < n; i++) {
    const vx = x[i] - mx
    const vy = y[i] - my
    num += vx * vy
    dx += vx * vx
    dy += vy * vy
  }
  const den = Math.sqrt(dx * dy)
  if (den === 0) return 0
  return Math.max(-1, Math.min(1, num / den))
}


