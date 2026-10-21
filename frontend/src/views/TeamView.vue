<script setup lang="ts">
import { computed, ref, watch, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import CarAnnotated from '@/components/CarAnnotated.vue'
import DriverHighlight from '@/components/DriverHighlight.vue'
import DriverSeasonChart from '@/components/DriverSeasonChart.vue'
import RedFlag from '@/components/RedFlag.vue'
import SkeletonTower from '@/components/SkeletonTower.vue'
import StartLights from '@/components/StartLights.vue'
import StatTile from '@/components/StatTile.vue'
import TimingTower from '@/components/TimingTower.vue'
import YearSelector from '@/components/YearSelector.vue'
import { useApi } from '@/composables/useApi'
import type { TeamSummary } from '@/types/api'
import type { TowerRow } from '@/types/ui'
import { getCarHotspots, getTeamInfo } from '@/data/teamInfo'
import { formatDate, formatLuck, luckClass, teamColour } from '@/utils/format'
import { teamCar, teamLogo } from '@/utils/identity'

const props = defineProps<{ teamKey: string; year: number }>()
const router = useRouter()

const {
  data: team,
  loading,
  error,
  reload,
} = useApi<TeamSummary>(() => `/api/team/${props.teamKey}?year=${props.year}`, {
  pollWhile: (t) => !t.progress.complete,
})

const colour = computed(() => teamColour(team.value?.team_colour))
const logo = computed(() => (team.value ? teamLogo(team.value.name) : null))
const car = computed(() => (team.value ? teamCar(team.value.name, props.year) : null))
const logoFailed = ref(false)
const carFailed = ref(false)
const carLoaded = ref(false)
const heroTimedOut = ref(false)
let heroTimer: ReturnType<typeof setTimeout> | undefined

watch(logo, () => (logoFailed.value = false))
watch(car, () => {
  carFailed.value = false
  carLoaded.value = false
  heroTimedOut.value = false
  clearTimeout(heroTimer)
  // Pre-load the car so it's ready when the hero renders
  if (car.value) {
    const img = new Image()
    img.onload = () => (carLoaded.value = true)
    img.onerror = () => (carLoaded.value = true) // show hero even if car fails
    img.src = car.value
    // Fallback: reveal after 1.8s regardless
    heroTimer = setTimeout(() => (heroTimedOut.value = true), 1800)
  } else {
    carLoaded.value = true
  }
})
onBeforeUnmount(() => clearTimeout(heroTimer))

// Hero is ready once car is preloaded (or timed out)
const heroReady = computed(() => carLoaded.value || heroTimedOut.value)

const seasonYears = computed(() => team.value?.seasons.map((s) => s.year) ?? [props.year])

const teamInfo = computed(() => getTeamInfo(props.teamKey))

// Seasons without an entry show the latest known leadership
const leadershipYear = computed(() => {
  const principal = teamInfo.value?.principal ?? {}
  return principal[props.year] ? props.year : Math.max(...Object.keys(principal).map(Number))
})
const hotspots = getCarHotspots()

// Pit crew stats derived from race execution scores
const crewStats = computed(() => {
  const execs = (team.value?.races ?? [])
    .filter((r) => r.race_execution !== null)
    .map((r) => r.race_execution as number)
  if (!execs.length) return null
  const avg = execs.reduce((a, b) => a + b, 0) / execs.length
  const best = Math.max(...execs)
  const worst = Math.min(...execs)
  const consistent = execs.filter((e) => Math.abs(e) < 1.5).length
  return { avg, best, worst, consistent, total: execs.length }
})

function versusNormal(delta: number): string {
  if (delta > 0) return 'faster than normal'
  if (delta < 0) return 'slower than normal'
  return 'same as normal'
}

// Earlier and later names, e.g. Racing Bulls was RB
const otherNames = computed(() => {
  const seen = new Set<string>([team.value?.name ?? ''])
  return (team.value?.seasons ?? []).filter((s) => !seen.has(s.name) && seen.add(s.name))
})

function selectYear(year: number): void {
  void router.replace({ query: { year } })
}

const raceRows = computed<TowerRow[]>(() =>
  (team.value?.races ?? []).map((r) => ({
    key: r.session_key,
    code: `R${String(r.round).padStart(2, '0')}`,
    title: r.race_name,
    subtitle: formatDate(r.date),
    tag: r.drivers
      .map((d) => `${d.name_acronym} ${d.outcome ?? formatLuck(d.race_luck)}`)
      .join('\n'),
    colour: colour.value,
    team: team.value?.name,
    luck: r.race_luck,
    note: r.no_stops ? 'No stops' : r.race_luck === null ? 'N/A' : undefined,
    to: { name: 'race', params: { sessionKey: r.session_key } },
  })),
)

const standingRows = computed<TowerRow[]>(() =>
  (team.value?.standings ?? []).map((t) => ({
    key: t.key,
    code: '',
    title: t.name,
    highlight: t.key === props.teamKey,
    tag: `${t.races_scored} race${t.races_scored === 1 ? '' : 's'}`,
    colour: teamColour(t.team_colour),
    team: t.name,
    luck: t.luck_per_race,
    to: { name: 'team', params: { teamKey: t.key }, query: { year: props.year } },
  })),
)
</script>

<template>
  <div>
    <button type="button" class="back-link" @click="router.back()">← Back</button>

    <RedFlag v-if="error" :message="error" @retry="reload" />

    <template v-else-if="loading || !team || !heroReady">
      <StartLights label="Loading team" />
      <SkeletonTower :rows="8" />
    </template>

    <Transition name="content" appear>
      <div v-if="!loading && team && heroReady" class="page-content">
        <section class="hero rise" :style="{ '--i': 0, '--team': colour }">
          <img
            v-if="car && !carFailed"
            class="hero__car"
            :src="car"
            :alt="`${team.name} ${year} car`"
            decoding="async"
            @error="carFailed = true"
          />
          <div class="hero__text">
            <span class="tag">{{ year }} Season</span>
            <h1 class="hero__name">
              <img
                v-if="logo && !logoFailed"
                class="hero__logo"
                :src="logo"
                alt=""
                @error="logoFailed = true"
              />
              {{ team.name }}
            </h1>
            <p v-if="otherNames.length" class="hero__history">
              Also raced as
              <template v-for="(s, i) in otherNames" :key="s.year">
                <RouterLink :to="{ name: 'team', params: { teamKey }, query: { year: s.year } }">
                  {{ s.name }} ({{ s.year }})</RouterLink
                ><template v-if="i < otherNames.length - 1">, </template>
              </template>
            </p>
            <YearSelector
              class="hero__years"
              :model-value="year"
              :options="seasonYears"
              @update:model-value="selectYear"
            />
          </div>
        </section>

        <!-- Team info strip -->
        <div
          v-if="teamInfo"
          class="info-strip rise"
          style="--i: 1; margin-top: clamp(1.5rem, 3vw, 2rem)"
        >
          <div class="info-strip__item">
            <span class="info-strip__label">Team Principal</span>
            <span class="info-strip__value">{{ teamInfo.principal[leadershipYear] ?? '—' }}</span>
            <span v-if="teamInfo.principalNote?.[leadershipYear]" class="info-strip__note">{{
              teamInfo.principalNote[leadershipYear]
            }}</span>
          </div>
          <div class="info-strip__item">
            <span class="info-strip__label">Base</span>
            <span class="info-strip__value">{{ teamInfo.base }}</span>
          </div>
          <div class="info-strip__item">
            <span class="info-strip__label">Founded</span>
            <span class="info-strip__value">{{ teamInfo.founded }}</span>
          </div>
          <div class="info-strip__item">
            <span class="info-strip__label">Chassis</span>
            <span class="info-strip__value">{{
              teamInfo.chassis[year] ??
              teamInfo.chassis[Math.max(...Object.keys(teamInfo.chassis).map(Number))] ??
              '—'
            }}</span>
          </div>
          <div class="info-strip__item">
            <span class="info-strip__label">Power Unit</span>
            <span class="info-strip__value">{{
              teamInfo.powerUnit[year] ??
              teamInfo.powerUnit[Math.max(...Object.keys(teamInfo.powerUnit).map(Number))] ??
              '—'
            }}</span>
          </div>
        </div>

        <section class="section tiles rise" style="--i: 2">
          <StatTile
            label="Saved per race"
            :value="formatLuck(team.luck_per_race)"
            :tone="luckClass(team.luck_per_race)"
            :hint="`${formatLuck(team.season_luck)} against the field this season`"
          />
          <StatTile
            label="Team ranking"
            :value="team.rank ? `P${team.rank}` : '—'"
            :hint="`for time saved, of ${team.teams_count} teams`"
          />
          <StatTile
            label="Crew saved"
            :value="formatLuck(team.season_execution)"
            :tone="luckClass(team.season_execution)"
            hint="In the pit lane vs normal stops, this season"
          />
          <StatTile
            label="Pit stops"
            :value="String(team.pit_stops)"
            :hint="`over ${team.races.length} races`"
          />
        </section>

        <section v-if="team.drivers.length" class="section rise" style="--i: 3">
          <h2 class="section__title">Drivers</h2>
          <div class="drivers">
            <DriverHighlight
              v-for="d in team.drivers"
              :key="d.driver_number"
              :driver="d"
              :label="`${d.races_scored} race${d.races_scored === 1 ? '' : 's'}`"
              :year="year"
            />
          </div>
        </section>

        <section v-if="team.races.length" class="section rise" style="--i: 4">
          <h2 class="section__title">Season progression</h2>
          <div class="card chart">
            <DriverSeasonChart :races="team.races" />
          </div>
        </section>

        <!-- Interactive car section -->
        <section id="car" class="section rise" style="--i: 5">
          <h2 class="section__title">The car</h2>
          <div class="card car-card">
            <div class="car-card__head">
              <div>
                <span class="car-card__model num">
                  {{ teamInfo?.chassis[year] ?? team.name }}
                </span>
                <span class="car-card__pu">
                  {{ teamInfo?.powerUnit[year] ?? 'Power unit' }}
                </span>
              </div>
              <span class="car-card__hint">Click any dot to see component specs</span>
            </div>
            <CarAnnotated
              :team-name="team.name"
              :year="year"
              :hotspots="hotspots"
              :colour="colour"
            />
          </div>
        </section>

        <!-- Pit crew deep-dive -->
        <section v-if="crewStats" class="section rise" style="--i: 6">
          <h2 class="section__title">Pit crew performance</h2>
          <div class="crew-grid">
            <div class="card crew-stat">
              <span class="crew-stat__label">Crew saved per race</span>
              <span class="crew-stat__value num" :class="luckClass(crewStats.avg)">
                {{ formatLuck(crewStats.avg) }}
              </span>
              <span class="crew-stat__note">both cars combined, this season</span>
            </div>
            <div class="card crew-stat">
              <span class="crew-stat__label">Best race</span>
              <span class="crew-stat__value num" :class="luckClass(crewStats.best)">
                {{ formatLuck(crewStats.best) }}
              </span>
              <span class="crew-stat__note">{{ versusNormal(crewStats.best) }}</span>
            </div>
            <div class="card crew-stat">
              <span class="crew-stat__label">Worst race</span>
              <span class="crew-stat__value num" :class="luckClass(crewStats.worst)">
                {{ formatLuck(crewStats.worst) }}
              </span>
              <span class="crew-stat__note">{{ versusNormal(crewStats.worst) }}</span>
            </div>
            <div class="card crew-stat">
              <span class="crew-stat__label">Clean races</span>
              <span class="crew-stat__value num">
                {{ crewStats.consistent }}/{{ crewStats.total }}
              </span>
              <span class="crew-stat__note">within 1.5s of normal</span>
            </div>
          </div>
        </section>

        <section v-if="team.races.length" class="section rise" style="--i: 7">
          <h2 class="section__title">Race by race</h2>
          <TimingTower
            :rows="raceRows"
            :numbered="false"
            title-label="Grand Prix"
            tag-label="Drivers"
            value-label="Time saved"
          />
        </section>

        <section v-if="team.standings.length" class="section rise" style="--i: 8">
          <h2 class="section__title">Team standings</h2>
          <TimingTower
            :rows="standingRows"
            title-label="Team"
            tag-label="Races"
            value-label="Saved per race"
          />
        </section>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
/* Page content fades in as a unit so rise animations start from invisible, not from a flash */
.content-enter-active {
  transition: opacity 0.12s ease;
}
.content-enter-from {
  opacity: 0;
}

.page-content {
  /* needed so Transition wraps a single element */
}

.hero {
  position: relative;
  isolation: isolate;
  overflow: hidden;
  min-height: clamp(220px, 28vw, 300px);
  padding: clamp(1.5rem, 4vw, 2.5rem) clamp(1rem, 3vw, 1.75rem) 1.5rem;
  border-left: 5px solid var(--team);
  background: linear-gradient(
    110deg,
    color-mix(in srgb, var(--team) 22%, transparent) 0%,
    transparent 60%
  );
}

.hero__text {
  position: relative;
  z-index: 1;
  max-width: 60%;
}

.hero .tag {
  margin-bottom: 1rem;
}

.hero__name {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin: 0;
  font-size: clamp(2.2rem, 7vw, 4.5rem);
  font-weight: 900;
  line-height: 1;
  text-transform: uppercase;
}

.hero__logo {
  flex: none;
  width: 1.1em;
  height: 1.1em;
  object-fit: contain;
  filter: drop-shadow(0 6px 14px rgba(0, 0, 0, 0.55));
}

.hero__history {
  margin: 0.9rem 0 0;
  font-size: 0.9rem;
  color: var(--text-muted);
}

.hero__history a {
  color: var(--text);
  text-decoration: underline;
  text-decoration-color: var(--team);
  text-underline-offset: 3px;
}

.hero__years {
  margin-top: 1.25rem;
}

.hero__car {
  position: absolute;
  right: clamp(-2rem, -2vw, 0rem);
  bottom: 1rem;
  z-index: 0;
  width: min(48%, 620px);
  filter: drop-shadow(0 16px 20px rgba(0, 0, 0, 0.7));
  animation: car-in 1.2s var(--ease-out) both;
  pointer-events: none;
}

@keyframes car-in {
  from {
    transform: translateX(-130vw);
  }
}

.tiles {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr));
  gap: 0.75rem;
}

/* ── Team info strip ─────────────────────────────────────────────────────── */

.info-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 0;
  background: var(--bg-elev);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  overflow: hidden;
}

.info-strip__item {
  flex: 1 1 140px;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  padding: 0.75rem 1.1rem;
  border-right: 1px solid var(--line);
}

.info-strip__item:last-child {
  border-right: none;
}

.info-strip__label {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.info-strip__value {
  font-size: 0.88rem;
  font-weight: 700;
  color: var(--text);
  line-height: 1.3;
}

.info-strip__note {
  font-size: 0.72rem;
  line-height: 1.35;
  color: var(--text-muted);
}

/* ── Car card ────────────────────────────────────────────────────────────── */

.car-card {
  padding: 1.1rem 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.car-card__head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

.car-card__model {
  display: block;
  font-size: 1.6rem;
  font-weight: 900;
  letter-spacing: -0.01em;
  text-transform: uppercase;
  color: var(--text);
}

.car-card__pu {
  display: block;
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--text-muted);
  margin-top: 0.1rem;
}

.car-card__hint {
  font-size: 0.72rem;
  color: var(--text-muted);
  font-style: italic;
}

/* ── Pit crew grid ───────────────────────────────────────────────────────── */

.crew-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 200px), 1fr));
  gap: 0.75rem;
}

.crew-stat {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  padding: 1rem 1.2rem;
}

.crew-stat__label {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.crew-stat__value {
  font-size: 2rem;
  font-weight: 900;
  line-height: 1.1;
}

.crew-stat__note {
  font-size: 0.75rem;
  color: var(--text-muted);
}

/* ── Drivers / charts ────────────────────────────────────────────────────── */

.drivers {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 420px), 1fr));
  gap: 0.75rem;
}

.chart {
  padding: 1rem 1rem 0.25rem;
}

@media (max-width: 760px) {
  .hero__text {
    max-width: none;
  }

  .hero__car {
    position: relative;
    right: auto;
    bottom: auto;
    display: block;
    width: min(100%, 420px);
    margin-top: 1.25rem;
    /* On mobile the car is in-flow; use a short fade-up instead of the full-width slide */
    animation-name: car-in-mobile;
  }

  @keyframes car-in-mobile {
    from {
      opacity: 0;
      transform: translateY(20px);
    }
  }
}
</style>
