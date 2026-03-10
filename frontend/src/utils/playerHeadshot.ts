/**
 * NBA CDN player headshot URLs.
 * https://cdn.nba.com/headshots/nba/latest/{size}/{playerId}.png
 * Some IDs may 404 (e.g. very new rookies) — handle with img onError.
 */
const BASE = 'https://cdn.nba.com/headshots/nba/latest'

export type HeadshotSize = '260x190' | '1040x760'

const SIZES: Record<HeadshotSize, string> = {
  '260x190': '260x190',
  '1040x760': '1040x760',
}

/**
 * Returns the NBA CDN headshot URL for a player by NBA person ID.
 * Use with <img src={...} onError={...} /> to show a fallback when image 404s.
 */
export function getPlayerHeadshotUrl(
  playerId: number | string,
  size: HeadshotSize = '260x190'
): string {
  const id = typeof playerId === 'string' ? playerId.trim() : String(playerId)
  if (!id) return ''
  const path = SIZES[size] || SIZES['260x190']
  return `${BASE}/${path}/${id}.png`
}
