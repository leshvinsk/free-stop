import type { FlagStatus, RaceDetail, RaceDriverResult, StopDetail } from '@/types/api'

export type StoryKind = 'lucky' | 'missed' | 'penalty' | 'crew'

export interface Story {
  key: string
  kind: StoryKind
  driver: RaceDriverResult
  /** Seconds the moment was worth; drives ordering and colour. */
  value: number
  headline: string
  detail: string
}

export const FLAG_NAME: Record<FlagStatus, string> = {
  GREEN: 'green flag',
  SC: 'safety car',
  VSC: 'virtual safety car',
  RED: 'red flag',
}

// Below these, a stop is within normal noise and not worth a headline
const NEUTRALISED_LUCK = 3
const GREEN_LUCK = 5
const SLOW_CREW = 2

const s = (n: number) => `${Math.abs(n).toFixed(3)}s`

function storiesForStop(race: RaceDetail, driver: RaceDriverResult, stop: StopDetail): Story[] {
  const key = `${driver.driver_number}-${stop.lap}`
  const code = driver.name_acronym
  const stories: Story[] = []

  if (stop.missed < 0 && stop.missed_status && stop.missed_lap) {
    const flag = FLAG_NAME[stop.missed_status]
    stories.push({
      key: `${key}-missed`,
      kind: 'missed',
      driver,
      value: stop.missed,
      headline: `${code} pitted just before the ${flag}`,
      detail:
        stop.missed_status === 'RED'
          ? `Pitted on lap ${stop.lap}; the red flag on lap ${stop.missed_lap} handed everyone a free tyre change. That stop cost ${s(stop.missed)}.`
          : `Pitted on lap ${stop.lap}; the ${flag} came out on lap ${stop.missed_lap} and\nrivals stopped for free. Missed out on ${s(stop.missed)}.`,
    })
  }

  if (stop.luck !== null) {
    const threshold = stop.status === 'GREEN' ? GREEN_LUCK : NEUTRALISED_LUCK
    if (stop.luck >= threshold) {
      const cost = stop.time_loss !== null ? Math.max(0, stop.time_loss) : null
      const normal = race.baseline_pit_loss
      stories.push({
        key: `${key}-lucky`,
        kind: 'lucky',
        driver,
        value: stop.luck,
        headline:
          stop.status === 'GREEN'
            ? `${code} timed it perfectly as the race was neutralised`
            : `${code} pitted under the ${FLAG_NAME[stop.status]}`,
        detail:
          cost !== null && normal !== null
            ? `Lap ${stop.lap}: stop cost ${s(cost)} while the field paid the usual ${s(normal)}.`
            : `Lap ${stop.lap}: saved ${s(stop.luck)} compared with a normal stop.`,
      })
    }
  }

  if (stop.penalty > 0) {
    stories.push({
      key: `${key}-penalty`,
      kind: 'penalty',
      driver,
      value: -stop.penalty,
      headline: `${code} served a ${stop.penalty}s penalty`,
      detail: `Served at the lap ${stop.lap} pit stop. Counted as a penalty — not bad luck or a slow crew.`,
    })
  }

  if (stop.execution !== null && stop.execution <= -SLOW_CREW) {
    stories.push({
      key: `${key}-crew`,
      kind: 'crew',
      driver,
      value: stop.execution,
      headline: `${code} slow pit stop`,
      detail: `Lap ${stop.lap}: ${s(stop.execution)} longer in the pit lane than a normal stop. That's on the crew, not luck.`,
    })
  }

  return stories
}

/** The race's defining pit-lane moments, biggest first. */
export function raceStories(race: RaceDetail, limit = 8): Story[] {
  return race.drivers
    .flatMap((d) => d.stops.flatMap((stop) => storiesForStop(race, d, stop)))
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value))
    .slice(0, limit)
}
