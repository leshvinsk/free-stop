/**
 * Team display data. Verified values (TEAM_INFO_VERIFIED) always override
 * the daily-scraped fallback (teams_scraped.json). New seasons and new teams
 * are populated automatically from the scraper until a verified entry is added.
 */
import scrapedRaw from './teams_scraped.json'

export interface CarHotspot {
  id: string
  label: string
  /** Position as percentage of the car image (left edge = 0, right = 100) */
  x: number
  /** Position as percentage of the car image (top = 0, bottom = 100) */
  y: number
  specs: { label: string; value: string }[]
  note?: string
}

export interface CarInfo {
  model: string
  powerUnit: string
  hotspots: CarHotspot[]
}

export interface TeamInfo {
  /** "A → B" marks a mid-season change */
  principal: Record<number, string>
  /** Extra leadership context shown under the principal */
  principalNote?: Record<number, string>
  base: string
  founded: string
  chassis: Record<number, string>
  powerUnit: Record<number, string>
}

interface ScrapedTeam {
  principal?: string
  base?: string
  chassis?: string
  power_unit?: string
  founded?: string
}

const _scraped = scrapedRaw as { year: number; teams: Record<string, ScrapedTeam> }

// ── Hotspot definitions (positions tuned to the F1 side-view car silhouette) ──

const HOTSPOTS_2026: Omit<CarHotspot, 'id'>[] = [
  {
    label: 'Front Wing',
    x: 93,
    y: 72,
    specs: [
      { label: 'Material', value: 'Carbon fibre' },
      { label: 'Function', value: 'Downforce + aero balance' },
      { label: 'Adjustment', value: 'Flap angle at pit stop' },
    ],
    note: '2026 regs reduced front-wing complexity to clean up turbulent air behind the car.',
  },
  {
    label: 'Front Tyres',
    x: 83,
    y: 82,
    specs: [
      { label: 'Supplier', value: 'Pirelli' },
      { label: 'Rim size', value: '18 inch' },
      { label: 'Compounds', value: 'C1 – C5 (hard to soft)' },
      { label: 'Width', value: '305 mm front / 405 mm rear' },
    ],
    note: 'Low-profile tyres introduced in 2022. Pirelli sole supplier through 2027.',
  },
  {
    label: 'Suspension',
    x: 66,
    y: 55,
    specs: [
      { label: 'Type', value: 'Double wishbone push-rod' },
      { label: 'Material', value: 'Carbon fibre uprights' },
      { label: 'Anti-roll', value: 'Adjustable front and rear' },
    ],
  },
  {
    label: 'Halo',
    x: 57,
    y: 30,
    specs: [
      { label: 'Material', value: 'Grade 5 titanium' },
      { label: 'Weight', value: '~7 kg' },
      { label: 'Load rating', value: 'Withstands 125 kN (≈12.5 t)' },
      { label: 'Mandatory since', value: '2018' },
    ],
    note: "Required on all F1 cars. Credited with saving multiple drivers' lives.",
  },
  {
    label: 'Power Unit',
    x: 39,
    y: 44,
    specs: [
      { label: 'Configuration', value: '1.6 L V6 turbo-hybrid' },
      { label: 'Total output', value: '~1,000 hp' },
      { label: 'ICE share', value: '~500 hp @ ~15,000 rpm' },
      { label: 'Electrical share', value: '~500 hp (MGU-K)' },
      { label: 'ERS store', value: '4 MJ per lap' },
      { label: 'Fuel per race', value: '70 kg (biofuel blend)' },
    ],
    note: '2026 regulations mandate 50% hybrid power — a major step toward net-zero.',
  },
  {
    label: 'Gearbox',
    x: 25,
    y: 50,
    specs: [
      { label: 'Type', value: '8-speed semi-automatic' },
      { label: 'Actuation', value: 'Electrohydraulic' },
      { label: 'Change time', value: '~50 ms' },
      { label: 'Material', value: 'Carbon fibre casing' },
    ],
  },
  {
    label: 'Rear Tyres',
    x: 14,
    y: 82,
    specs: [
      { label: 'Supplier', value: 'Pirelli' },
      { label: 'Rim size', value: '18 inch' },
      { label: 'Width', value: '405 mm' },
      { label: 'Pressure', value: 'Team-defined within FIA limits' },
    ],
  },
  {
    label: 'Active Aero',
    x: 6,
    y: 21,
    specs: [
      { label: 'System', value: 'Hydraulic active rear wing' },
      { label: 'Replaced', value: 'DRS (drag reduction system)' },
      { label: 'Effect', value: 'Reduces drag on straights' },
      { label: 'Control', value: 'FIA-managed automatic activation' },
    ],
    note: 'From 2026, DRS was replaced by an automated active aero system allowed on designated straights.',
  },
  {
    label: 'Floor / Diffuser',
    x: 45,
    y: 75,
    specs: [
      { label: 'Concept', value: 'Ground effect venturi tunnels' },
      { label: 'Downforce share', value: '~40% of total' },
      { label: 'Material', value: 'Carbon fibre sandwich' },
    ],
    note: 'Ground effect was reintroduced in 2022. The floor is the single most sensitive aero surface.',
  },
]

function hotspots(): CarHotspot[] {
  return HOTSPOTS_2026.map((h, i) => ({ ...h, id: `h${i}` }))
}

// ── Verified team data (always overrides scraped fallback) ──────────────────

const TEAM_INFO_VERIFIED: Record<string, TeamInfo> = {
  mercedes: {
    principal: { 2024: 'Toto Wolff', 2025: 'Toto Wolff', 2026: 'Toto Wolff' },
    base: 'Brackley, UK',
    founded: '2010',
    chassis: { 2024: 'W15', 2025: 'W16', 2026: 'W17' },
    powerUnit: {
      2024: 'Mercedes-AMG F1 M15 E Performance',
      2025: 'Mercedes-AMG F1 M16 E Performance',
      2026: 'Mercedes-AMG F1 M17',
    },
  },
  'red-bull-racing': {
    principal: {
      2024: 'Christian Horner',
      2025: 'Christian Horner → Laurent Mekies',
      2026: 'Laurent Mekies',
    },
    base: 'Milton Keynes, UK',
    founded: '2005',
    chassis: { 2024: 'RB20', 2025: 'RB21', 2026: 'RB22' },
    powerUnit: { 2024: 'Honda RBPTH002', 2025: 'Honda RBPTH003', 2026: 'Red Bull Ford DM01' },
  },
  ferrari: {
    principal: { 2024: 'Frédéric Vasseur', 2025: 'Frédéric Vasseur', 2026: 'Frédéric Vasseur' },
    base: 'Maranello, Italy',
    founded: '1929',
    chassis: { 2024: 'SF-24', 2025: 'SF-25', 2026: 'SF-26' },
    powerUnit: { 2024: 'Ferrari 066/12', 2025: 'Ferrari 066/14', 2026: 'Ferrari 067/6' },
  },
  mclaren: {
    principal: { 2024: 'Andrea Stella', 2025: 'Andrea Stella', 2026: 'Andrea Stella' },
    base: 'Woking, UK',
    founded: '1963',
    chassis: { 2024: 'MCL38', 2025: 'MCL39', 2026: 'MCL40' },
    powerUnit: {
      2024: 'Mercedes-AMG F1 M15 E Performance',
      2025: 'Mercedes-AMG F1 M16 E Performance',
      2026: 'Mercedes-AMG F1 M17',
    },
  },
  'aston-martin': {
    principal: { 2024: 'Mike Krack', 2025: 'Andy Cowell', 2026: 'Adrian Newey' },
    principalNote: { 2025: 'Mike Krack moved to Chief Trackside Officer' },
    base: 'Silverstone, UK',
    founded: '2021',
    chassis: { 2024: 'AMR24', 2025: 'AMR25', 2026: 'AMR26' },
    powerUnit: {
      2024: 'Mercedes-AMG F1 M15 E Performance',
      2025: 'Mercedes-AMG F1 M16 E Performance',
      2026: 'Honda RA626H',
    },
  },
  alpine: {
    principal: {
      2024: 'Bruno Famin → Oliver Oakes',
      2025: 'Oliver Oakes → Flavio Briatore',
      2026: 'Flavio Briatore',
    },
    principalNote: {
      2025: 'Briatore covering Team Principal duties',
      2026: 'Covers Team Principal duties · Steve Nielsen, Managing Director',
    },
    base: 'Enstone, UK',
    founded: '2021',
    chassis: { 2024: 'A524', 2025: 'A525', 2026: 'A526' },
    powerUnit: {
      2024: 'Renault E-Tech RE24',
      2025: 'Renault E-Tech RE25',
      2026: 'Mercedes-AMG F1 M17',
    },
  },
  williams: {
    principal: { 2024: 'James Vowles', 2025: 'James Vowles', 2026: 'James Vowles' },
    base: 'Grove, UK',
    founded: '1977',
    chassis: { 2024: 'FW46', 2025: 'FW47', 2026: 'FW48' },
    powerUnit: {
      2024: 'Mercedes-AMG F1 M15 E Performance',
      2025: 'Mercedes-AMG F1 M16 E Performance',
      2026: 'Mercedes-AMG F1 M17',
    },
  },
  'racing-bulls': {
    principal: {
      2024: 'Laurent Mekies',
      2025: 'Laurent Mekies → Alan Permane',
      2026: 'Alan Permane',
    },
    base: 'Faenza, Italy',
    founded: '2006',
    chassis: { 2024: 'VCARB 01', 2025: 'VCARB 02', 2026: 'VCARB 03' },
    powerUnit: { 2024: 'Honda RBPTH002', 2025: 'Honda RBPTH003', 2026: 'Red Bull Ford DM01' },
  },
  haas: {
    principal: { 2024: 'Ayao Komatsu', 2025: 'Ayao Komatsu', 2026: 'Ayao Komatsu' },
    base: 'Kannapolis, USA',
    founded: '2014',
    chassis: { 2024: 'VF-24', 2025: 'VF-25', 2026: 'VF-26' },
    powerUnit: { 2024: 'Ferrari 066/12', 2025: 'Ferrari 066/14', 2026: 'Ferrari 067/6' },
  },
  audi: {
    principal: {
      2024: 'Alessandro Alunni Bravi',
      2025: 'Mattia Binotto → Jonathan Wheatley',
      2026: 'Jonathan Wheatley → Mattia Binotto',
    },
    principalNote: {
      2024: 'Team Representative, not a formal Team Principal',
      2025: 'Binotto led the team before Wheatley took over',
      2026: 'Allan McNish, Racing Director',
    },
    base: 'Hinwil, Switzerland',
    founded: '1993',
    chassis: { 2024: 'C44', 2025: 'C45', 2026: 'R26' },
    powerUnit: { 2024: 'Ferrari 066/12', 2025: 'Ferrari 066/14', 2026: 'Audi AFR 26 Hybrid' },
  },
  cadillac: {
    principal: { 2026: 'Graeme Lowdon → Marcin Budkowski' },
    base: 'Silverstone, UK',
    founded: '2025',
    chassis: { 2026: 'MAC-26' },
    powerUnit: { 2026: 'Ferrari 067/6' },
  },
}

// ── Merge verified + scraped (verified always wins) ─────────────────────────

function _mergeTeam(key: string): TeamInfo | null {
  const v = TEAM_INFO_VERIFIED[key]
  const s = _scraped.teams[key]
  if (!v && !s) return null
  const y = _scraped.year
  return {
    principal: {
      ...(s?.principal ? { [y]: s.principal } : {}),
      ...(v?.principal ?? {}),
    },
    principalNote: v?.principalNote,
    base: v?.base ?? s?.base ?? '—',
    founded: v?.founded ?? s?.founded ?? '—',
    chassis: {
      ...(s?.chassis ? { [y]: s.chassis } : {}),
      ...(v?.chassis ?? {}),
    },
    powerUnit: {
      ...(s?.power_unit ? { [y]: s.power_unit } : {}),
      ...(v?.powerUnit ?? {}),
    },
  }
}

function _buildTeamInfo(): Record<string, TeamInfo> {
  const keys = new Set([...Object.keys(TEAM_INFO_VERIFIED), ...Object.keys(_scraped.teams)])
  const result: Record<string, TeamInfo> = {}
  for (const key of keys) {
    const info = _mergeTeam(key)
    if (info) result[key] = info
  }
  return result
}

export const TEAM_INFO: Record<string, TeamInfo> = _buildTeamInfo()

export function getCarHotspots(): CarHotspot[] {
  return hotspots()
}

export function getTeamInfo(key: string): TeamInfo | null {
  return TEAM_INFO[key] ?? null
}
