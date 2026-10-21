<script setup lang="ts">
import { computed } from 'vue'
import F1Car from '@/components/F1Car.vue'
import type { Progress } from '@/types/api'

const props = defineProps<{ progress: Progress }>()

const pct = computed(() =>
  props.progress.rounds_total
    ? (props.progress.rounds_scored / props.progress.rounds_total) * 100
    : 0,
)
</script>

<template>
  <div class="progress card" role="status" aria-live="polite">
    <div class="head">
      <span class="live"><span class="live__dot" />Live scoring</span>
      <span class="count num">
        Round <strong>{{ progress.rounds_scored }}</strong> / {{ progress.rounds_total }}
      </span>
    </div>
    <div
      class="track"
      role="progressbar"
      :aria-valuenow="progress.rounds_scored"
      :aria-valuemax="progress.rounds_total"
    >
      <div class="fill" :style="{ width: `${pct}%` }">
        <span class="car" aria-hidden="true">
          <span class="car__streaks" />
          <F1Car class="car__body" />
        </span>
      </div>
      <span class="flag chequered" />
    </div>
    <p class="hint">
      Standings update as each Grand Prix is analysed. Scored races are saved, so this only happens
      once.
    </p>
  </div>
</template>

<style scoped>
.progress {
  padding: 1rem 1.25rem 1.1rem;
  margin-bottom: 1.25rem;
}

.head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.live {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--f1-red);
}

.live__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--f1-red);
  animation: pulse 1.2s ease-in-out infinite;
}

@keyframes pulse {
  0%,
  100% {
    box-shadow: 0 0 0 0 var(--f1-red-glow);
  }
  60% {
    box-shadow: 0 0 0 7px rgba(225, 6, 0, 0);
    opacity: 0.5;
  }
}

.count {
  color: var(--text-muted);
}

.count strong {
  color: var(--text);
  font-size: 1rem;
}

.track {
  position: relative;
  height: 10px;
  margin: 1.1rem 0 0.9rem; /* the car is taller than the track */
  background: var(--bg-elev-2);
  border-radius: 2px;
}

.fill {
  position: relative;
  height: 100%;
  min-width: 68px; /* room for the car on the grid at round 0 */
  background:
    repeating-linear-gradient(-45deg, rgba(255, 255, 255, 0.18) 0 6px, transparent 6px 12px),
    linear-gradient(90deg, var(--f1-red-dark), var(--f1-red));
  background-size:
    34px 100%,
    100% 100%;
  animation: stripes 0.6s linear infinite;
  transition: width 0.8s var(--ease-out);
}

@keyframes stripes {
  to {
    background-position:
      34px 0,
      0 0;
  }
}

.car {
  position: absolute;
  right: 0;
  top: 50%;
  width: 66px;
  height: 24px;
  /* Nose sits on the leading edge of the fill */
  transform: translate(2px, -50%);
}

.car__body {
  position: relative;
  display: block;
  width: 100%;
  height: 100%;
  /* A thin light halo and a dark shadow lift the car off the red fill */
  filter: drop-shadow(0 0 1px rgba(255, 255, 255, 0.55)) drop-shadow(0 3px 4px rgba(0, 0, 0, 0.75));
  animation: shimmy 0.18s linear infinite;
}

@keyframes shimmy {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-0.6px);
  }
}

/* Slipstream lines trailing off the rear wing */
.car__streaks {
  position: absolute;
  top: 50%;
  right: 100%;
  width: 20px;
  height: 12px;
  transform: translateY(-50%);
  background:
    linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.55)) 0 1px / 100% 1px no-repeat,
    linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.35)) 8px 6px / 80% 1px no-repeat,
    linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.55)) 0 10px / 100% 1px no-repeat;
  animation: streaks 0.35s linear infinite;
}

@keyframes streaks {
  from {
    opacity: 1;
    transform: translate(0, -50%);
  }
  to {
    opacity: 0.3;
    transform: translate(-10px, -50%);
  }
}

@media (prefers-reduced-motion: reduce) {
  .car__body,
  .car__streaks,
  .fill {
    animation: none;
  }
}

.flag {
  position: absolute;
  right: 0;
  top: 0;
  width: 20px;
  height: 100%;
}

.hint {
  margin: 0.7rem 0 0;
  font-size: 0.8rem;
  color: var(--text-dim);
}
</style>
