<script setup lang="ts">
import { computed } from 'vue'
import { CURRENT_SEASON, FIRST_SEASON } from '@/utils/format'

/** `options` limits the choice, e.g. to the seasons a team raced. */
const props = defineProps<{ modelValue: number; options?: number[] }>()
const emit = defineEmits<{ 'update:modelValue': [year: number] }>()

const years = computed(() =>
  props.options
    ? [...props.options].sort((a, b) => b - a)
    : Array.from({ length: CURRENT_SEASON - FIRST_SEASON + 1 }, (_, i) => CURRENT_SEASON - i),
)
</script>

<template>
  <div class="years" role="radiogroup" aria-label="Season">
    <button
      v-for="y in years"
      :key="y"
      type="button"
      role="radio"
      class="year num"
      :class="{ 'year--active': y === modelValue }"
      :aria-checked="y === modelValue"
      @click="emit('update:modelValue', y)"
    >
      {{ y }}
    </button>
  </div>
</template>

<style scoped>
.years {
  display: inline-flex;
  gap: 0.35rem;
  padding: 0.3rem;
  background: var(--bg-elev);
  border: 1px solid var(--line);
  border-radius: var(--radius);
}

.year {
  padding: 0.45rem 0.95rem;
  font-size: 0.9rem;
  font-weight: 700;
  color: var(--text-muted);
  background: transparent;
  border: 0;
  cursor: pointer;
  clip-path: polygon(6px 0, 100% 0, calc(100% - 6px) 100%, 0 100%);
  transition:
    color 0.2s,
    background 0.25s var(--ease-out);
}

.year:hover {
  color: var(--text);
  background: var(--bg-elev-2);
}

.year--active,
.year--active:hover {
  color: #fff;
  background: var(--f1-red);
}
</style>
