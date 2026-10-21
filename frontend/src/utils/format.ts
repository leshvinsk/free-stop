export const FIRST_SEASON = 2024 // earliest season Free Stop covers
export const CURRENT_SEASON = new Date().getFullYear()

export function formatLuck(value: number | null, digits = 3): string {
  if (value === null) return '—'
  const fixed = value.toFixed(digits)
  return value > 0 ? `+${fixed}s` : `${fixed}s`
}

export function luckClass(value: number | null): string {
  if (value === null || value === 0) return 'muted'
  return value > 0 ? 'lucky' : 'unlucky'
}

/** OpenF1 sends team colours as bare hex ("3671C6"). */
export function teamColour(hex: string | null | undefined): string {
  return hex ? `#${hex.replace('#', '')}` : '#6b6b76'
}

export function formatDate(iso: string): string {
  return new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

/** "Max Verstappen" → { first: "Max", last: "Verstappen" } */
export function splitName(fullName: string): { first: string; last: string } {
  const parts = fullName.trim().split(/\s+/)
  const last = parts.pop() ?? ''
  return { first: parts.join(' '), last }
}

/** OpenF1 sends full_name as "Charles LECLERC" — title-case the all-caps last name for display. */
export function formatFullName(fullName: string): string {
  return fullName
    .split(/\s+/)
    .map((w) => (w === w.toUpperCase() ? w.charAt(0) + w.slice(1).toLowerCase() : w))
    .join(' ')
}

/** OpenF1 links F1's thumbnail-sized headshot ("1col"); ask F1's image server for a larger one. */
export function portraitUrl(url: string | null | undefined): string | null {
  return url ? url.replace('/1col/', '/4col/') : null
}
