<script setup lang="ts">
withDefaults(
  defineProps<{
    label: string
    value: string
    hint?: string
    tone?: string
  }>(),
  { hint: '', tone: '' },
)
</script>

<template>
  <div class="tile card">
    <span class="label">{{ label }}</span>
    <span class="value num" :class="tone">{{ value }}</span>
    <span v-if="hint" class="hint">{{ hint }}</span>
  </div>
</template>

<style scoped>
.tile {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  padding: 1rem 1.1rem;
  overflow: hidden;
}

.tile::after {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: 42px;
  height: 3px;
  background: var(--f1-red);
  transform: skewX(var(--skew));
  transform-origin: top right;
}

.label {
  font-size: 0.7rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.value {
  font-size: clamp(1.4rem, 3.5vw, 1.9rem);
  font-weight: 900;
  line-height: 1.1;
}

.hint {
  overflow: hidden;
  font-size: 0.8rem;
  color: var(--text-muted);
  white-space: nowrap;
  text-overflow: ellipsis;
}
</style>
