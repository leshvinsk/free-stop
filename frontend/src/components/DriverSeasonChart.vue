<script setup lang="ts">
import { computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, MarkLineComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { EChartsOption } from 'echarts'
import type { DriverRaceResult } from '@/types/api'

use([BarChart, LineChart, GridComponent, MarkLineComponent, TooltipComponent, CanvasRenderer])

// Works for a driver's races or a team's: only these fields are used
type SeasonRace = Pick<DriverRaceResult, 'round' | 'race_name' | 'race_luck' | 'no_stops'>

const props = defineProps<{ races: SeasonRace[] }>()

// Neutral white so the running total reads clearly over both green and red bars,
// whatever the team colour
const LINE = '#f5f5f7'

const option = computed<EChartsOption>(() => {
  const labels = props.races.map((r) => `R${r.round}`)
  const values = props.races.map((r) => r.race_luck ?? 0)
  let running = 0
  const cumulative = values.map((v) => +(running += v).toFixed(2))

  return {
    backgroundColor: 'transparent',
    textStyle: { fontFamily: 'Titillium Web, system-ui, sans-serif' },
    animationDuration: 900,
    animationEasing: 'cubicOut',
    grid: { left: 48, right: 16, top: 24, bottom: 32 },
    xAxis: {
      type: 'category',
      data: labels,
      axisLine: { lineStyle: { color: '#38383f' } },
      axisTick: { show: false },
      axisLabel: { color: '#f0f0f4', fontWeight: 700, fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#1d1d27' } },
      axisLabel: {
        color: '#f0f0f4',
        formatter: (v: number) => `${v > 0 ? '+' : ''}${v}s`,
      },
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow', shadowStyle: { color: 'rgba(255,255,255,0.04)' } },
      backgroundColor: '#15151e',
      borderColor: '#38383f',
      padding: [8, 12],
      textStyle: { color: '#f5f5f7', fontSize: 12 },
      formatter: (params: unknown) => {
        const [bar] = params as { dataIndex: number }[]
        const race = props.races[bar.dataIndex]
        const fmt = (v: number) => `${v >= 0 ? '+' : ''}${v.toFixed(2)}s`
        const result = race.no_stops
          ? 'No stops'
          : race.race_luck === null
            ? 'N/A'
            : fmt(race.race_luck)
        return `<b>${race.race_name}</b><br/>Race luck: <b>${result}</b><br/>Season total: ${fmt(cumulative[bar.dataIndex])}`
      },
    },
    series: [
      {
        name: 'Race luck',
        type: 'bar',
        barMaxWidth: 26,
        // Zero line: the field average every race is measured against
        markLine: {
          silent: true,
          symbol: 'none',
          label: { show: false },
          lineStyle: { color: '#6b6b76', type: 'dashed', width: 1 },
          data: [{ yAxis: 0 }],
        },
        data: values.map((v) => ({
          value: v,
          itemStyle: {
            color: v >= 0 ? '#1fe08a' : '#ff3b47',
            borderRadius: v >= 0 ? [3, 3, 0, 0] : [0, 0, 3, 3],
          },
        })),
      },
      {
        name: 'Season total',
        type: 'line',
        data: cumulative,
        smooth: 0.3,
        symbol: 'circle',
        symbolSize: 7,
        lineStyle: {
          width: 2.5,
          color: LINE,
          shadowBlur: 8,
          shadowColor: 'rgba(0, 0, 0, 0.8)',
        },
        itemStyle: { color: LINE, borderColor: '#0b0b10', borderWidth: 2 },
        emphasis: { scale: 1.6 },
        z: 3,
      },
    ],
  }
})
</script>

<template>
  <div>
    <div class="legend" aria-hidden="true">
      <span><i class="swatch swatch--lucky" />Luckier than the field</span>
      <span><i class="swatch swatch--unlucky" />Unluckier than the field</span>
      <span
        ><i class="swatch swatch--line"><i class="swatch__dot" /></i>Running season total</span
      >
    </div>
    <VChart :option="option" style="height: 320px; width: 100%" autoresize />
  </div>
</template>

<style scoped>
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1.25rem;
  margin-bottom: 0.25rem;
  font-size: 0.78rem;
  color: var(--text-muted);
}

.legend span {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
}

.swatch {
  display: inline-block;
}

.swatch--lucky,
.swatch--unlucky {
  width: 10px;
  height: 12px;
  border-radius: 2px;
}

.swatch--lucky {
  background: var(--lucky);
}

.swatch--unlucky {
  background: var(--unlucky);
}

.swatch--line {
  position: relative;
  width: 20px;
  height: 2.5px;
  border-radius: 2px;
  background: #f5f5f7;
}

.swatch__dot {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #f5f5f7;
  box-shadow: 0 0 0 2px #0b0b10;
  transform: translate(-50%, -50%);
}
</style>
