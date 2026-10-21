<script setup lang="ts">
import { computed } from 'vue'
import type { CircuitMap } from '@/types/api'

const props = defineProps<{
  circuit: CircuitMap
  laps?: number
}>()

// F1 TV sector colours
const SECTOR_COLOURS = ['#ff3b47', '#33c3ff', '#ffd60a']
const SIZE = 1000 // longest side after rotating
const PAD = 60
const BADGE = 26 // marker radius

type Point = [number, number]

// Turn the circuit so its long side runs left to right and it fills a wide card
const layout = computed(() => {
  const raw = props.circuit.points
  let best = { angle: 0, ratio: 0 }
  for (let deg = 0; deg < 180; deg += 3) {
    const a = (deg * Math.PI) / 180
    const xs = raw.map(([x, y]) => x * Math.cos(a) - y * Math.sin(a))
    const ys = raw.map(([x, y]) => x * Math.sin(a) + y * Math.cos(a))
    const ratio = (Math.max(...xs) - Math.min(...xs)) / (Math.max(...ys) - Math.min(...ys) || 1)
    // Prefer staying close to the true orientation unless rotating is clearly wider
    if (ratio > best.ratio * 1.04) best = { angle: a, ratio }
  }
  const { angle } = best
  const turned = raw.map(([x, y]): Point => [
    x * Math.cos(angle) - y * Math.sin(angle),
    x * Math.sin(angle) + y * Math.cos(angle),
  ])
  const minX = Math.min(...turned.map((p) => p[0]))
  const minY = Math.min(...turned.map((p) => p[1]))
  const w = Math.max(...turned.map((p) => p[0])) - minX
  const h = Math.max(...turned.map((p) => p[1])) - minY
  const scale = SIZE / Math.max(w, h)
  return {
    points: turned.map(([x, y]): Point => [(x - minX) * scale, (y - minY) * scale]),
    width: w * scale,
    height: h * scale,
  }
})

const viewBox = computed(
  () => `${-PAD} ${-PAD} ${layout.value.width + PAD * 2} ${layout.value.height + PAD * 2}`,
)

function pathOf(points: Point[], close = false): string {
  if (!points.length) return ''
  const [first, ...rest] = points
  return `M${first[0]},${first[1]} ${rest.map(([x, y]) => `L${x},${y}`).join(' ')}${close ? ' Z' : ''}`
}

/** Points from index a to b inclusive, wrapping past the end of the lap. */
function slice(a: number, b: number): Point[] {
  const pts = layout.value.points
  return a <= b ? pts.slice(a, b + 1) : [...pts.slice(a), ...pts.slice(0, b + 1)]
}

function middle(pts: Point[]): Point {
  return pts[Math.floor(pts.length / 2)]
}

function heading(i: number): number {
  const pts = layout.value.points
  const [x0, y0] = pts[i]
  const [x1, y1] = pts[(i + 1) % pts.length]
  return (Math.atan2(y1 - y0, x1 - x0) * 180) / Math.PI
}

const track = computed(() => pathOf(layout.value.points, true))

// Each sector's marker sits on the track where that sector begins
const sectors = computed(() => {
  const n = layout.value.points.length
  const bounds = [0, ...props.circuit.sectors, n - 1]
  return bounds.slice(0, -1).map((start, i) => {
    const last = i === bounds.length - 2
    // The last sector closes the loop back to the line (unless it is the whole lap)
    const pts = slice(start, last ? (start === 0 ? n - 1 : 0) : bounds[i + 1])
    // Sector 1 starts on the line, so its marker moves a little way along
    const at = i === 0 ? pts[Math.min(pts.length - 1, Math.round(pts.length * 0.12))] : pts[0]
    return {
      d: pathOf(pts),
      colour: SECTOR_COLOURS[i] ?? '#fff',
      label: `S${i + 1}`,
      x: at[0],
      y: at[1],
    }
  })
})

function bands(ranges: [number, number][]) {
  return ranges.map(([a, b], i) => {
    const pts = slice(a, b)
    const [x, y] = middle(pts)
    return { d: pathOf(pts), n: i + 1, x, y }
  })
}

const drsZones = computed(() => (props.circuit.drs_era ? bands(props.circuit.drs_zones) : []))
const straights = computed(() => bands(props.circuit.straights))

const startLine = computed(() => {
  const [x, y] = layout.value.points[0]
  return { x, y, angle: heading(0) }
})

// Chevrons on the track just after the line, pointing the way the cars go
const chevrons = computed(() => {
  const pts = layout.value.points
  return [0.035, 0.06].map((f) => {
    const i = Math.min(pts.length - 2, Math.round(pts.length * f))
    return { x: pts[i][0], y: pts[i][1], angle: heading(i) }
  })
})

const facts = computed(() => [
  { label: 'Direction', value: props.circuit.clockwise ? 'Clockwise' : 'Anticlockwise' },
  { label: 'Sectors', value: String(sectors.value.length) },
  props.circuit.drs_era
    ? { label: 'DRS zones', value: String(drsZones.value.length) }
    : { label: 'Aid', value: 'Active aero' },
  { label: 'Straights', value: String(straights.value.length) },
  ...(props.laps ? [{ label: 'Race laps', value: String(props.laps) }] : []),
])
</script>

<template>
  <div class="circuit">
    <div class="map-wrap">
      <svg class="map" :viewBox="viewBox" role="img" aria-label="Circuit map">
        <!-- Tarmac -->
        <path class="tarmac-edge" :d="track" />
        <path class="tarmac" :d="track" />

        <!-- Full-throttle straights -->
        <path v-for="s in straights" :key="`straight-${s.n}`" class="straight" :d="s.d" />

        <!-- DRS zones -->
        <path v-for="z in drsZones" :key="`drs-${z.n}`" class="drs-band" :d="z.d" />

        <!-- Sectors, drawn in on load -->
        <path
          v-for="(s, i) in sectors"
          :key="s.label"
          class="sector"
          :d="s.d"
          :stroke="s.colour"
          pathLength="1"
          :style="{ '--i': i }"
        />

        <!-- Direction of travel -->
        <g
          v-for="(c, i) in chevrons"
          :key="i"
          class="chevron"
          :transform="`translate(${c.x} ${c.y}) rotate(${c.angle})`"
        >
          <path d="M-9,-10 L5,0 L-9,10" />
        </g>

        <!-- Start / finish -->
        <g :transform="`translate(${startLine.x} ${startLine.y}) rotate(${startLine.angle + 90})`">
          <rect class="start" x="-26" y="-7" width="52" height="14" rx="2" />
          <rect x="-26" y="-7" width="13" height="7" fill="#fff" />
          <rect x="0" y="-7" width="13" height="7" fill="#fff" />
          <rect x="-13" y="0" width="13" height="7" fill="#fff" />
          <rect x="13" y="0" width="13" height="7" fill="#fff" />
        </g>

        <!-- Markers sit on the track itself, so labels can't collide -->
        <g
          v-for="z in drsZones"
          :key="`drs-badge-${z.n}`"
          class="badge badge--drs"
          :transform="`translate(${z.x} ${z.y})`"
        >
          <circle :r="BADGE" />
          <text>{{ z.n }}</text>
        </g>
        <g
          v-for="(s, i) in sectors"
          :key="`${s.label}-badge`"
          class="badge badge--sector"
          :style="{ '--i': i, '--colour': s.colour }"
          :transform="`translate(${s.x} ${s.y})`"
        >
          <rect
            :x="-BADGE * 1.25"
            :y="-BADGE * 0.85"
            :width="BADGE * 2.5"
            :height="BADGE * 1.7"
            rx="8"
          />
          <text>{{ s.label }}</text>
        </g>
      </svg>
    </div>

    <div class="legend" aria-hidden="true">
      <span v-for="(colour, i) in SECTOR_COLOURS" :key="colour">
        <i class="swatch" :style="{ background: colour }" />Sector {{ i + 1 }}
      </span>
      <span v-if="circuit.drs_era"><i class="swatch swatch--drs">1</i>DRS zone</span>
      <span><i class="swatch swatch--straight" />Full-throttle straight</span>
      <span><i class="swatch swatch--start" />Start / finish</span>
    </div>

    <dl class="facts">
      <div v-for="f in facts" :key="f.label">
        <dt>{{ f.label }}</dt>
        <dd>{{ f.value }}</dd>
      </div>
    </dl>
  </div>
</template>

<style scoped>
.circuit {
  display: flex;
  flex-direction: column;
  flex: 1;
  gap: 0.85rem;
  min-height: 0;
}

.map-wrap {
  display: flex;
  flex: 1;
  min-height: 120px;
  max-height: 420px;
}

.map {
  display: block;
  width: 100%;
  flex: 1;
}

.tarmac-edge {
  fill: none;
  stroke: #000;
  stroke-width: 44;
  stroke-linejoin: round;
  opacity: 0.55;
}

.tarmac {
  fill: none;
  stroke: #2c2c38;
  stroke-width: 32;
  stroke-linejoin: round;
}

.straight {
  fill: none;
  stroke: #50505f;
  stroke-width: 32;
  stroke-linecap: round;
}

.drs-band {
  fill: none;
  stroke: var(--lucky);
  stroke-width: 32;
  stroke-linecap: round;
  opacity: 0.45;
  animation: drs-pulse 1.8s ease-in-out infinite;
}

@keyframes drs-pulse {
  50% {
    opacity: 0.75;
  }
}

.sector {
  fill: none;
  stroke-width: 9;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-dasharray: 1;
  stroke-dashoffset: 1;
  animation: draw 1.1s var(--ease-out) forwards;
  animation-delay: calc(var(--i) * 0.4s);
}

@keyframes draw {
  to {
    stroke-dashoffset: 0;
  }
}

.chevron path {
  fill: none;
  stroke: #fff;
  stroke-width: 5;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.start {
  fill: #0b0b10;
}

.badge text {
  font-family: var(--font-num);
  font-size: 30px;
  font-weight: 800;
  text-anchor: middle;
  dominant-baseline: central;
}

.badge--drs circle {
  fill: var(--lucky);
  stroke: #0b0b10;
  stroke-width: 5;
}

.badge--drs text {
  fill: #0b0b10;
}

.badge--sector {
  opacity: 0;
  animation: fade-in 0.5s ease-out forwards;
  animation-delay: calc(var(--i) * 0.4s + 0.5s);
}

.badge--sector rect {
  fill: #0b0b10;
  stroke: var(--colour);
  stroke-width: 4;
}

.badge--sector text {
  font-style: italic;
  fill: var(--colour);
}

@keyframes fade-in {
  to {
    opacity: 1;
  }
}

.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem 1.1rem;
  font-size: 0.75rem;
  color: var(--text-muted);
}

.legend span {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
}

.swatch {
  display: inline-grid;
  place-items: center;
  width: 16px;
  height: 6px;
  border-radius: 2px;
}

.swatch--drs {
  height: 16px;
  border-radius: 50%;
  font-family: var(--font-num);
  font-size: 0.7rem;
  font-style: normal;
  font-weight: 700;
  color: #0b0b10;
  background: var(--lucky);
}

.swatch--straight {
  height: 9px;
  background: #50505f;
}

.swatch--start {
  height: 9px;
  background: repeating-linear-gradient(90deg, #fff 0 3px, #0b0b10 3px 6px);
}

.facts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(96px, 1fr));
  gap: 0.5rem;
  margin: 0;
}

.facts div {
  padding: 0.45rem 0.7rem;
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid var(--line);
  border-radius: var(--radius);
}

dt {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--text-muted);
  white-space: nowrap;
}

dd {
  margin: 0.15rem 0 0;
  font-size: 0.95rem;
  font-weight: 600;
  letter-spacing: 0.01em;
}

@media (prefers-reduced-motion: reduce) {
  .sector {
    animation: none;
    stroke-dashoffset: 0;
  }

  .badge--sector {
    animation: none;
    opacity: 1;
  }

  .drs-band {
    animation: none;
  }
}
</style>
