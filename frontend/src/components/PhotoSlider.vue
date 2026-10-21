<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import type { RacePhotos } from '@/types/api'
import { formatDate } from '@/utils/format'

const props = defineProps<{ gallery: RacePhotos; year: string }>()

const ADVANCE_MS = 5000

const index = ref(0)
const paused = ref(false)
const photos = computed(() => props.gallery.photos)
const current = computed(() => photos.value[index.value])

const heading = computed(() =>
  props.gallery.scope === 'weekend'
    ? `From the ${props.year} race weekend`
    : 'From this Grand Prix in other years',
)

function go(step: number): void {
  const n = photos.value.length
  index.value = (index.value + step + n) % n
}

let timer: ReturnType<typeof setInterval> | undefined
const reducedMotion =
  typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches

function restart(): void {
  clearInterval(timer)
  if (!reducedMotion && photos.value.length > 1) {
    timer = setInterval(() => !paused.value && go(1), ADVANCE_MS)
  }
}

onMounted(restart)
watch(photos, () => {
  index.value = 0
  restart()
})
onBeforeUnmount(() => clearInterval(timer))
</script>

<template>
  <figure
    class="slider card"
    @mouseenter="paused = true"
    @mouseleave="paused = false"
    @focusin="paused = true"
    @focusout="paused = false"
  >
    <div class="slider__frame">
      <TransitionGroup name="fade">
        <img
          v-for="(photo, i) in photos"
          v-show="i === index"
          :key="photo.url"
          class="slider__photo"
          :src="photo.url"
          :alt="photo.caption"
          :loading="i === 0 ? 'eager' : 'lazy'"
          decoding="async"
        />
      </TransitionGroup>

      <span class="slider__tag">{{ heading }}</span>

      <template v-if="photos.length > 1">
        <button type="button" class="nav nav--prev" aria-label="Previous photo" @click="go(-1)">
          <span aria-hidden="true">‹</span>
        </button>
        <button type="button" class="nav nav--next" aria-label="Next photo" @click="go(1)">
          <span aria-hidden="true">›</span>
        </button>
        <div class="dots" role="tablist" aria-label="Photos">
          <button
            v-for="(photo, i) in photos"
            :key="photo.url"
            type="button"
            class="dot"
            :class="{ 'dot--active': i === index }"
            role="tab"
            :aria-selected="i === index"
            :aria-label="`Photo ${i + 1}`"
            @click="index = i"
          />
        </div>
      </template>
    </div>

    <figcaption v-if="current" class="slider__credit">
      <span class="slider__caption">
        {{ current.caption
        }}<template v-if="current.taken"> · {{ formatDate(current.taken) }}</template>
      </span>
      <a :href="current.page_url" target="_blank" rel="noopener">
        Photo: {{ current.author }} · {{ current.license }} · Wikimedia Commons
      </a>
    </figcaption>
  </figure>
</template>

<style scoped>
/* The frame keeps 16:9 on its own, but grows to fill a taller space it is stretched into */
.slider {
  display: flex;
  flex-direction: column;
  margin: 0;
  overflow: hidden;
}

.slider__frame {
  position: relative;
  flex: 1 1 auto;
  min-height: 220px;
  aspect-ratio: 16 / 9;
  background: #000;
}

.slider__photo {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.9s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* Keep controls readable over bright photos */
.slider__frame::after {
  content: '';
  position: absolute;
  inset: auto 0 0;
  height: 38%;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.6), transparent);
  pointer-events: none;
}

.slider__tag {
  position: absolute;
  top: 0.7rem;
  left: 0.7rem;
  z-index: 1;
  padding: 0.25rem 0.7rem;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #fff;
  background: rgba(11, 11, 16, 0.75);
  border-left: 3px solid var(--f1-red);
  backdrop-filter: blur(4px);
}

.nav {
  position: absolute;
  top: 50%;
  z-index: 2;
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  padding: 0;
  font-size: 1.5rem;
  line-height: 1;
  color: #fff;
  background: rgba(11, 11, 16, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  cursor: pointer;
  opacity: 0;
  transform: translateY(-50%);
  transition:
    opacity 0.25s,
    background 0.2s,
    border-color 0.2s;
}

.nav span {
  margin-top: -3px;
}

.nav--prev {
  left: 0.6rem;
}

.nav--next {
  right: 0.6rem;
}

.slider:hover .nav,
.nav:focus-visible {
  opacity: 1;
}

.nav:hover {
  background: var(--f1-red);
  border-color: var(--f1-red);
}

.dots {
  position: absolute;
  bottom: 0.7rem;
  left: 50%;
  z-index: 2;
  display: flex;
  gap: 0.35rem;
  transform: translateX(-50%);
}

.dot {
  width: 8px;
  height: 8px;
  padding: 0;
  background: rgba(255, 255, 255, 0.45);
  border: 0;
  border-radius: 4px;
  cursor: pointer;
  transition:
    width 0.3s var(--ease-out),
    background 0.2s;
}

.dot--active {
  width: 22px;
  background: var(--f1-red);
}

.slider__credit {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  padding: 0.6rem 0.8rem 0.7rem;
  font-size: 0.75rem;
}

.slider__caption {
  overflow: hidden;
  font-weight: 600;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.slider__credit a {
  overflow: hidden;
  color: var(--text-dim);
  white-space: nowrap;
  text-overflow: ellipsis;
}

.slider__credit a:hover {
  color: var(--text);
  text-decoration: underline;
}

@media (hover: none) {
  .nav {
    opacity: 1;
  }
}
</style>
