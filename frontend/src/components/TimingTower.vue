<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import type { TowerRow } from '@/types/ui'
import { formatLuck, luckClass } from '@/utils/format'
import { countryName, flagUrl, teamLogo } from '@/utils/identity'

const props = withDefaults(
  defineProps<{
    rows: TowerRow[]
    numbered?: boolean
    titleLabel?: string
    tagLabel?: string
    valueLabel?: string
    barLabel?: string
  }>(),
  {
    numbered: true,
    titleLabel: 'Driver',
    tagLabel: '',
    valueLabel: 'Time saved',
    barLabel: 'Unlucky ← → Lucky',
  },
)

const maxAbs = computed(() =>
  Math.max(1, ...props.rows.map((r) => (r.luck === null ? 0 : Math.abs(r.luck)))),
)

// Track position changes between updates so rows can flash ▲/▼ like a live timing screen
const moves = ref(new Map<TowerRow['key'], number>())
let previous = new Map<TowerRow['key'], number>()
let clearTimer: ReturnType<typeof setTimeout> | undefined

watch(
  () => props.rows.map((r) => r.key),
  (keys) => {
    const next = new Map(keys.map((k, i) => [k, i]))
    const changed = new Map<TowerRow['key'], number>()
    next.forEach((i, k) => {
      const before = previous.get(k)
      if (before !== undefined && before !== i) changed.set(k, before - i)
    })
    if (changed.size) {
      moves.value = changed
      clearTimeout(clearTimer)
      clearTimer = setTimeout(() => (moves.value = new Map()), 4000)
    }
    previous = next
  },
  { immediate: true },
)

onBeforeUnmount(() => clearTimeout(clearTimer))

const router = useRouter()

// The whole row is a link, so the logo can't be a nested <a>: it navigates on its own instead
function openTeam(event: Event, row: TowerRow): void {
  if (!row.teamTo) return // rows without a team page keep the row's own link
  event.preventDefault()
  event.stopPropagation()
  void router.push(row.teamTo)
}

// Logos that failed to load fall back to the team-colour bar
const brokenLogos = ref(new Set<string>())
function logoOf(row: TowerRow): string | null {
  const url = row.team ? teamLogo(row.team) : null
  return url && !brokenLogos.value.has(url) ? url : null
}
function markBroken(url: string): void {
  brokenLogos.value = new Set(brokenLogos.value).add(url)
}

function barStyle(luck: number): Record<string, string> {
  return { width: `${(Math.abs(luck) / maxAbs.value) * 50}%` }
}
</script>

<template>
  <div class="tower card">
    <div class="tower__head" :class="{ 'tower__head--plain': !numbered }">
      <span v-if="numbered">Pos</span>
      <span />
      <span>{{ titleLabel }}</span>
      <span class="col-tag">{{ tagLabel }}</span>
      <span class="col-bar">{{ barLabel }}</span>
      <span class="col-value">{{ valueLabel }}</span>
    </div>

    <TransitionGroup tag="ol" name="tower" class="tower__list">
      <li v-for="(row, i) in rows" :key="row.key" :style="{ '--i': Math.min(i, 20) }">
        <component
          :is="row.to ? RouterLink : 'div'"
          :to="row.to"
          class="row"
          :class="{
            'row--plain': !numbered,
            'row--link': row.to,
            'row--highlight': row.highlight,
            'row--muted': row.muted,
          }"
        >
          <span
            v-if="numbered"
            class="pos num"
            :class="{ 'pos--leader': i === 0 && (row.luck ?? 0) > 0 }"
          >
            {{ i + 1 }}
          </span>
          <span
            class="badge"
            :class="{ 'badge--link': row.teamTo }"
            :style="{ '--team': row.colour }"
            :role="row.teamTo ? 'link' : undefined"
            :tabindex="row.teamTo ? 0 : undefined"
            :aria-label="row.teamTo && row.team ? `${row.team} team page` : undefined"
            :title="row.teamTo && row.team ? `${row.team} — team page` : undefined"
            @click="openTeam($event, row)"
            @keydown.enter="openTeam($event, row)"
          >
            <img
              v-if="logoOf(row)"
              class="badge__logo"
              :src="logoOf(row) ?? undefined"
              :alt="row.team"
              :title="row.team"
              loading="lazy"
              @error="markBroken(logoOf(row) ?? '')"
            />
            <span v-else class="badge__stripe" />
          </span>
          <span class="who">
            <span v-if="row.code" class="code" :class="{ 'code--driver': row.country }">{{
              row.code
            }}</span>
            <span
              v-if="row.number !== undefined"
              class="number num"
              :style="{ '--team': row.colour }"
            >
              <span class="number__digits">{{ row.number }}</span>
            </span>
            <img
              v-if="row.country"
              class="flag"
              :src="flagUrl(row.country)"
              :alt="countryName(row.country)"
              :title="countryName(row.country)"
              loading="lazy"
            />
            <span class="names">
              <span class="title">{{ row.title }}</span>
              <span v-if="row.subtitle" class="subtitle">{{ row.subtitle }}</span>
            </span>
            <span
              v-if="moves.get(row.key)"
              class="move"
              :class="(moves.get(row.key) ?? 0) > 0 ? 'move--up' : 'move--down'"
              :aria-label="`moved ${(moves.get(row.key) ?? 0) > 0 ? 'up' : 'down'}`"
            >
              {{ (moves.get(row.key) ?? 0) > 0 ? '▲' : '▼' }}{{ Math.abs(moves.get(row.key) ?? 0) }}
            </span>
          </span>
          <span class="col-tag">
            <span v-if="row.tag" class="tag-chip">{{ row.tag }}</span>
          </span>
          <span v-if="row.barNote" class="col-bar bar-note">{{ row.barNote }}</span>
          <span v-else class="col-bar bar" aria-hidden="true">
            <span class="bar__axis" />
            <span
              v-if="row.luck"
              class="bar__fill"
              :class="row.luck > 0 ? 'bar__fill--pos' : 'bar__fill--neg'"
              :style="barStyle(row.luck)"
            />
          </span>
          <span class="col-value value num" :class="row.note ? 'muted' : luckClass(row.luck)">
            {{ row.note ?? formatLuck(row.luck) }}
          </span>
        </component>
      </li>
    </TransitionGroup>

    <p v-if="!rows.length" class="empty">No results yet.</p>
  </div>
</template>

<style scoped>
.tower {
  overflow: hidden;
}

.tower__head,
.row {
  display: grid;
  grid-template-columns: 2.75rem 40px minmax(0, 1fr) minmax(100px, 16%) minmax(120px, 28%) 5.5rem;
  align-items: center;
  gap: 0 1rem;
  padding: 0 1rem;
}

.tower__head--plain,
.row--plain {
  grid-template-columns: 40px minmax(0, 1fr) minmax(100px, 16%) minmax(120px, 28%) 5.5rem;
}

.tower__head {
  height: 40px;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--text-dim);
  border-bottom: 1px solid var(--line-strong);
  background: rgba(0, 0, 0, 0.25);
}

.tower__head .col-bar {
  text-align: center;
}

/* Longer labels such as "Saved per race" run left into the bar column's spare space,
   and wrap instead once the bars get too narrow to leave room */
.tower__head .col-value {
  white-space: nowrap;
  direction: rtl;
}

@media (max-width: 1080px) {
  .tower__head .col-value {
    white-space: normal;
    direction: ltr;
  }
}

.tower__list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.row {
  position: relative;
  min-height: 66px;
  border-bottom: 1px solid var(--line);
  transition:
    background 0.2s,
    transform 0.25s var(--ease-out);
}

li:last-child .row {
  border-bottom: 0;
}

.row--link {
  cursor: pointer;
}

.row--link::before {
  content: '';
  position: absolute;
  inset: 0 auto 0 0;
  width: 3px;
  background: var(--f1-red);
  transform: scaleY(0);
  transition: transform 0.25s var(--ease-out);
}

.row--link:hover {
  background: rgba(255, 255, 255, 0.035);
}

.row--link:hover::before {
  transform: scaleY(1);
}

.row--link:hover .code {
  color: var(--f1-red);
}

.pos {
  display: grid;
  place-items: center;
  width: 2rem;
  height: 2rem;
  font-size: 1.05rem;
  font-weight: 900;
  color: var(--text);
  background: var(--bg-elev-2);
  clip-path: polygon(6px 0, 100% 0, calc(100% - 6px) 100%, 0 100%);
}

.pos--leader {
  background: var(--purple);
  color: #fff;
  box-shadow: 0 0 16px rgba(177, 77, 255, 0.5);
}

/* Team logo, standing on its own */
.badge {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  transition: transform 0.3s var(--ease-out);
}

.badge__logo {
  width: 38px;
  height: 38px;
  object-fit: contain;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.6));
}

.badge__stripe {
  width: 4px;
  height: 26px;
  border-radius: 2px;
  background: var(--team);
}

.row--link:hover .badge {
  transform: scale(1.12);
}

.badge--link {
  cursor: pointer;
}

.badge--link:hover,
.badge--link:focus-visible {
  outline: none;
  transform: scale(1.15);
}

.badge--link:focus-visible .badge__logo {
  filter: drop-shadow(0 0 6px var(--team)) drop-shadow(0 2px 4px rgba(0, 0, 0, 0.6));
}

.row--highlight {
  background: color-mix(in srgb, var(--f1-red) 10%, transparent);
  box-shadow: inset 3px 0 0 var(--f1-red);
}

.row--muted {
  opacity: 0.5;
}

.row--muted:hover,
.row--muted:focus-within {
  opacity: 1;
}

/* Car number: italic, team-coloured, rolls up into place like a pit board */
.number {
  flex: none;
  display: inline-block;
  min-width: 2.9rem;
  height: 38px;
  overflow: hidden;
  font-size: 1.85rem;
  font-weight: 900;
  font-style: italic;
  line-height: 38px;
  text-align: center;
  color: var(--team);
  text-shadow: 0 0 14px color-mix(in srgb, var(--team) 55%, transparent);
}

.number__digits {
  display: inline-block;
  animation: number-roll 0.7s var(--ease-out) both;
  animation-delay: calc(var(--i) * 45ms + 200ms);
  transition: transform 0.35s var(--ease-out);
}

@keyframes number-roll {
  from {
    opacity: 0;
    transform: translateY(110%) skewX(-12deg);
  }
}

.row--link:hover .number__digits {
  transform: scale(1.15) skewX(-8deg);
}

/* Same width as the team logo; 3:2 like a real flag */
.flag {
  flex: none;
  width: 38px;
  height: 26px;
  border-radius: 3px;
  object-fit: cover;
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.12),
    0 3px 8px -3px rgba(0, 0, 0, 0.7);
  transition: transform 0.3s var(--ease-out);
}

.row--link:hover .flag {
  transform: scale(1.08);
}

.who {
  display: flex;
  align-items: center;
  gap: 0.9rem;
  min-width: 0;
}

.code {
  flex: none;
  min-width: 3rem;
  font-size: 1.05rem;
  font-weight: 900;
  letter-spacing: 0.04em;
  transition: color 0.2s;
}

.names {
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 0.2rem;
  line-height: 1.3;
}

.title,
.subtitle {
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.title {
  font-weight: 600;
}

.subtitle {
  font-size: 0.8rem;
  color: var(--text-muted);
  white-space: pre-line;
}

.move {
  flex: none;
  padding: 0.05rem 0.4rem;
  font-size: 0.7rem;
  font-weight: 700;
  border-radius: 3px;
  animation: flash 4s ease-out forwards;
}

.move--up {
  color: var(--lucky);
  background: rgba(31, 224, 138, 0.12);
}

.move--down {
  color: var(--unlucky);
  background: rgba(255, 59, 71, 0.12);
}

@keyframes flash {
  0%,
  80% {
    opacity: 1;
  }
  100% {
    opacity: 0;
  }
}

.col-tag {
  display: flex;
  align-items: center;
}

/* Same type as the value column, without its lucky/unlucky colour */
.tag-chip {
  font-family: var(--font-num);
  font-size: 1.05rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.01em;
  line-height: 1.5;
  white-space: pre-line;
  color: var(--text);
}

.bar {
  position: relative;
  height: 10px;
}

/* Same type as the value column, in grey */
.bar-note {
  text-align: center;
  font-family: var(--font-num);
  font-size: 1.05rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.01em;
  color: var(--text-muted);
}

.bar__axis {
  position: absolute;
  left: 50%;
  top: -6px;
  bottom: -6px;
  width: 1px;
  background: var(--line-strong);
}

.bar__fill {
  position: absolute;
  top: 0;
  height: 100%;
  border-radius: 2px;
  animation: grow 0.9s var(--ease-out) both;
  animation-delay: calc(var(--i) * 40ms + 150ms);
  transition: width 0.6s var(--ease-out);
}

.bar__fill--pos {
  left: 50%;
  transform-origin: left;
  background: linear-gradient(90deg, rgba(31, 224, 138, 0.35), var(--lucky));
}

.bar__fill--neg {
  right: 50%;
  transform-origin: right;
  background: linear-gradient(270deg, rgba(255, 59, 71, 0.35), var(--unlucky));
}

@keyframes grow {
  from {
    transform: scaleX(0);
  }
}

.value {
  text-align: right;
  font-size: 1.05rem;
  font-weight: 700;
}

.col-value {
  text-align: right;
}

.empty {
  margin: 0;
  padding: 2rem;
  text-align: center;
  color: var(--text-muted);
}

/* List animations: rows slide in, and re-ordering glides (FLIP) like a live timing tower */
.tower-enter-active {
  transition:
    opacity 0.5s var(--ease-out),
    transform 0.5s var(--ease-out);
  transition-delay: calc(var(--i) * 35ms);
}

.tower-enter-from {
  opacity: 0;
  transform: translateX(-24px);
}

.tower-move {
  transition: transform 0.7s var(--ease-out);
}

.tower-leave-active {
  display: none;
}

@media (prefers-reduced-motion: reduce) {
  .number__digits {
    animation: none;
  }
}

/* Narrow screens: one line per row with only the name and the value. The tag column and
   the luck bar are left to wider screens. */
@media (max-width: 720px) {
  .tower__head,
  .row {
    gap: 0.35rem 0.75rem;
    padding: 0 0.75rem;
  }

  .tower__head {
    grid-template-columns: 2.5rem 40px minmax(0, 1fr) auto;
  }

  .tower__head--plain {
    grid-template-columns: 40px minmax(0, 1fr) auto;
  }

  .col-bar,
  .col-tag {
    display: none;
  }

  .row {
    grid-template-columns: 2.5rem 40px minmax(0, 1fr) auto;
    padding-block: 0.6rem;
  }

  .row--plain {
    grid-template-columns: 40px minmax(0, 1fr) auto;
  }

  .who {
    gap: 0.6rem;
  }
}

/* Phones: smaller logo and position, and no car number or driver code, so the full name fits */
@media (max-width: 560px) {
  .tower__head,
  .row {
    gap: 0.35rem 0.6rem;
    padding-inline: 0.7rem;
  }

  .tower__head {
    grid-template-columns: 1.9rem 30px minmax(0, 1fr) auto;
  }

  .tower__head--plain {
    grid-template-columns: 30px minmax(0, 1fr) auto;
  }

  .row {
    min-height: 58px;
    padding-block: 0.55rem;
    grid-template-columns: 1.9rem 30px minmax(0, 1fr) auto;
  }

  .row--plain {
    grid-template-columns: 30px minmax(0, 1fr) auto;
  }

  .pos {
    width: 1.75rem;
    height: 1.75rem;
    font-size: 0.92rem;
  }

  .badge {
    width: 30px;
    height: 30px;
  }

  .badge__logo {
    width: 30px;
    height: 30px;
  }

  .who {
    gap: 0.5rem;
  }

  .number,
  .code--driver {
    display: none;
  }

  .code {
    min-width: 2.4rem;
    font-size: 0.92rem;
  }

  .flag {
    width: 24px;
    height: 16px;
    border-radius: 2px;
  }

  .names {
    gap: 0.1rem;
  }

  .title {
    font-size: 0.95rem;
  }

  .subtitle {
    font-size: 0.76rem;
  }

  .value {
    font-size: 0.95rem;
  }
}
</style>
