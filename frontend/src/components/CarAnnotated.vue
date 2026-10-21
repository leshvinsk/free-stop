<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { CarHotspot } from '@/data/teamInfo'
import { teamCar } from '@/utils/identity'

const props = defineProps<{
  teamName: string
  year: number
  hotspots: CarHotspot[]
  colour: string
}>()

const carUrl = computed(() => teamCar(props.teamName, props.year))
const carFailed = ref(false)
watch(carUrl, () => (carFailed.value = false))
const active = ref<CarHotspot | null>(null)

function toggle(h: CarHotspot) {
  active.value = active.value?.id === h.id ? null : h
}
</script>

<template>
  <div class="annotated">
    <!-- Car canvas with hotspot overlays -->
    <div class="canvas" :style="{ '--team': colour }">
      <img
        v-if="carUrl && !carFailed"
        class="canvas__car"
        :src="carUrl"
        :alt="`${teamName} ${year} car`"
        decoding="async"
        @error="carFailed = true"
      />
      <div v-else class="canvas__fallback">Car image unavailable</div>

      <!-- Hotspot dots positioned as % over the image -->
      <button
        v-for="h in hotspots"
        :key="h.id"
        class="dot"
        :class="{ 'dot--active': active?.id === h.id }"
        :style="{ left: `${h.x}%`, top: `${h.y}%` }"
        :aria-label="h.label"
        :title="h.label"
        @click="toggle(h)"
      >
        <span class="dot__ring" />
      </button>
    </div>

    <!-- Detail panel for the selected hotspot -->
    <transition name="panel">
      <div v-if="active" class="panel" :style="{ '--team': colour }">
        <div class="panel__head">
          <span class="panel__label">{{ active.label }}</span>
          <button class="panel__close" aria-label="Close" @click="active = null">✕</button>
        </div>
        <div class="panel__body">
          <dl class="panel__specs">
            <div v-for="s in active.specs" :key="s.label" class="panel__row">
              <dt>{{ s.label }}</dt>
              <dd>{{ s.value }}</dd>
            </div>
          </dl>
          <p v-if="active.note" class="panel__note">{{ active.note }}</p>
        </div>
      </div>
    </transition>

    <!-- Legend chips for all hotspots -->
    <div class="legend">
      <button
        v-for="h in hotspots"
        :key="h.id"
        class="chip"
        :class="{ 'chip--active': active?.id === h.id }"
        @click="toggle(h)"
      >
        {{ h.label }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.annotated {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

/* ── Car canvas ─────────────────────────────────────────────────────────── */

.canvas {
  position: relative;
  /* Fixed aspect ratio so % hotspot positions are reliable */
  aspect-ratio: 4 / 1;
  background: radial-gradient(
    ellipse 70% 60% at 50% 70%,
    color-mix(in srgb, var(--team) 12%, transparent),
    transparent 80%
  );
  border-radius: var(--radius);
  overflow: visible;
}

.canvas__car {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  filter: drop-shadow(0 8px 18px rgba(0, 0, 0, 0.6));
  pointer-events: none;
}

.canvas__fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  font-size: 0.85rem;
  color: var(--text-muted);
}

/* ── Hotspot dots ────────────────────────────────────────────────────────── */

/* Always white/dark so dots are visible on any car colour (red, silver, etc.) */
.dot {
  position: absolute;
  width: 22px;
  height: 22px;
  padding: 0;
  background: rgba(0, 0, 0, 0.72);
  border: 2px solid #fff;
  border-radius: 50%;
  cursor: pointer;
  transform: translate(-50%, -50%);
  transition:
    background 0.2s,
    border-color 0.2s,
    transform 0.25s var(--ease-out);
  z-index: 2;
  box-shadow:
    0 0 0 1px rgba(0, 0, 0, 0.6),
    0 2px 6px rgba(0, 0, 0, 0.7);
}

.dot::after {
  content: '';
  position: absolute;
  inset: 4px;
  background: #fff;
  border-radius: 50%;
  opacity: 0.9;
  transition:
    opacity 0.2s,
    background 0.2s;
}

.dot__ring {
  position: absolute;
  inset: -5px;
  border: 1.5px solid rgba(255, 255, 255, 0.75);
  border-radius: 50%;
  opacity: 0;
  animation: pulse 2.5s ease-out infinite;
}

@keyframes pulse {
  0% {
    transform: scale(0.8);
    opacity: 0.7;
  }
  100% {
    transform: scale(1.9);
    opacity: 0;
  }
}

.dot:hover {
  transform: translate(-50%, -50%) scale(1.2);
  background: rgba(0, 0, 0, 0.85);
  border-color: var(--team);
}

.dot:hover::after {
  background: var(--team);
  opacity: 1;
}

.dot--active {
  background: rgba(0, 0, 0, 0.85);
  border-color: var(--team);
  transform: translate(-50%, -50%) scale(1.15);
}

.dot--active::after {
  background: var(--team);
  opacity: 1;
}

.dot--active .dot__ring {
  border-color: var(--team);
}

/* ── Detail panel ────────────────────────────────────────────────────────── */

.panel {
  background: var(--bg-elev);
  border: 1px solid var(--line-strong);
  border-left: 3px solid var(--team);
  border-radius: var(--radius);
  overflow: hidden;
}

.panel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.7rem 1rem;
  background: color-mix(in srgb, var(--team) 14%, transparent);
}

.panel__label {
  font-size: 0.85rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.panel__close {
  padding: 0.1rem 0.35rem;
  font-size: 0.75rem;
  color: var(--text-muted);
  background: none;
  border: none;
  cursor: pointer;
  border-radius: 4px;
  transition:
    color 0.15s,
    background 0.15s;
}

.panel__close:hover {
  color: var(--text);
  background: var(--bg-elev-2);
}

.panel__body {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 0.9rem 1.5rem;
  padding: 0.9rem 1rem;
}

.panel__specs {
  margin: 0;
  display: grid;
  gap: 0.3rem;
}

.panel__row {
  display: grid;
  grid-template-columns: 140px 1fr;
  gap: 0.5rem;
  align-items: baseline;
}

dt {
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--text-muted);
}

dd {
  margin: 0;
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text);
}

.panel__note {
  margin: 0;
  font-size: 0.78rem;
  line-height: 1.55;
  color: var(--text-muted);
  max-width: 340px;
  align-self: center;
}

/* ── Legend chips ────────────────────────────────────────────────────────── */

.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.chip {
  padding: 0.25rem 0.65rem;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-muted);
  background: var(--bg-elev);
  border: 1px solid var(--line);
  border-radius: 99px;
  cursor: pointer;
  transition:
    color 0.2s,
    background 0.2s,
    border-color 0.2s;
}

.chip:hover {
  color: var(--text);
  border-color: var(--team);
}

.chip--active {
  color: var(--text);
  background: color-mix(in srgb, var(--team) 18%, transparent);
  border-color: var(--team);
}

/* ── Panel transition ────────────────────────────────────────────────────── */

.panel-enter-active,
.panel-leave-active {
  transition:
    opacity 0.2s,
    transform 0.25s var(--ease-out);
}

.panel-enter-from,
.panel-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

/* ── Mobile ──────────────────────────────────────────────────────────────── */

@media (max-width: 600px) {
  .canvas {
    aspect-ratio: 3 / 1;
  }

  .dot {
    width: 18px;
    height: 18px;
  }

  .panel__body {
    grid-template-columns: 1fr;
  }
}
</style>
