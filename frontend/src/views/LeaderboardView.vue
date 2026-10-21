<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import DriverHighlight from '@/components/DriverHighlight.vue'
import RaceCalendar from '@/components/RaceCalendar.vue'
import RedFlag from '@/components/RedFlag.vue'
import ScoringProgress from '@/components/ScoringProgress.vue'
import SkeletonTower from '@/components/SkeletonTower.vue'
import StartLights from '@/components/StartLights.vue'
import TimingTower from '@/components/TimingTower.vue'
import YearSelector from '@/components/YearSelector.vue'
import { useApi } from '@/composables/useApi'
import type { RaceRef, SeasonSummary } from '@/types/api'
import type { TowerRow } from '@/types/ui'
import { nationality } from '@/utils/identity'
import { formatFullName, teamColour } from '@/utils/format'

const props = defineProps<{ year: number }>()
const router = useRouter()

const season = useApi<SeasonSummary>(() => `/api/season/${props.year}`, {
  pollWhile: (s) => !s.progress.complete,
})
const races = useApi<RaceRef[]>(() => `/api/season/${props.year}/races`)

const drivers = computed(() => season.data.value?.drivers ?? [])
const progress = computed(() => season.data.value?.progress)
const hasStandings = computed(() => drivers.value.length > 0)
// Headline cards only go to drivers with enough races, so a one-off stand-in can't top them
const regulars = computed(() => {
  const needed = season.data.value?.min_races ?? 1
  return drivers.value.filter((d) => d.races_scored >= needed)
})
const luckiest = computed(() => regulars.value[0])
const unluckiest = computed(() => (regulars.value.length > 1 ? regulars.value.at(-1) : undefined))

const rows = computed<TowerRow[]>(() =>
  drivers.value.map((d) => ({
    key: d.driver_number,
    code: d.name_acronym,
    title: formatFullName(d.full_name),
    subtitle: d.team_name,
    tag: `${d.races_scored} race${d.races_scored === 1 ? '' : 's'}`,
    colour: teamColour(d.team_colour),
    team: d.team_name,
    teamTo: { name: 'team', params: { teamKey: d.team_key }, query: { year: props.year } },
    number: d.driver_number,
    country: nationality(d.name_acronym),
    luck: d.luck_per_race,
    to: { name: 'driver', params: { driverNumber: d.driver_number }, query: { year: props.year } },
  })),
)

function selectYear(year: number): void {
  void router.replace({ query: year === new Date().getFullYear() ? {} : { year } })
}
</script>

<template>
  <div>
    <section class="hero rise">
      <div>
        <span class="tag">{{ year }} Season</span>
        <h1 class="display">Who got the<br /><em>free</em> stop?</h1>
        <p class="lede">
          A normal pit stop costs around 20 seconds. Box under a safety car and it's almost free.
          Here's who the timing helped this season, and who it left behind.
        </p>
      </div>
      <YearSelector :model-value="year" class="hero__years" @update:model-value="selectYear" />
    </section>

    <RedFlag
      v-if="season.error.value"
      :message="season.error.value"
      class="section"
      @retry="season.reload"
    />

    <template v-else>
      <section v-if="!hasStandings" class="section">
        <StartLights
          :label="progress ? 'Scoring the season' : 'Lights out in a moment'"
          :detail="progress ? 'The first results appear as soon as a race is analysed.' : ''"
        />
        <ScoringProgress v-if="progress && !progress.complete" :progress="progress" />
        <SkeletonTower :rows="8" />
      </section>

      <template v-else>
        <section class="section highlights">
          <DriverHighlight
            v-if="luckiest"
            :driver="luckiest"
            label="Luckiest"
            :year="year"
            class="rise"
            style="--i: 1"
          />
          <DriverHighlight
            v-if="unluckiest"
            :driver="unluckiest"
            label="Unluckiest"
            :year="year"
            class="rise"
            style="--i: 2"
          />
        </section>

        <section class="section rise" style="--i: 3">
          <h2 class="section__title">Luck standings</h2>
          <ScoringProgress v-if="progress && !progress.complete" :progress="progress" />
          <TimingTower :rows="rows" tag-label="Races" value-label="Saved per race" />
        </section>
      </template>

      <section v-if="races.data.value?.length" class="section">
        <h2 class="section__title">Race by race</h2>
        <RaceCalendar :races="races.data.value" />
      </section>
    </template>
  </div>
</template>

<style scoped>
.hero {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1.5rem 2rem;
}

.hero .tag {
  margin-bottom: 1rem;
}

.highlights {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 320px), 1fr));
  gap: 1rem;
}
</style>
