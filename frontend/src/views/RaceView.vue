<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import CircuitMap from '@/components/CircuitMap.vue'
import RaceHighlights from '@/components/RaceHighlights.vue'
import RaceWeather from '@/components/RaceWeather.vue'
import RaceTimeline from '@/components/RaceTimeline.vue'
import RedFlag from '@/components/RedFlag.vue'
import SkeletonTower from '@/components/SkeletonTower.vue'
import StartLights from '@/components/StartLights.vue'
import StatTile from '@/components/StatTile.vue'
import TimingTower from '@/components/TimingTower.vue'
import { useApi } from '@/composables/useApi'
import type {
  CircuitMap as Circuit,
  FlagStatus,
  RaceDetail,
  RaceWeather as Weather,
} from '@/types/api'
import type { TowerRow } from '@/types/ui'
import { nationality } from '@/utils/identity'
import { formatDate, formatFullName, formatLuck, luckClass, teamColour } from '@/utils/format'
import { raceStories } from '@/utils/stories'

const props = defineProps<{ sessionKey: number }>()
const router = useRouter()

const {
  data: race,
  loading,
  error,
  reload,
} = useApi<RaceDetail>(() => `/api/race/${props.sessionKey}`)

// Trackside extras: requested alongside the race (the server starts them early too)
const circuit = useApi<Circuit>(() => `/api/race/${props.sessionKey}/circuit`)
const weather = useApi<Weather>(() => `/api/race/${props.sessionKey}/weather`)

// Page waits for ALL three: race, circuit, and weather. Once ready the whole page
// reveals in one go and the staggered rise animations play top-to-bottom.
const pageReady = computed(() => !!race.value && !circuit.loading.value && !weather.loading.value)

const title = computed(() => {
  const name = race.value?.race_name ?? ''
  const match = name.match(/^(.*?)\s*(Grand Prix)$/i)
  return match ? { main: match[1], suffix: match[2] } : { main: name, suffix: '' }
})

function count(type: FlagStatus): number {
  return race.value?.events.filter((e) => e.type === type).length ?? 0
}

const luckiest = computed(() =>
  race.value?.drivers.find((d) => d.race_luck !== null && d.race_luck > 0),
)

const year = computed(() => race.value?.date.slice(0, 4) ?? '')
const stories = computed(() => (race.value ? raceStories(race.value) : []))
const missedCount = computed(
  () =>
    race.value?.drivers.reduce((n, d) => n + d.stops.filter((s) => s.missed < 0).length, 0) ?? 0,
)

// One line per race state, e.g. "1 x SC" over "1 x GREEN", in the key's order
const CONDITIONS: [FlagStatus, string][] = [
  ['SC', 'SC'],
  ['VSC', 'VSC'],
  ['RED', 'RED'],
  ['GREEN', 'GREEN'],
]

function stopConditions(stops: { status: FlagStatus }[]): string {
  return CONDITIONS.map(
    ([status, label]) => [stops.filter((s) => s.status === status).length, label] as const,
  )
    .filter(([n]) => n > 0)
    .map(([n, label]) => `${n} x ${label}`)
    .join('\n')
}

const rows = computed<TowerRow[]>(() => {
  if (!race.value) return []
  return race.value.drivers.map((d) => ({
    key: d.driver_number,
    code: d.name_acronym,
    title: formatFullName(d.full_name),
    subtitle: d.team_name,
    tag: d.no_stops ? 'No stops' : stopConditions(d.stops),
    colour: teamColour(d.team_colour),
    team: d.team_name,
    teamTo: { name: 'team', params: { teamKey: d.team_key }, query: { year: year.value } },
    number: d.driver_number,
    country: nationality(d.name_acronym),
    luck: d.race_luck,
    note: d.outcome ?? (d.race_luck === null ? 'N/A' : undefined),
    barNote: d.outcome ? 'N/A' : undefined,
    to: {
      name: 'driver',
      params: { driverNumber: d.driver_number },
      query: { year: year.value },
    },
  }))
})

// Pit crews ranked by time won or lost in the pit lane against a normal stop
const crewRows = computed<TowerRow[]>(() =>
  (race.value?.drivers ?? [])
    .filter((d) => d.race_execution !== null)
    .sort((a, b) => (b.race_execution ?? 0) - (a.race_execution ?? 0))
    .map((d) => ({
      key: d.driver_number,
      code: d.name_acronym,
      title: d.team_name,
      subtitle: formatFullName(d.full_name),
      colour: teamColour(d.team_colour),
      team: d.team_name,
      teamTo: { name: 'team', params: { teamKey: d.team_key }, query: { year: year.value } },
      tag: d.stops.length
        ? `${Math.min(...d.stops.map((s) => s.pit_duration)).toFixed(3)}s`
        : undefined,
      luck: d.race_execution,
    })),
)
</script>

<template>
  <div>
    <button type="button" class="back-link" @click="router.back()">← Back</button>

    <RedFlag v-if="error" :message="error" @retry="reload" />

    <template v-else-if="loading || !race || !pageReady">
      <StartLights
        label="Analysing the race"
        detail="Pulling pit stops and race control messages."
      />
      <div class="tiles">
        <div v-for="n in 4" :key="n" class="tile-skeleton card" />
      </div>
      <SkeletonTower class="section" :rows="10" />
    </template>

    <Transition name="content" appear>
      <div v-if="!loading && race && pageReady" class="page-content">
        <section class="hero hero--split rise" style="--i: 0">
          <div class="hero__title">
            <span class="tag">{{ race.round ? `Round ${race.round}` : 'Grand Prix' }}</span>
            <h1 class="display">
              {{ title.main
              }}<template v-if="title.suffix"
                ><br /><em>{{ title.suffix }}</em></template
              >
            </h1>
            <p class="meta">
              <span>{{ race.circuit }}</span>
              <span>{{ formatDate(race.date) }}</span>
              <span v-if="race.total_laps">{{ race.total_laps }} laps</span>
            </p>

            <RaceHighlights :stories="stories" :year="year" />
          </div>

          <aside class="trackside card rise" style="--i: 1">
            <CircuitMap
              v-if="circuit.data.value"
              :circuit="circuit.data.value"
              :laps="race.total_laps"
            />
            <div class="trackside__divider" />
            <RaceWeather v-if="weather.data.value" :weather="weather.data.value" />
          </aside>
        </section>

        <section class="section tiles">
          <StatTile
            class="rise"
            style="--i: 2"
            label="Normal pit stop"
            :value="race.baseline_pit_loss ? `${race.baseline_pit_loss.toFixed(3)}s` : 'N/A'"
            :hint="
              race.insufficient_baseline_data
                ? 'Not enough data'
                : race.baseline_estimated
                  ? 'Estimated: no green-flag stops'
                  : `Lost to the field · ${race.typical_pit_lane?.toFixed(3)}s in the lane`
            "
          />
          <StatTile
            class="rise"
            style="--i: 3"
            label="Safety cars"
            :value="String(count('SC'))"
            :hint="`${count('VSC')} virtual · ${count('RED')} red flag${count('RED') === 1 ? '' : 's'}`"
            :tone="count('SC') ? 'flag-yellow' : ''"
          />
          <StatTile
            class="rise"
            style="--i: 3"
            label="Luckiest"
            :value="luckiest ? formatLuck(luckiest.race_luck) : '—'"
            :hint="luckiest ? formatFullName(luckiest.full_name) : 'Nobody saved time'"
            :tone="luckClass(luckiest?.race_luck ?? null)"
          />
          <StatTile
            class="rise"
            style="--i: 3"
            label="Missed out"
            :value="String(missedCount)"
            hint="Pitted just before a neutralisation"
            :tone="missedCount ? 'unlucky' : ''"
          />
        </section>

        <section class="section rise" style="--i: 4">
          <h2 class="section__title">Pit stop timeline</h2>
          <div class="card chart">
            <RaceTimeline :race="race" />
          </div>
        </section>

        <section class="section rise" style="--i: 5">
          <h2 class="section__title">Race luck</h2>
          <p v-if="race.field_average !== null" class="section__lede">
            Each stop is benchmarked against the {{ race.baseline_pit_loss?.toFixed(3) }}s
            green-flag baseline. Safety car stops cost near zero, so they score as big savings.
            Field average ({{ formatLuck(race.field_average) }} this race) is subtracted, so only
            relative luck counts.
          </p>
          <dl class="conditions" aria-label="What the stop conditions mean">
            <div>
              <dt><i class="key key--sc" />SC</dt>
              <dd>Safety car. The field slows right down, so a stop costs far less.</dd>
            </div>
            <div>
              <dt><i class="key key--vsc" />VSC</dt>
              <dd>
                Virtual safety car. Everyone slows to a set pace: cheaper, but less than a full SC.
              </dd>
            </div>
            <div>
              <dt><i class="key key--red" />RED FLAG</dt>
              <dd>Red flag. The race is stopped and everyone changes tyres for free.</dd>
            </div>
            <div>
              <dt><i class="key key--green" />GREEN</dt>
              <dd>Normal racing. The stop costs the full time.</dd>
            </div>
          </dl>
          <TimingTower :rows="rows" tag-label="Stop conditions" value-label="Time saved" />
        </section>

        <section v-if="crewRows.length" class="section rise" style="--i: 6">
          <h2 class="section__title">Pit crew execution</h2>
          <p class="section__lede">
            Time won or lost per driver against the race's normal stop. Penalties are excluded. Best
            stop shows the crew's fastest single pit lane time.
          </p>
          <TimingTower
            :rows="crewRows"
            title-label="Team"
            tag-label="Best stop"
            value-label="Crew saved"
            bar-label="Slower ← → Quicker"
          />
        </section>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
/* Page content fades in as a unit so rise animations start from invisible */
.content-enter-active {
  transition: opacity 0.12s ease;
}
.content-enter-from {
  opacity: 0;
}

/* Both columns share a height: title + highlights on the left, map + weather on the right */
.hero {
  display: grid;
  gap: 1.5rem;
  align-items: stretch;
}

.hero__title {
  display: flex;
  flex-direction: column;
}

.hero--split {
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
}

.trackside {
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  padding: 1rem 1.1rem 1.1rem;
  min-height: 0;
}

.trackside__divider {
  height: 1px;
  background: var(--line);
}

.trackside__divider:first-child,
.trackside__divider:last-child {
  display: none;
}

.trackside__loading {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 0.5rem;
}

.trackside__skel {
  flex: 1;
  border-radius: var(--radius);
  background: linear-gradient(90deg, var(--bg-elev-2) 25%, var(--line) 50%, var(--bg-elev-2) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.6s infinite;
  min-height: 140px;
}

.trackside__skel--sm {
  flex: 0 0 100px;
  min-height: unset;
}

@keyframes shimmer {
  from {
    background-position: 200% 0;
  }
  to {
    background-position: -200% 0;
  }
}

@media (max-width: 900px) {
  .hero--split {
    grid-template-columns: minmax(0, 1fr);
  }
}

.hero .tag {
  margin-bottom: 1rem;
}

.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.25rem 1.25rem;
  margin: 1rem 0 0;
  font-size: 0.85rem;
  font-weight: 600;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.meta span + span::before {
  content: '/';
  margin-right: 1.25rem;
  color: var(--f1-red);
}

.tiles {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 200px), 1fr));
  gap: 0.75rem;
}

.tile-skeleton {
  height: 104px;
  background: linear-gradient(90deg, var(--bg-elev) 0%, var(--bg-elev-2) 50%, var(--bg-elev) 100%);
  background-size: 300% 100%;
  animation: shimmer 1.4s ease-in-out infinite;
}

@keyframes shimmer {
  from {
    background-position: 100% 0;
  }
  to {
    background-position: -50% 0;
  }
}

.chart {
  padding: 1rem 1rem 0.25rem;
}

/* Key for the Stop conditions column, coloured like the timeline's zones */
.conditions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 200px), 1fr));
  gap: 0.5rem;
  margin: 0 0 0.9rem;
}

.conditions > div {
  padding: 0.6rem 0.8rem;
  background: var(--bg-elev);
  border: 1px solid var(--line);
  border-radius: var(--radius);
}

.conditions dt {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.92rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.conditions dd {
  margin: 0.25rem 0 0;
  font-size: 0.78rem;
  line-height: 1.45;
  color: var(--text-muted);
}

.key {
  flex: none;
  width: 12px;
  height: 12px;
  border-radius: 3px;
}

.key--sc {
  background: var(--yellow);
}

.key--vsc {
  border: 2px solid var(--yellow);
}

.key--red {
  background: var(--f1-red);
}

.key--green {
  background: var(--lucky);
}

.section__lede {
  max-width: 640px;
  margin: -0.5rem 0 1rem;
  font-size: 0.9rem;
  line-height: 1.6;
  color: var(--text-muted);
}

:deep(.flag-yellow) {
  color: var(--yellow);
}
</style>
