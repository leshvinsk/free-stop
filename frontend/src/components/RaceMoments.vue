<script setup lang="ts">
import { RouterLink } from 'vue-router'
import type { Story, StoryKind } from '@/utils/stories'
import { formatLuck, teamColour } from '@/utils/format'

defineProps<{ stories: Story[]; year: string }>()

const LABEL: Record<StoryKind, string> = {
  lucky: 'Lucky stop',
  missed: 'Missed out',
  penalty: 'Penalty',
  crew: 'Pit crew',
}
</script>

<template>
  <ol class="moments">
    <li
      v-for="(story, i) in stories"
      :key="story.key"
      class="moment card rise"
      :class="`moment--${story.kind}`"
      :style="{ '--i': i + 1, '--team': teamColour(story.driver.team_colour) }"
    >
      <div class="moment__top">
        <span class="moment__kind">{{ LABEL[story.kind] }}</span>
        <span class="moment__value num" :class="story.value >= 0 ? 'lucky' : 'unlucky'">
          {{ formatLuck(story.value) }}
        </span>
      </div>
      <RouterLink
        class="moment__headline"
        :to="{
          name: 'driver',
          params: { driverNumber: story.driver.driver_number },
          query: { year },
        }"
      >
        {{ story.headline }}
      </RouterLink>
      <p class="moment__detail">{{ story.detail }}</p>
    </li>
  </ol>
</template>

<style scoped>
.moments {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(100%, 280px), 1fr));
  gap: 0.75rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.moment {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1rem 1.1rem 1.1rem 1.3rem;
  border-left: 4px solid var(--team);
  transition:
    transform 0.25s var(--ease-out),
    border-color 0.25s;
}

.moment:hover {
  transform: translateY(-3px);
}

.moment__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.moment__kind {
  padding: 0.2rem 0.65rem;
  font-size: 0.65rem;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  clip-path: polygon(8% 0, 100% 0, 92% 100%, 0 100%);
  background: var(--bg-elev-2);
  color: var(--text-muted);
}

.moment--lucky .moment__kind {
  background: color-mix(in srgb, var(--lucky) 18%, transparent);
  color: var(--lucky);
}

.moment--missed .moment__kind {
  background: color-mix(in srgb, var(--unlucky) 18%, transparent);
  color: var(--unlucky);
}

.moment--penalty .moment__kind {
  background: color-mix(in srgb, var(--yellow) 16%, transparent);
  color: var(--yellow);
}

.moment__value {
  font-size: 1.35rem;
  font-weight: 900;
}

.moment__headline {
  font-size: 1.05rem;
  font-weight: 700;
  line-height: 1.3;
  color: var(--text);
  text-decoration: none;
}

.moment__headline:hover {
  text-decoration: underline;
  text-decoration-color: var(--team);
  text-underline-offset: 3px;
}

.moment__detail {
  margin: 0;
  font-size: 0.85rem;
  line-height: 1.55;
  color: var(--text-muted);
}
</style>
