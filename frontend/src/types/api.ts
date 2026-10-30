// Mirror of backend app/models.py — keep these in sync.

export type FlagStatus = 'GREEN' | 'SC' | 'VSC' | 'RED'

export interface Progress {
  rounds_total: number
  rounds_scored: number
  complete: boolean
}

export interface StopDetail {
  /** The in-lap. */
  lap: number
  /** Pit-lane time. */
  pit_duration: number
  /** Race state while the car was in the pit lane. */
  status: FlagStatus
  /** Seconds lost to the field over the in-lap and out-lap, allowing for the car's usual pace. */
  time_loss: number | null
  /** Timing luck of the stop itself. */
  luck: number | null
  /** Pit-lane time against normal; positive is quicker than usual. */
  execution: number | null
  /** Seconds of penalty served at this stop. */
  penalty: number
  /** ≤ 0: a neutralisation came out just after this stop. */
  missed: number
  missed_status: FlagStatus | null
  missed_lap: number | null
  /** luck + missed: what this stop adds to race luck. */
  delta: number | null
  note: string | null
}

export interface RaceDriverResult {
  driver_number: number
  full_name: string
  name_acronym: string
  team_name: string
  /** Stable across renames, for linking to the team page. */
  team_key: string
  team_colour: string | null
  headshot_url: string | null
  /** Against this race's field average. */
  race_luck: number | null
  /** Sum of the driver's stops against a normal stop. */
  race_luck_raw: number | null
  race_execution: number | null
  no_stops: boolean
  insufficient_baseline_data: boolean
  /** DNF / DNS / DSQ: no luck or crew score for that race. */
  outcome: string | null
  stops: StopDetail[]
}

export interface RaceEvent {
  lap: number
  type: FlagStatus
  message: string
}

export interface RaceDetail {
  session_key: number
  round: number | null
  race_name: string
  circuit: string
  date: string
  total_laps: number
  /** Time a normal green-flag stop costs. */
  baseline_pit_loss: number | null
  /** No green-flag stops to measure, so estimated from pit-lane time. */
  baseline_estimated: boolean
  typical_pit_lane: number | null
  insufficient_baseline_data: boolean
  /** Mean raw race luck; race_luck is measured from here. */
  field_average: number | null
  drivers: RaceDriverResult[]
  events: RaceEvent[]
}

export interface SeasonDriver {
  driver_number: number
  full_name: string
  name_acronym: string
  team_name: string
  /** Stable across renames, for linking to the team page. */
  team_key: string
  team_colour: string | null
  headshot_url: string | null
  /** Average race luck against the field; the ranking value. */
  luck_per_race: number
  /** Total race luck against the field. */
  season_luck: number
  season_execution: number
  races_scored: number
  races_no_stops: number
}

export interface SeasonSummary {
  year: number
  progress: Progress
  /** Races needed to be named luckiest or unluckiest. */
  min_races: number
  drivers: SeasonDriver[]
}

export interface RaceRef {
  session_key: number
  round: number
  race_name: string
  circuit: string
  /** e.g. "Melbourne"; mapped to a track outline. */
  location: string
  date: string
}

export interface DriverRaceResult {
  session_key: number
  round: number
  race_name: string
  circuit: string
  date: string
  /** Against this race's field average. */
  race_luck: number | null
  race_luck_raw: number | null
  race_execution: number | null
  no_stops: boolean
  insufficient_baseline_data: boolean
  outcome: string | null
}

export interface DriverSummary {
  driver_number: number
  full_name: string
  name_acronym: string
  team_name: string
  /** Stable across renames, for linking to the team page. */
  team_key: string
  team_colour: string | null
  headshot_url: string | null
  luck_per_race: number
  season_luck: number
  season_execution: number
  races_scored: number
  progress: Progress
  races: DriverRaceResult[]
}

export interface CircuitMap {
  /** Which session the trace came from, e.g. "Qualifying". */
  source: string
  width: number
  height: number
  points: [number, number][]
  /** [start, end] point indices; end < start wraps across the line. */
  drs_zones: [number, number][]
  /** Full-throttle stretches, same index convention. */
  straights: [number, number][]
  clockwise: boolean
  /** Point indices where sectors 2 and 3 begin. */
  sectors: number[]
  /** False from 2026, when active aero replaced DRS. */
  drs_era: boolean
}

export interface WeatherSample {
  minute: number
  air: number | null
  track: number | null
  rain: boolean
}

export interface RaceWeather {
  air_min: number | null
  air_max: number | null
  track_min: number | null
  track_max: number | null
  humidity: number | null
  wind_speed: number | null
  /** Average degrees the wind blows from. */
  wind_direction: number | null
  /** Share of readings with rain, 0..1. */
  rain_share: number
  samples: WeatherSample[]
}

export interface RacePhoto {
  url: string
  /** The file's Commons page, for attribution. */
  page_url: string
  caption: string
  author: string
  /** e.g. "CC BY-SA 4.0" */
  license: string
  /** YYYY-MM-DD */
  taken: string | null
}

export interface RacePhotos {
  /** "weekend" (that race weekend), "circuit" (other years) or "none". */
  scope: 'weekend' | 'circuit' | 'none'
  category: string | null
  photos: RacePhoto[]
}

export interface TeamSeason {
  year: number
  /** What the team was called that season. */
  name: string
}

export interface TeamRaceDriver {
  driver_number: number
  name_acronym: string
  race_luck: number | null
  outcome: string | null
}

export interface TeamRaceResult {
  session_key: number
  round: number
  race_name: string
  circuit: string
  date: string
  /** The team's drivers combined, against the field. */
  race_luck: number | null
  race_execution: number | null
  no_stops: boolean
  insufficient_baseline_data: boolean
  drivers: TeamRaceDriver[]
}

export interface TeamStanding {
  key: string
  name: string
  team_colour: string | null
  luck_per_race: number
  races_scored: number
}

export interface TeamSummary {
  key: string
  name: string
  team_colour: string | null
  year: number
  /** Every season of this team's lineage, oldest first. */
  seasons: TeamSeason[]
  progress: Progress
  /** Position among the teams by luck per race. */
  rank: number | null
  teams_count: number
  luck_per_race: number
  season_luck: number
  season_execution: number
  pit_stops: number
  /** Stats from their races for this team only. */
  drivers: SeasonDriver[]
  races: TeamRaceResult[]
  /** Every team this season, luckiest first. */
  standings: TeamStanding[]
}
