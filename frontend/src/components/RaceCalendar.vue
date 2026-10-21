<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { RaceRef } from '@/types/api'
import { formatDate } from '@/utils/format'
import { trackOutline } from '@/utils/identity'

const props = defineProps<{ races: RaceRef[] }>()

const strip = ref<HTMLElement | null>(null)
const atStart = ref(true)
const atEnd = ref(true)

/** "Chinese Grand Prix" → "Chinese GP" */
function shortName(name: string): string {
  return name.replace(/\s*Grand Prix$/i, ' GP')
}

// Outlines that fail to load are hidden rather than showing a broken image
const missingTracks = ref(new Set<string>())

function updateEdges(): void {
  const el = strip.value
  if (!el) return
  atStart.value = el.scrollLeft <= 2
  atEnd.value = el.scrollLeft + el.clientWidth >= el.scrollWidth - 2
}

function page(direction: 1 | -1): void {
  const el = strip.value
  if (!el) return
  el.scrollBy({ left: direction * el.clientWidth * 0.8, behavior: 'smooth' })
}

let resize: ResizeObserver | undefined
onMounted(() => {
  updateEdges()
  resize = new ResizeObserver(updateEdges)
  if (strip.value) resize.observe(strip.value)
})
onBeforeUnmount(() => resize?.disconnect())
watch(
  () => props.races.length,
  () => nextTick(updateEdges),
)
</script>

<template>
  <div class="calendar" :class="{ 'calendar--start': atStart, 'calendar--end': atEnd }">
    <button
      type="button"
      class="nav nav--prev"
      aria-label="Previous races"
      :disabled="atStart"
      @click="page(-1)"
    >
      <span aria-hidden="true">‹</span>
    </button>

    <div ref="strip" class="strip" role="list" @scroll.passive="updateEdges">
      <RouterLink
        v-for="(race, i) in races"
        :key="race.session_key"
        :to="{ name: 'race', params: { sessionKey: race.session_key } }"
        class="race card rise"
        role="listitem"
        :style="{ '--i': Math.min(i, 12) }"
      >
        <img
          v-if="!missingTracks.has(race.location)"
          class="track"
          :src="trackOutline(race.location)"
          alt=""
          loading="lazy"
          @error="missingTracks = new Set(missingTracks).add(race.location)"
        />
        <span class="round num">R{{ String(race.round).padStart(2, '0') }}</span>
        <span class="name">{{ shortName(race.race_name) }}</span>
        <span class="meta">{{ race.circuit }}</span>
        <span class="date">{{ formatDate(race.date) }}</span>
      </RouterLink>
    </div>

    <button
      type="button"
      class="nav nav--next"
      aria-label="Next races"
      :disabled="atEnd"
      @click="page(1)"
    >
      <span aria-hidden="true">›</span>
    </button>
  </div>
</template>

<style scoped>
.calendar {
  position: relative;
}

.strip {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(230px, 250px);
  gap: 0.75rem;
  /* Room inside the scroller so the hover lift and border aren't clipped */
  padding: 6px 2px 8px;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  scroll-padding-inline: 2px;
  overscroll-behavior-x: contain;
  /* Scrollable by touch, trackpad and keyboard, but no visible bar */
  scrollbar-width: none;
  /* Fade whichever edge has more races beyond it */
  --fade-start: 48px;
  --fade-end: 48px;
  mask-image: linear-gradient(
    90deg,
    transparent 0,
    #000 var(--fade-start),
    #000 calc(100% - var(--fade-end)),
    transparent 100%
  );
}

.strip::-webkit-scrollbar {
  display: none;
}

.calendar--start .strip {
  --fade-start: 0px;
}

.calendar--end .strip {
  --fade-end: 0px;
}

.nav {
  position: absolute;
  top: 50%;
  z-index: 2;
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  padding: 0;
  font-size: 1.6rem;
  line-height: 1;
  color: var(--text);
  background: var(--bg-elev-2);
  border: 1px solid var(--line-strong);
  border-radius: 50%;
  cursor: pointer;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.5);
  transform: translateY(-50%);
  transition:
    opacity 0.25s,
    background 0.2s,
    border-color 0.2s,
    transform 0.25s var(--ease-out);
}

.nav span {
  margin-top: -3px;
}

.nav--prev {
  left: -14px;
}

.nav--next {
  right: -14px;
}

.nav:hover:not(:disabled) {
  background: var(--f1-red);
  border-color: var(--f1-red);
  transform: translateY(-50%) scale(1.08);
}

.nav:focus-visible {
  outline: 2px solid var(--f1-red);
  outline-offset: 2px;
}

.nav:disabled {
  opacity: 0;
  pointer-events: none;
}

.race {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.9rem 1rem;
  scroll-snap-align: start;
  transition:
    border-color 0.2s,
    transform 0.3s var(--ease-out),
    background 0.2s;
}

.race:hover {
  border-color: var(--f1-red);
  transform: translateY(-3px);
  background: var(--bg-elev-2);
}

/* Circuit outline on the right of each card */
.track {
  position: absolute;
  top: 50%;
  right: 0.8rem;
  width: 74px;
  height: 58px;
  object-fit: contain;
  opacity: 0.55;
  transform: translateY(-50%);
  pointer-events: none;
  transition:
    opacity 0.3s,
    transform 0.4s var(--ease-out);
}

.race:hover .track {
  opacity: 1;
  transform: translateY(-50%) scale(1.06);
}

.round,
.name,
.meta {
  position: relative;
  max-width: calc(100% - 82px);
}

.round {
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: var(--f1-red);
}

.name {
  overflow: hidden;
  font-size: 1.05rem;
  font-weight: 700;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.meta,
.date {
  font-size: 0.78rem;
  color: var(--text-muted);
}

/* On touch screens swiping is natural; the buttons would just cover cards */
@media (hover: none) {
  .nav {
    display: none;
  }
}
</style>
