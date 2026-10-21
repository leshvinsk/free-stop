<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { SeasonDriver } from '@/types/api'
import { formatLuck, luckClass, portraitUrl, splitName, teamColour } from '@/utils/format'
import { teamLogo } from '@/utils/identity'

const props = defineProps<{ driver: SeasonDriver; label: string; year: number }>()

const name = computed(() => splitName(props.driver.full_name))
const colour = computed(() => teamColour(props.driver.team_colour))
const portrait = computed(() => portraitUrl(props.driver.headshot_url))
const logo = computed(() => teamLogo(props.driver.team_name))

// "+3.0s" → "+3.0" and "s", so the unit can sit smaller beside the figure
const perRace = computed(() => {
  const text = formatLuck(props.driver.luck_per_race)
  return text.endsWith('s') ? { value: text.slice(0, -1), unit: 's' } : { value: text, unit: '' }
})

// Hide images F1's servers don't have; the number and team name remain
const portraitFailed = ref(false)
const logoFailed = ref(false)
watch(portrait, () => (portraitFailed.value = false))
watch(logo, () => (logoFailed.value = false))
</script>

<template>
  <RouterLink
    :to="{ name: 'driver', params: { driverNumber: driver.driver_number }, query: { year } }"
    class="highlight card"
    :style="{ '--team': colour }"
  >
    <span class="watermark num" aria-hidden="true">{{ driver.driver_number }}</span>
    <img
      v-if="portrait && !portraitFailed"
      class="portrait"
      :src="portrait"
      :alt="driver.full_name"
      loading="lazy"
      decoding="async"
      @error="portraitFailed = true"
    />
    <span class="tag">{{ label }}</span>
    <span class="name">
      <span class="first">{{ name.first }}</span>
      <span class="last">
        {{ name.last }}
        <img
          v-if="logo && !logoFailed"
          class="logo"
          :src="logo"
          :alt="driver.team_name"
          loading="lazy"
          @error="logoFailed = true"
        />
      </span>
    </span>
    <span class="team"><span class="chip" />{{ driver.team_name }}</span>
    <span class="luck num" :class="luckClass(driver.luck_per_race)">
      {{ perRace.value }}<span class="unit">{{ perRace.unit }}</span>
      <small class="per">saved per race</small>
    </span>
    <span class="races">
      {{ formatLuck(driver.season_luck) }} against the field over {{ driver.races_scored }} races
    </span>
  </RouterLink>
</template>

<style scoped>
.highlight {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  min-height: 230px;
  padding: 1.25rem 1.4rem;
  overflow: hidden;
  border-left: 4px solid var(--team);
  background:
    linear-gradient(120deg, color-mix(in srgb, var(--team) 28%, transparent) 0%, transparent 55%),
    var(--bg-elev);
  /* One curve and duration for every moving part, so the card moves as one piece */
  --hover-ease: cubic-bezier(0.22, 1, 0.36, 1);
  --hover-time: 0.55s;
  box-shadow: 0 0 0 -20px transparent;
  transition:
    transform var(--hover-time) var(--hover-ease),
    box-shadow var(--hover-time) var(--hover-ease);
  will-change: transform;
}

.highlight:hover {
  transform: translateY(-4px);
  box-shadow: 0 22px 44px -20px color-mix(in srgb, var(--team) 75%, transparent);
}

/* Car number in front of the portrait, like the official F1 driver cards */
.watermark {
  position: absolute;
  right: 1rem;
  bottom: -0.9rem;
  z-index: 2;
  font-family: var(--font-num);
  font-size: 6.5rem;
  font-weight: 800;
  font-style: italic;
  line-height: 1;
  color: color-mix(in srgb, var(--team) 85%, #fff);
  -webkit-text-stroke: 1px rgba(255, 255, 255, 0.35);
  text-shadow:
    0 4px 18px rgba(0, 0, 0, 0.85),
    0 0 28px color-mix(in srgb, var(--team) 45%, transparent);
  pointer-events: none;
  transition: transform var(--hover-time) var(--hover-ease);
  animation: number-in 0.8s var(--ease-out) 0.25s backwards;
}

@keyframes number-in {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
}

.highlight:hover .watermark {
  transform: translateX(-8px);
}

.portrait {
  position: absolute;
  right: 0;
  bottom: 0;
  height: 100%;
  max-width: 55%;
  object-fit: contain;
  object-position: right bottom;
  /* Fade the shoulders into the card, like the official F1 driver cards */
  mask-image: linear-gradient(to top, transparent 0%, #000 28%);
  pointer-events: none;
  transform-origin: bottom right;
  transition: transform var(--hover-time) var(--hover-ease);
  animation: portrait-in 0.8s var(--ease-out) backwards;
  will-change: transform;
}

@keyframes portrait-in {
  from {
    opacity: 0;
    transform: translateX(24px);
  }
}

.highlight:hover .portrait {
  transform: scale(1.03);
}

/* Text stays above the portrait */
.tag,
.name,
.team,
.luck,
.races {
  position: relative;
  z-index: 1;
}

.tag {
  align-self: flex-start;
  margin-bottom: 0.6rem;
}

.name {
  display: flex;
  flex-direction: column;
  line-height: 1;
}

.first {
  font-size: 1rem;
  color: var(--text-muted);
}

.last {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  max-width: 62%;
  font-size: clamp(1.6rem, 4vw, 2.1rem);
  font-weight: 900;
  text-transform: uppercase;
}

.team {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.85rem;
  color: var(--text-muted);
}

.chip {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  background: var(--team);
}

.luck {
  margin-top: auto;
  font-size: clamp(2rem, 5vw, 2.6rem);
  font-weight: 900;
  line-height: 1;
}

.unit {
  margin-left: 0.05em;
  font-size: 0.55em;
  font-weight: 700;
  text-transform: lowercase;
}

/* Team logo on the surname line, sized to the letters */
.logo {
  flex: none;
  width: 1.3em;
  height: 1.3em;
  object-fit: contain;
  filter: drop-shadow(0 4px 10px rgba(0, 0, 0, 0.55));
  animation: logo-in 0.8s var(--ease-out) 0.1s backwards;
}

@keyframes logo-in {
  from {
    opacity: 0;
    transform: scale(0.8);
  }
}

.per {
  margin-left: 0.4rem;
  font-family: var(--font);
  font-size: 0.85rem;
  font-weight: 700;
  font-style: normal;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-muted);
}

/* On narrow cards the label drops under the figure, clear of the car number */
@media (max-width: 1080px) {
  .per {
    display: block;
    margin: 0.4rem 0 0;
  }
}

.races {
  font-size: 0.8rem;
  color: var(--text-dim);
}
</style>
