<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import DriverSeasonChart from '@/components/DriverSeasonChart.vue'
import RedFlag from '@/components/RedFlag.vue'
import ScoringProgress from '@/components/ScoringProgress.vue'
import SkeletonTower from '@/components/SkeletonTower.vue'
import StartLights from '@/components/StartLights.vue'
import StatTile from '@/components/StatTile.vue'
import TimingTower from '@/components/TimingTower.vue'
import { useApi } from '@/composables/useApi'
import type { DriverRaceResult, DriverSummary } from '@/types/api'
import type { TowerRow } from '@/types/ui'
import {
  formatDate,
  formatLuck,
  luckClass,
  portraitUrl,
  splitName,
  teamColour,
} from '@/utils/format'
import { countryName, flagUrl, nationality, teamCar, teamLogo } from '@/utils/identity'

const props = defineProps<{ driverNumber: number; year: number }>()
const router = useRouter()

const {
  data: driver,
  loading,
  error,
  reload,
} = useApi<DriverSummary>(() => `/api/driver/${props.driverNumber}?year=${props.year}`, {
  pollWhile: (d) => !d.progress.complete,
})

const colour = computed(() => teamColour(driver.value?.team_colour))
const name = computed(() => splitName(driver.value?.full_name ?? ''))
const portrait = computed(() => portraitUrl(driver.value?.headshot_url))
const country = computed(() => (driver.value ? nationality(driver.value.name_acronym) : null))
const logo = computed(() => (driver.value ? teamLogo(driver.value.team_name) : null))
const car = computed(() => (driver.value ? teamCar(driver.value.team_name, props.year) : null))

// Hide images F1's servers don't have; the number watermark and colour chip remain
const portraitFailed = ref(false)
const logoFailed = ref(false)
const carFailed = ref(false)
watch(portrait, () => (portraitFailed.value = false))
watch(logo, () => (logoFailed.value = false))
watch(car, () => (carFailed.value = false))

// The header holds back until the car and portrait have loaded, so car, driver and name
// arrive together. A slow image can't block it for long.
const REVEAL_TIMEOUT_MS = 1800
const carLoaded = ref(false)
const portraitLoaded = ref(false)
const revealTimedOut = ref(false)
let revealTimer: ReturnType<typeof setTimeout> | undefined
watch(
  [car, portrait],
  () => {
    carLoaded.value = false
    portraitLoaded.value = false
    revealTimedOut.value = false
    clearTimeout(revealTimer)
    revealTimer = setTimeout(() => (revealTimedOut.value = true), REVEAL_TIMEOUT_MS)
  },
  { immediate: true },
)
onBeforeUnmount(() => clearTimeout(revealTimer))
const heroReady = computed(() => {
  const carDone = !car.value || carFailed.value || carLoaded.value
  const portraitDone = !portrait.value || portraitFailed.value || portraitLoaded.value
  return revealTimedOut.value || (carDone && portraitDone)
})
const scored = computed(() => driver.value?.races.filter((r) => r.race_luck !== null) ?? [])

function extreme(pick: (a: number, b: number) => boolean): DriverRaceResult | undefined {
  return scored.value.reduce<DriverRaceResult | undefined>(
    (best, r) => (!best || pick(r.race_luck ?? 0, best.race_luck ?? 0) ? r : best),
    undefined,
  )
}

const best = computed(() => extreme((a, b) => a > b))
const worst = computed(() => extreme((a, b) => a < b))

const rows = computed<TowerRow[]>(() =>
  (driver.value?.races ?? []).map((r) => ({
    key: r.session_key,
    code: `R${String(r.round).padStart(2, '0')}`,
    title: r.race_name,
    subtitle: `${r.circuit} · ${formatDate(r.date)}`,
    // No crew time to judge after a retirement, or when the only stops were made under a red flag
    tag: r.outcome || r.race_execution === null ? '—' : formatLuck(r.race_execution),
    colour: colour.value,
    team: driver.value?.team_name,
    teamTo: driver.value
      ? { name: 'team', params: { teamKey: driver.value.team_key }, query: { year: props.year } }
      : undefined,
    luck: r.race_luck,
    note: r.outcome ?? (r.no_stops ? 'No stops' : r.race_luck === null ? 'N/A' : undefined),
    barNote: r.outcome ? 'N/A' : undefined,
    to: { name: 'race', params: { sessionKey: r.session_key } },
  })),
)
</script>

<template>
  <div>
    <button type="button" class="back-link" @click="router.back()">← Back</button>

    <RedFlag v-if="error" :message="error" @retry="reload" />

    <template v-else-if="loading || !driver">
      <StartLights label="Loading driver" />
      <SkeletonTower :rows="8" />
    </template>

    <template v-else>
      <section class="hero" :class="{ 'hero--ready': heroReady }" :style="{ '--team': colour }">
        <span class="hero__number num" aria-hidden="true">{{ driver.driver_number }}</span>
        <img
          v-if="portrait && !portraitFailed"
          class="hero__portrait"
          :src="portrait"
          :alt="driver.full_name"
          decoding="async"
          fetchpriority="high"
          @load="portraitLoaded = true"
          @error="portraitFailed = true"
        />
        <div class="hero__text">
          <span class="tag">{{ year }} Season</span>
          <h1 class="hero__name">
            <span class="hero__first">{{ name.first }}</span>
            <span class="hero__last">{{ name.last }}</span>
          </h1>
          <p class="hero__team">
            <RouterLink
              class="hero__team-link"
              :to="{ name: 'team', params: { teamKey: driver.team_key }, query: { year } }"
              :title="`${driver.team_name} — team page`"
            >
              <img
                v-if="logo && !logoFailed"
                class="hero__logo"
                :src="logo"
                alt=""
                @error="logoFailed = true"
              />
              <span v-else class="chip" />
              {{ driver.team_name }}
            </RouterLink>
            <template v-if="country">
              <span class="hero__sep" aria-hidden="true">/</span>
              <img class="hero__flag" :src="flagUrl(country)" alt="" />
              {{ countryName(country) }}
            </template>
          </p>
        </div>
        <RouterLink
          v-if="car && !carFailed"
          class="hero__car-link"
          :to="{
            name: 'team',
            params: { teamKey: driver.team_key },
            query: { year },
            hash: '#car',
          }"
          :title="`${driver.team_name} — car specs`"
        >
          <img
            class="hero__car"
            :src="car"
            :alt="`${driver.team_name} ${year} car`"
            decoding="async"
            fetchpriority="high"
            @load="carLoaded = true"
            @error="carFailed = true"
          />
          <span class="hero__car-badge">View car specs →</span>
        </RouterLink>
      </section>

      <!-- Everything below waits for the header, then rises in after it -->
      <div class="after-hero" :class="{ 'after-hero--waiting': !heroReady }">
        <section class="section tiles">
          <StatTile
            class="rise"
            style="--i: 1"
            label="Saved per race"
            :value="formatLuck(driver.luck_per_race)"
            :tone="luckClass(driver.luck_per_race)"
            :hint="`${formatLuck(driver.season_luck)} against the field over ${driver.races_scored} races`"
          />
          <StatTile
            class="rise"
            style="--i: 2"
            label="Luckiest race"
            :value="best ? formatLuck(best.race_luck) : '—'"
            :tone="luckClass(best?.race_luck ?? null)"
            :hint="best?.race_name ?? ''"
          />
          <StatTile
            class="rise"
            style="--i: 3"
            label="Unluckiest race"
            :value="worst ? formatLuck(worst.race_luck) : '—'"
            :tone="luckClass(worst?.race_luck ?? null)"
            :hint="worst?.race_name ?? ''"
          />
          <StatTile
            class="rise"
            style="--i: 4"
            label="Crew saved"
            :value="formatLuck(driver.season_execution)"
            :tone="luckClass(driver.season_execution)"
            hint="In the pit lane vs normal stops, this season"
          />
        </section>

        <ScoringProgress
          v-if="!driver.progress.complete"
          :progress="driver.progress"
          class="section"
        />

        <section v-if="driver.races.length" class="section rise" style="--i: 4">
          <h2 class="section__title">Season progression</h2>
          <div class="card chart">
            <DriverSeasonChart :races="driver.races" />
          </div>
        </section>

        <section class="section rise" style="--i: 5">
          <h2 class="section__title">Race by race</h2>
          <TimingTower
            :rows="rows"
            :numbered="false"
            title-label="Grand Prix"
            tag-label="Crew saved"
            value-label="Time saved"
          />
        </section>
      </div>
    </template>
  </div>
</template>

<style scoped>
.hero {
  position: relative;
  isolation: isolate;
  overflow: hidden;
  min-height: clamp(220px, 30vw, 300px);
  padding: clamp(1.5rem, 4vw, 2.5rem) 0 1.25rem;
  border-left: 5px solid var(--team);
  padding-left: clamp(1rem, 3vw, 1.75rem);
}

/* Car number in front of the portrait, styled like the home page cards */
.hero__number {
  position: absolute;
  right: clamp(0.5rem, 4vw, 3rem);
  bottom: -1rem;
  z-index: 1;
  font-family: var(--font-num);
  font-size: clamp(4.5rem, 11vw, 7.5rem);
  font-weight: 800;
  font-style: italic;
  line-height: 1;
  color: color-mix(in srgb, var(--team) 85%, #fff);
  -webkit-text-stroke: 1px rgba(255, 255, 255, 0.35);
  text-shadow:
    0 4px 18px rgba(0, 0, 0, 0.85),
    0 0 28px color-mix(in srgb, var(--team) 45%, transparent);
  pointer-events: none;
}

/* The team's car, in front of everything, between the name and the portrait */
.hero__car-link {
  position: absolute;
  left: 34%;
  bottom: 1.25rem;
  z-index: 2;
  width: min(36%, 460px);
  display: block;
  text-decoration: none;
}

.hero__car {
  display: block;
  width: 100%;
  height: auto;
  filter: drop-shadow(0 14px 18px rgba(0, 0, 0, 0.7));
  transition:
    filter 0.3s,
    transform 0.35s var(--ease-out);
}

.hero__car-link:hover .hero__car,
.hero__car-link:focus-visible .hero__car {
  filter: drop-shadow(0 18px 28px rgba(0, 0, 0, 0.8)) brightness(1.1);
  transform: translateY(-5px);
}

/* Suppress the browser focus ring — we handle focus with the car glow instead */
.hero__car-link:focus-visible {
  outline: 0 !important;
}

.hero__car-badge {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%) scale(0.9);
  padding: 0.3rem 0.9rem;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #fff;
  background: rgba(0, 0, 0, 0.72);
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: 99px;
  white-space: nowrap;
  pointer-events: none;
  opacity: 0;
  transition:
    opacity 0.2s,
    transform 0.25s var(--ease-out),
    border-color 0.2s,
    background 0.2s;
  backdrop-filter: blur(4px);
}

.hero__car-link:hover .hero__car-badge,
.hero__car-link:focus-visible .hero__car-badge {
  opacity: 1;
  transform: translate(-50%, -50%) scale(1);
  border-color: var(--team);
  background: color-mix(in srgb, var(--team) 50%, rgba(0, 0, 0, 0.6));
}

/* Nothing shows until the images are in; then everything arrives at once */
.hero__text,
.hero__car-link,
.hero__car,
.hero__portrait,
.hero__number {
  opacity: 0;
}

/* The car drives in from the left and the name follows close behind, as if towed */
.hero--ready .hero__car-link,
.hero--ready .hero__car {
  animation: car-in 1.2s var(--ease-out) both;
}

.hero--ready .hero__text {
  animation: towed-in 1.2s var(--ease-out) 0.12s both;
}

.hero--ready .hero__portrait {
  animation: portrait-in 1s var(--ease-out) 0.1s both;
}

.hero--ready .hero__number {
  animation: number-in 0.9s var(--ease-out) 0.35s both;
}

@keyframes car-in {
  from {
    opacity: 1;
    transform: translateX(-130vw);
  }
  to {
    opacity: 1;
  }
}

@keyframes towed-in {
  from {
    opacity: 0;
    transform: translateX(-90px);
  }
  to {
    opacity: 1;
  }
}

@media (prefers-reduced-motion: reduce) {
  .hero--ready .hero__text,
  .hero--ready .hero__car,
  .hero--ready .hero__portrait,
  .hero--ready .hero__number {
    animation: none;
    opacity: 1;
  }
}

@keyframes number-in {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
  }
}

/* Portrait in front of the car, fading out at the shoulders */
.hero__portrait {
  position: absolute;
  right: clamp(0rem, 6vw, 4rem);
  bottom: 0;
  z-index: -1;
  height: 115%;
  max-width: 45%;
  object-fit: contain;
  object-position: right bottom;
  mask-image: linear-gradient(to top, transparent 0%, #000 30%);
  pointer-events: none;
}

@keyframes portrait-in {
  from {
    opacity: 0;
    transform: translateX(40px);
  }
  to {
    opacity: 1;
  }
}

@keyframes portrait-in-dim {
  from {
    opacity: 0;
    transform: translateX(40px);
  }
  to {
    opacity: 0.45;
  }
}

/* Narrow screens: no room beside the name, so the car drives in underneath it */
@media (max-width: 760px) {
  .hero__car-link {
    position: relative;
    left: auto;
    bottom: auto;
    display: block;
    width: min(100%, 380px);
    margin-top: 1.25rem;
  }
}

@media (max-width: 560px) {
  .hero__portrait {
    right: -1rem;
    max-width: 60%;
  }

  .hero--ready .hero__portrait {
    animation-name: portrait-in-dim;
  }

  .hero__car-link {
    width: 62%;
  }
}

.hero__team-link {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  color: inherit;
  transition: color 0.2s;
}

/* Same red underline as the navigation */
.hero__team-link::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: -4px;
  height: 2px;
  background: var(--team);
  transform: scaleX(0);
  transform-origin: left;
  transition: transform 0.35s var(--ease-out);
}

.hero__team-link:hover {
  color: var(--text);
}

.hero__team-link:hover::after {
  transform: scaleX(1);
}

.hero__logo {
  width: 20px;
  height: 20px;
  object-fit: contain;
}

.hero__sep {
  color: var(--f1-red);
}

.hero__flag {
  width: 20px;
  height: 14px;
  border-radius: 2px;
  object-fit: cover;
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.12);
}

.hero__text {
  position: relative;
  z-index: 1;
}

.hero .tag {
  margin-bottom: 1rem;
}

.hero__name {
  display: flex;
  flex-direction: column;
  margin: 0;
  line-height: 0.95;
}

.hero__first {
  font-size: clamp(1.3rem, 3.5vw, 2rem);
  font-weight: 400;
  color: var(--text-muted);
}

.hero__last {
  font-size: clamp(2.6rem, 9vw, 5.5rem);
  font-weight: 900;
  text-transform: uppercase;
  letter-spacing: -0.01em;
}

.hero__team {
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  margin: 1rem 0 0;
  font-size: 0.9rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.chip {
  width: 12px;
  height: 12px;
  border-radius: 2px;
  background: var(--team);
  box-shadow: 0 0 12px var(--team);
}

/* Held back (and its own entrance animations paused) until the header has arrived */
.after-hero {
  animation: after-hero-in 0.6s var(--ease-out) 0.45s both;
}

.after-hero--waiting {
  opacity: 0;
  animation: none;
}

.after-hero--waiting :deep(*) {
  animation-play-state: paused !important;
}

@keyframes after-hero-in {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
}

@media (prefers-reduced-motion: reduce) {
  .after-hero {
    animation: none;
  }
}

.tiles {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr));
  gap: 0.75rem;
}

.chart {
  padding: 1rem 1rem 0.25rem;
}
</style>
