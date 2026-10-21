<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { ScatterChart } from 'echarts/charts'
import { GridComponent, MarkAreaComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { EChartsOption } from 'echarts'
import type { FlagStatus, RaceDetail, StopDetail } from '@/types/api'
import { formatLuck, teamColour } from '@/utils/format'
import { FLAG_NAME } from '@/utils/stories'

use([ScatterChart, GridComponent, TooltipComponent, MarkAreaComponent, CanvasRenderer])

const props = defineProps<{ race: RaceDetail }>()

const ZONE: Record<Exclude<FlagStatus, 'GREEN'>, { fill: string; label: string }> = {
  SC: { fill: 'rgba(255, 214, 10, 0.16)', label: 'SC' },
  VSC: { fill: 'rgba(255, 214, 10, 0.08)', label: 'VSC' },
  RED: { fill: 'rgba(225, 6, 0, 0.2)', label: 'RED' },
}

function toneOf(value: number | null): string {
  if (value === null) return '#6b6b76'
  return value >= 0 ? '#1fe08a' : '#ff3b47'
}

function row(label: string, value: string, tone = '#f5f5f7'): string {
  return `<div style="display:flex;justify-content:space-between;gap:16px"><span style="color:#f0f0f4">${label}</span><b style="color:${tone}">${value}</b></div>`
}

function tooltip(code: string, stop: StopDetail): string {
  const parts = [
    `<div style="margin-bottom:4px"><b>${code}</b> · Lap ${stop.lap} · ${stop.status === 'GREEN' ? 'Green flag' : FLAG_NAME[stop.status]}</div>`,
    row('Pit lane', `${stop.pit_duration.toFixed(3)}s`),
  ]
  if (stop.time_loss !== null)
    parts.push(row('Lost to the field', `${Math.max(0, stop.time_loss).toFixed(3)}s`))
  if (stop.luck !== null) parts.push(row('Timing luck', formatLuck(stop.luck), toneOf(stop.luck)))
  if (stop.missed < 0 && stop.missed_status)
    parts.push(
      row(
        `Missed ${FLAG_NAME[stop.missed_status]} (L${stop.missed_lap})`,
        formatLuck(stop.missed),
        toneOf(stop.missed),
      ),
    )
  if (stop.execution !== null)
    parts.push(row('Pit crew', formatLuck(stop.execution), toneOf(stop.execution)))
  if (stop.penalty) parts.push(row('Penalty served', `${stop.penalty}s`, '#ffd60a'))
  if (stop.note)
    parts.push(
      `<div style="margin-top:4px;max-width:240px;white-space:normal;color:#dcdce3">${stop.note}</div>`,
    )
  return parts.join('')
}

const drivers = computed(() => props.race.drivers.filter((d) => d.stops.length > 0))

const zones = computed(() => {
  const { events, total_laps } = props.race
  return events.flatMap((ev, i) => {
    if (ev.type === 'GREEN') return []
    const end = events[i + 1]?.lap ?? total_laps
    const zone = ZONE[ev.type]
    return [
      [
        {
          xAxis: ev.lap - 0.5,
          itemStyle: { color: zone.fill },
          label: {
            show: true,
            formatter: zone.label,
            color: '#ffd60a',
            fontWeight: 700,
            fontSize: 10,
          },
        },
        { xAxis: end - 0.5 },
      ],
    ]
  })
})

const option = computed<EChartsOption>(() => ({
  backgroundColor: 'transparent',
  textStyle: { fontFamily: 'Titillium Web, system-ui, sans-serif' },
  animationDuration: 900,
  animationEasing: 'cubicOut',
  grid: { left: 52, right: 16, top: 28, bottom: 36 },
  xAxis: {
    type: 'value',
    min: 1,
    max: Math.max(props.race.total_laps, 1),
    name: 'LAP',
    nameLocation: 'end',
    nameTextStyle: { color: '#dcdce3', fontWeight: 700, fontSize: 10 },
    axisLine: { lineStyle: { color: '#38383f' } },
    splitLine: { lineStyle: { color: '#1d1d27' } },
    axisLabel: { color: '#f0f0f4' },
  },
  yAxis: {
    type: 'category',
    inverse: true,
    data: drivers.value.map((d) => d.name_acronym),
    axisLabel: { color: '#f5f5f7', fontWeight: 700, fontSize: 11 },
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: { show: true, lineStyle: { color: '#15151e' } },
  },
  tooltip: {
    trigger: 'item',
    backgroundColor: '#15151e',
    borderColor: '#38383f',
    padding: [8, 12],
    textStyle: { color: '#f5f5f7', fontSize: 12 },
    formatter: (p: unknown) => {
      const { code, stop } = (p as { data: { code: string; stop: StopDetail } }).data
      return tooltip(code, stop)
    },
  },
  series: [
    {
      type: 'scatter',
      silent: true,
      data: [],
      markArea: { silent: true, data: zones.value as never },
    },
    ...drivers.value.map((d) => ({
      name: d.name_acronym,
      type: 'scatter' as const,
      data: d.stops.map((stop) => {
        const tone = toneOf(stop.delta)
        return {
          value: [stop.lap, d.name_acronym],
          code: d.name_acronym,
          stop,
          symbol: stop.missed < 0 ? 'triangle' : stop.status === 'GREEN' ? 'circle' : 'diamond',
          symbolRotate: stop.missed < 0 ? 180 : 0,
          symbolSize: stop.status === 'GREEN' && stop.missed === 0 ? 11 : 16,
          itemStyle: {
            color: tone,
            borderColor: teamColour(d.team_colour),
            borderWidth: 2,
            shadowBlur: 10,
            shadowColor: `${tone}80`,
          },
        }
      }),
      emphasis: { scale: 1.5 },
    })),
  ],
}))

const height = computed(() => `${Math.max(280, drivers.value.length * 26 + 70)}px`)
</script>

<template>
  <div>
    <div class="legend" aria-hidden="true">
      <span><i class="dot dot--lucky" />Cheaper than normal</span>
      <span><i class="dot dot--unlucky" />Costlier than normal</span>
      <span><i class="diamond" />Under SC / VSC</span>
      <span><i class="triangle" />Pitted just before one</span>
      <span><i class="zone" />Neutralised laps</span>
    </div>
    <VChart :option="option" :style="{ height, width: '100%' }" autoresize />
  </div>
</template>

<style scoped>
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1.25rem;
  margin-bottom: 0.5rem;
  font-size: 0.78rem;
  color: var(--text-muted);
}

.legend span {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.dot--lucky {
  background: var(--lucky);
}

.dot--unlucky {
  background: var(--unlucky);
}

.diamond {
  width: 9px;
  height: 9px;
  background: var(--text-muted);
  transform: rotate(45deg);
}

.triangle {
  width: 0;
  height: 0;
  border-left: 6px solid transparent;
  border-right: 6px solid transparent;
  border-top: 10px solid var(--unlucky);
}

.zone {
  width: 18px;
  height: 10px;
  background: rgba(255, 214, 10, 0.25);
  border-radius: 2px;
}
</style>
