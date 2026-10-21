<script setup lang="ts">
import { ref } from 'vue'
import { formatFullName } from '@/utils/format'
import type { Story, StoryKind } from '@/utils/stories'

defineProps<{ stories: Story[]; year: string }>()

const brokenHeadshots = ref(new Set<string>())

const LABEL: Record<StoryKind, string> = {
  lucky: 'LUCKY',
  missed: 'MISSED',
  penalty: 'PENALTY',
  crew: 'SLOW PIT',
}

function valueLabel(story: Story): string {
  const abs = Math.abs(story.value).toFixed(3)
  return story.value > 0 ? `+${abs}s` : `−${abs}s`
}

/** Strip the leading "CODE " from the headline — all headlines start with the acronym */
function action(story: Story): string {
  const prefix = story.driver.name_acronym + ' '
  return story.headline.startsWith(prefix) ? story.headline.slice(prefix.length) : story.headline
}
</script>

<template>
  <div class="highlights">
    <div class="highlights__header">
      <span class="highlights__title">Race highlights</span>
    </div>

    <div v-if="!stories.length" class="highlights__empty">
      No standout pit-stop moments this race
    </div>

    <ul v-else class="highlights__list">
      <li v-for="story in stories" :key="story.key" class="moment" :class="`moment--${story.kind}`">
        <span class="moment__kind">{{ LABEL[story.kind] }}</span>
        <RouterLink
          class="moment__body"
          :to="{
            name: 'driver',
            params: { driverNumber: story.driver.driver_number },
            query: { year },
          }"
        >
          <img
            v-if="story.driver.headshot_url && !brokenHeadshots.has(story.driver.headshot_url)"
            class="moment__portrait"
            :src="story.driver.headshot_url"
            :alt="story.driver.full_name"
            loading="lazy"
            @error="brokenHeadshots = new Set(brokenHeadshots).add(story.driver.headshot_url)"
          />
          <div class="moment__content">
            <div class="moment__head">
              <div class="moment__text">
                <span class="moment__driver num">{{ story.driver.name_acronym }}</span>
                {{ ' '
                }}<span class="moment__name">{{ formatFullName(story.driver.full_name) }}</span>
                {{ ' ' }}<span class="moment__action">{{ action(story) }}</span>
              </div>
              <span class="moment__value num" :class="story.value >= 0 ? 'lucky' : 'unlucky'">{{
                valueLabel(story)
              }}</span>
            </div>
            <p class="moment__detail">{{ story.detail }}</p>
          </div>
        </RouterLink>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.highlights {
  display: flex;
  flex-direction: column;
  margin-top: 1.5rem;
}

.highlights__header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.65rem;
}

.highlights__title {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.highlights__title::before {
  content: '';
  display: inline-block;
  width: 14px;
  height: 3px;
  margin-right: 0.6rem;
  background: var(--f1-red);
  transform: skewX(-12deg);
  vertical-align: middle;
}

.highlights__empty {
  padding: 1.2rem 1rem;
  font-size: 0.85rem;
  color: var(--text-muted);
  background: var(--bg-elev);
  border: 1px solid var(--line);
  border-radius: var(--radius);
}

.highlights__list {
  display: flex;
  flex-direction: column;
  gap: 0;
  margin: 0;
  padding: 0;
  list-style: none;
  border: 1px solid var(--line);
  border-radius: var(--radius);
  overflow: hidden;
}

.moment {
  display: flex;
  gap: 0;
  background: var(--bg-elev);
  border-bottom: 1px solid var(--line);
}

.moment:last-child {
  border-bottom: none;
}

.moment__kind {
  display: flex;
  align-items: center;
  justify-content: center;
  writing-mode: vertical-rl;
  text-orientation: mixed;
  padding: 0.65rem 0.4rem;
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #fff;
  min-width: 28px;
  flex-shrink: 0;
}

.moment--lucky .moment__kind {
  background: #1fe08a;
  color: #041a0e;
}

.moment--missed .moment__kind {
  background: #ff3b47;
  color: #1a0003;
}

.moment--penalty .moment__kind {
  background: #ffd60a;
  color: #1a1500;
}

.moment--crew .moment__kind {
  background: #b14dff;
  color: #0f0020;
}

.moment__body {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.65rem 0.85rem;
  min-width: 0;
  text-decoration: none;
  color: inherit;
  transition: background 0.2s;
  cursor: pointer;
}

.moment__body:hover {
  background: var(--bg-elev-2);
}

.moment__content {
  flex: 1;
  min-width: 0;
}

.moment__head {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.moment__portrait {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  object-fit: cover;
  object-position: center center;
  flex-shrink: 0;
  align-self: center;
  border: 1px solid var(--line-strong);
}

.moment__text {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.moment__driver {
  font-size: 0.85rem;
  font-weight: 700;
  letter-spacing: 0.06em;
}

.moment__name {
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--text-dim);
}

.moment__action {
  font-size: 0.78rem;
  font-weight: 500;
  color: var(--text-muted);
}

.moment__value {
  font-size: 0.95rem;
  font-weight: 700;
  flex-shrink: 0;
  margin-left: auto;
}

.moment__detail {
  margin: 0.2rem 0 0;
  font-size: 0.73rem;
  line-height: 1.5;
  color: var(--text-muted);
  white-space: pre-line;
}
</style>
