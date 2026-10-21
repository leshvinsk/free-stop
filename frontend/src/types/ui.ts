import type { RouteLocationRaw } from 'vue-router'

export interface TowerRow {
  key: string | number
  /** Short bold code — driver acronym or round number. */
  code: string
  title: string
  subtitle?: string
  /** CSS colour for the team badge. */
  colour: string
  /** Team name, for its logo. Without one (or if it fails to load) a colour bar is shown. */
  team?: string
  /** Where clicking the team logo goes, e.g. the team page. */
  teamTo?: RouteLocationRaw
  /** Tints the row, e.g. the team whose page this is. */
  highlight?: boolean
  /** Car number, shown next to the code. */
  number?: number
  /** ISO country code, shown as a flag. */
  country?: string | null
  luck: number | null
  /** Short label shown in its own column, e.g. "2 stops". */
  tag?: string
  /** Shown instead of the luck value when set (e.g. "DNF"). */
  note?: string
  /** Shown in the lucky/unlucky column instead of a bar, e.g. "N/A". */
  barNote?: string
  to?: RouteLocationRaw
}
