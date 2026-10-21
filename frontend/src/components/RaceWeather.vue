<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, MarkAreaComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { EChartsOption } from 'echarts'
import type { RaceWeather } from '@/types/api'

use([LineChart, GridComponent, MarkAreaComponent, TooltipComponent, CanvasRenderer])

const TRACK_COLOUR = '#ffd60a'
const AIR_COLOUR = '#f5f5f7'
const RAIN_COLOUR = '#33c3ff'

const props = defineProps<{ weather: RaceWeather }>()

const condition = computed(() => {
  const share = props.weather.rain_share
  if (share >= 0.5)
    return {
      kind: 'wet',
      label: 'Wet race',
      detail: `Rain for ${Math.round(share * 100)}% of it`,
    }
  if (share > 0)
    return {
      kind: 'mixed',
      label: 'Mixed conditions',
      detail: `Rain for ${Math.round(share * 100)}% of the race`,
    }
  return { kind: 'dry', label: 'Dry race', detail: 'No rain recorded' }
})

function range(min: number | null, max: number | null): string {
  if (min === null || max === null) return '—'
  const lo = Math.round(min)
  const hi = Math.round(max)
  return lo === hi ? `${lo}°` : `${lo}–${hi}°`
}

const COMPASS = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
const windFrom = computed(() => {
  const d = props.weather.wind_direction
  return d === null ? '' : COMPASS[Math.round(d / 45) % 8]
})

// Temperatures through the race, with rain shaded behind
const rainBands = computed(() => {
  const samples = props.weather.samples
  const bands: [number, number][] = []
  let start: number | null = null
  samples.forEach((s, i) => {
    if (s.rain && start === null) start = s.minute
    const ends = !s.rain || i === samples.length - 1
    if (ends && start !== null) {
      bands.push([start, s.rain ? s.minute : samples[i - 1].minute])
      start = null
    }
  })
  return bands
})

const chart = computed<EChartsOption | null>(() => {
  const samples = props.weather.samples
  if (samples.filter((s) => s.track !== null || s.air !== null).length < 2) return null
  const tooltipRow = (colour: string, label: string, value: string) =>
    `<div style="display:flex;justify-content:space-between;gap:14px"><span><i style="display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px;background:${colour}"></i>${label}</span><b>${value}</b></div>`
  return {
    backgroundColor: 'transparent',
    textStyle: { fontFamily: 'Titillium Web, system-ui, sans-serif' },
    animationDuration: 900,
    grid: { left: 40, right: 12, top: 14, bottom: 26 },
    xAxis: {
      type: 'value',
      min: 0,
      max: Math.ceil(samples.at(-1)?.minute ?? 0),
      interval: 30,
      axisLine: { lineStyle: { color: '#38383f' } },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: {
        color: '#dcdce3',
        fontSize: 10,
        formatter: (m: number) => (m === 0 ? 'Start' : `${m} min`),
      },
    },
    yAxis: {
      type: 'value',
      scale: true,
      splitNumber: 3,
      splitLine: { lineStyle: { color: '#1d1d27' } },
      axisLabel: { color: '#dcdce3', fontSize: 10, formatter: (v: number) => `${Math.round(v)}°` },
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#15151e',
      borderColor: '#38383f',
      padding: [8, 12],
      textStyle: { color: '#f5f5f7', fontSize: 12 },
      formatter: (params: unknown) => {
        const [first] = params as { dataIndex: number }[]
        const s = samples[first.dataIndex]
        const rows = [`<b>${Math.round(s.minute)} min after the start</b>`]
        if (s.track !== null)
          rows.push(tooltipRow(TRACK_COLOUR, 'Track', `${s.track.toFixed(1)}°C`))
        if (s.air !== null) rows.push(tooltipRow(AIR_COLOUR, 'Air', `${s.air.toFixed(1)}°C`))
        rows.push(tooltipRow(RAIN_COLOUR, 'Rain', s.rain ? 'Yes' : 'No'))
        return rows.join('')
      },
    },
    series: [
      {
        name: 'Track',
        type: 'line',
        data: samples.map((s) => [s.minute, s.track]),
        showSymbol: false,
        smooth: 0.3,
        connectNulls: true,
        lineStyle: { width: 2.5, color: TRACK_COLOUR },
        itemStyle: { color: TRACK_COLOUR },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(255, 214, 10, 0.22)' },
              { offset: 1, color: 'rgba(255, 214, 10, 0)' },
            ],
          },
        },
        markArea: {
          silent: true,
          itemStyle: { color: 'rgba(51, 195, 255, 0.16)' },
          data: rainBands.value.map(([from, to]) => [{ xAxis: from }, { xAxis: to }]) as never,
        },
      },
      {
        name: 'Air',
        type: 'line',
        data: samples.map((s) => [s.minute, s.air]),
        showSymbol: false,
        smooth: 0.3,
        connectNulls: true,
        lineStyle: { width: 2, color: AIR_COLOUR, type: 'dashed' },
        itemStyle: { color: AIR_COLOUR },
      },
    ],
  }
})
</script>

<template>
  <div class="weather" :class="`weather--${condition.kind}`">
    <div class="weather__head">
      <svg class="icon" viewBox="0 0 48 48" aria-hidden="true">
        <!-- Sun (dry and mixed) -->
        <g v-if="condition.kind !== 'wet'" class="icon__sun">
          <circle cx="18" cy="18" r="8" />
          <g class="icon__rays">
            <line
              v-for="a in 8"
              :key="a"
              x1="18"
              y1="4"
              x2="18"
              y2="7"
              :transform="`rotate(${a * 45} 18 18)`"
            />
          </g>
        </g>
        <!-- Cloud and rain (mixed and wet) -->
        <g v-if="condition.kind !== 'dry'">
          <path class="icon__cloud" d="M14 34h20a7 7 0 0 0 0-14 10 10 0 0 0-19-2 8 8 0 0 0-1 16z" />
          <g class="icon__rain">
            <line x1="18" y1="38" x2="16" y2="44" />
            <line x1="25" y1="38" x2="23" y2="44" />
            <line x1="32" y1="38" x2="30" y2="44" />
          </g>
        </g>
      </svg>
      <div>
        <span class="weather__label">{{ condition.label }}</span>
        <span class="weather__detail">{{ condition.detail }}</span>
      </div>
    </div>

    <dl class="stats">
      <div>
        <dt>Air</dt>
        <dd class="num">{{ range(weather.air_min, weather.air_max) }}<small>C</small></dd>
      </div>
      <div>
        <dt>Track</dt>
        <dd class="num">{{ range(weather.track_min, weather.track_max) }}<small>C</small></dd>
      </div>
      <div>
        <dt>Humidity</dt>
        <dd class="num">
          {{ weather.humidity === null ? '—' : Math.round(weather.humidity) }}<small>%</small>
        </dd>
      </div>
      <div>
        <dt>Wind</dt>
        <dd class="num">
          <svg
            v-if="weather.wind_direction !== null"
            class="wind-arrow"
            viewBox="0 0 16 16"
            :style="{ transform: `rotate(${weather.wind_direction + 180}deg)` }"
            aria-hidden="true"
          >
            <path d="M8 1 L13 13 L8 10 L3 13 Z" />
          </svg>
          {{ weather.wind_speed === null ? '—' : weather.wind_speed.toFixed(1)
          }}<small>m/s {{ windFrom }}</small>
        </dd>
      </div>
    </dl>

    <div v-if="chart" class="trend">
      <div class="trend__head">
        <span class="trend__title">Through the race</span>
        <span class="trend__legend" aria-hidden="true">
          <span><i class="key key--track" />Track</span>
          <span><i class="key key--air" />Air</span>
          <span v-if="rainBands.length"><i class="key key--rain" />Rain</span>
        </span>
      </div>
      <VChart :option="chart" class="trend__chart" autoresize />
    </div>
  </div>
</template>

<style scoped>
.weather {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}

.weather__head {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.weather__head > div {
  display: flex;
  flex-direction: column;
}

.weather__label {
  font-size: 0.95rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.weather__detail {
  font-size: 0.8rem;
  color: var(--text-muted);
}

.icon {
  flex: none;
  width: 44px;
  height: 44px;
}

.icon__sun circle {
  fill: var(--yellow);
}

.icon__rays {
  stroke: var(--yellow);
  stroke-width: 2.5;
  stroke-linecap: round;
  transform-origin: 18px 18px;
  animation: spin 12s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.icon__cloud {
  fill: #d8dbe6;
}

.icon__rain {
  stroke: #33c3ff;
  stroke-width: 2.5;
  stroke-linecap: round;
  animation: rain 0.9s linear infinite;
}

@keyframes rain {
  from {
    transform: translateY(-3px);
    opacity: 0.3;
  }
  to {
    transform: translateY(3px);
    opacity: 1;
  }
}

.stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.5rem;
  margin: 0;
}

.stats div {
  padding: 0.45rem 0.6rem;
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
}

dd {
  display: flex;
  align-items: baseline;
  gap: 0.15rem;
  margin: 0.15rem 0 0;
  font-size: 1rem;
  font-weight: 600;
  white-space: nowrap;
}

dd small {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--text-muted);
}

.wind-arrow {
  align-self: center;
  width: 14px;
  height: 14px;
  margin-right: 0.15rem;
  fill: var(--text);
}

.trend__head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.4rem 1rem;
}

.trend__title {
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.trend__legend {
  display: flex;
  gap: 0.9rem;
  font-size: 0.75rem;
  color: var(--text-muted);
}

.trend__legend span {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
}

.key {
  display: inline-block;
  width: 16px;
  height: 3px;
  border-radius: 2px;
}

.key--track {
  background: #ffd60a;
}

.key--air {
  background: repeating-linear-gradient(90deg, #f5f5f7 0 4px, transparent 4px 7px);
}

.key--rain {
  height: 10px;
  background: rgba(51, 195, 255, 0.45);
}

.trend__chart {
  width: 100%;
  height: 170px;
}

@media (max-width: 480px) {
  .stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (prefers-reduced-motion: reduce) {
  .icon__rays,
  .icon__rain {
    animation: none;
  }
}
</style>
