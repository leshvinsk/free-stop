// Team logos and driver nationalities. OpenF1 has neither (its country_code is empty for
// current seasons), so they are looked up here.

const LOGO_BASE =
  'https://media.formula1.com/image/upload/c_lfill,w_96/f_png/q_auto/v1740000000/common/f1'
const logo = (season: number, slug: string, white = false) =>
  `${LOGO_BASE}/${season}/${slug}/${season}${slug}logo${white ? 'white' : ''}.png`

// Team name as OpenF1 sends it → its logo. Teams whose official logo is black or navy
// (Mercedes, Audi, Cadillac, Aston Martin, Racing Bulls) would vanish on the dark
// background, so they use F1's white edition.
const TEAM_LOGOS: Record<string, string> = {
  McLaren: logo(2026, 'mclaren'),
  Ferrari: logo(2026, 'ferrari'),
  Mercedes: logo(2026, 'mercedes', true),
  'Red Bull Racing': logo(2026, 'redbullracing'),
  'Aston Martin': logo(2026, 'astonmartin', true),
  Alpine: logo(2026, 'alpine'),
  Williams: logo(2026, 'williams'),
  'Racing Bulls': logo(2026, 'racingbulls', true),
  RB: logo(2024, 'rb', true),
  'Haas F1 Team': logo(2026, 'haasf1team'),
  // F1's Sauber logo sits on a black disc; this is the same mark on a transparent background
  'Kick Sauber': '/logos/kicksauber.png',
  Audi: logo(2026, 'audi', true),
  Cadillac: logo(2026, 'cadillac', true),
}

export function teamLogo(teamName: string): string | null {
  return TEAM_LOGOS[teamName] ?? null
}

// Driver acronym → ISO 3166 country code, covering every driver since 2024
const NATIONALITY: Record<string, string> = {
  ALB: 'th',
  ALO: 'es',
  ANT: 'it',
  BEA: 'gb',
  BOR: 'br',
  BOT: 'fi',
  COL: 'ar',
  DOO: 'au',
  GAS: 'fr',
  HAD: 'fr',
  HAM: 'gb',
  HUL: 'de',
  LAW: 'nz',
  LEC: 'mc',
  LIN: 'gb',
  MAG: 'dk',
  NOR: 'gb',
  OCO: 'fr',
  PER: 'mx',
  PIA: 'au',
  RIC: 'au',
  RUS: 'gb',
  SAI: 'es',
  SAR: 'us',
  STR: 'ca',
  TSU: 'jp',
  VER: 'nl',
  ZHO: 'cn',
}

export function nationality(acronym: string): string | null {
  return NATIONALITY[acronym] ?? null
}

const countryNames = new Intl.DisplayNames(undefined, { type: 'region' })

export function countryName(code: string): string {
  return countryNames.of(code.toUpperCase()) ?? code.toUpperCase()
}

export function flagUrl(code: string): string {
  return `https://flagcdn.com/w80/${code}.png`
}

// Side-on car renders from F1's image library, nose to the right. Scaled to 1600px wide:
// sharp at the largest size shown, about a third of the full 3840px download.
const CAR_BASE =
  'https://media.formula1.com/image/upload/c_scale,w_1600/f_auto/q_auto:best/v1740000000/common/f1'
const CAR_SLUGS: Record<string, string> = {
  McLaren: 'mclaren',
  Ferrari: 'ferrari',
  Mercedes: 'mercedes',
  'Red Bull Racing': 'redbullracing',
  'Aston Martin': 'astonmartin',
  Alpine: 'alpine',
  Williams: 'williams',
  'Racing Bulls': 'racingbulls',
  RB: 'rb',
  'Haas F1 Team': 'haasf1team',
  'Kick Sauber': 'kicksauber',
  Audi: 'audi',
  Cadillac: 'cadillac',
}

/** The car a team raced in a given season, or null when there's no image of it. */
export function teamCar(teamName: string, season: number): string | null {
  // F1 filed Haas's 2024 car under a shorter name
  const slug = teamName === 'Haas F1 Team' && season === 2024 ? 'haas' : CAR_SLUGS[teamName]
  if (!slug) return null
  return `${CAR_BASE}/${season}/${slug}/${season}${slug}carright.png`
}

// Track outlines from F1's image library, keyed by OpenF1's session location
const TRACK_BASE =
  'https://media.formula1.com/image/upload/c_fit,h_160/q_auto/v1740000000/common/f1/2026/track'
const TRACK_SLUGS: Record<string, string> = {
  Melbourne: 'melbourne',
  Shanghai: 'shanghai',
  Suzuka: 'suzuka',
  Sakhir: 'sakhir',
  Jeddah: 'jeddah',
  Miami: 'miami',
  'Miami Gardens': 'miami',
  Imola: 'imola',
  Monaco: 'montecarlo',
  'Monte Carlo': 'montecarlo',
  Barcelona: 'catalunya',
  Montréal: 'montreal',
  Spielberg: 'spielberg',
  Silverstone: 'silverstone',
  'Spa-Francorchamps': 'spafrancorchamps',
  Budapest: 'hungaroring',
  Zandvoort: 'zandvoort',
  Monza: 'monza',
  Baku: 'baku',
  'Marina Bay': 'singapore',
  Singapore: 'singapore',
  Austin: 'austin',
  'Mexico City': 'mexicocity',
  'São Paulo': 'interlagos',
  'Las Vegas': 'lasvegas',
  Lusail: 'lusail',
  'Yas Island': 'yasmarinacircuit',
  'Yas Marina': 'yasmarinacircuit',
  Madrid: 'madring',
  'Kuala Lumpur': 'kualalumpur',
}

/** White outline of the circuit at a race location. Unknown venues try a plain slug. */
export function trackOutline(location: string): string {
  const slug =
    TRACK_SLUGS[location] ??
    location
      .normalize('NFD')
      .replace(/[^A-Za-z]/g, '')
      .toLowerCase()
  return `${TRACK_BASE}/2026track${slug}whiteoutline.svg`
}
