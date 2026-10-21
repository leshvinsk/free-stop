<script setup lang="ts">
withDefaults(defineProps<{ rows?: number }>(), { rows: 10 })
</script>

<template>
  <div class="skeleton card" aria-hidden="true">
    <div v-for="n in rows" :key="n" class="row" :style="{ '--i': n }">
      <span class="bone bone--pos" />
      <span class="bone bone--bar" />
      <span class="bone bone--code" />
      <span class="bone bone--name" />
      <span class="bone bone--luck" />
    </div>
  </div>
</template>

<style scoped>
.skeleton {
  overflow: hidden;
}

.row {
  display: grid;
  grid-template-columns: 2.5rem 4px 3.5rem 1fr 5rem;
  align-items: center;
  gap: 1rem;
  height: 56px;
  padding: 0 1rem;
  border-bottom: 1px solid var(--line);
  opacity: calc(1 - var(--i) * 0.07);
}

.bone {
  height: 14px;
  border-radius: 3px;
  background: linear-gradient(90deg, var(--bg-elev-2) 0%, #2b2b37 40%, var(--bg-elev-2) 80%);
  background-size: 300% 100%;
  animation: shimmer 1.4s ease-in-out infinite;
  animation-delay: calc(var(--i) * 60ms);
}

.bone--pos {
  width: 1.5rem;
  height: 18px;
}
.bone--bar {
  width: 4px;
  height: 28px;
}
.bone--code {
  width: 3rem;
  height: 16px;
}
.bone--name {
  width: min(60%, 220px);
}
.bone--luck {
  width: 4rem;
  justify-self: end;
  height: 18px;
}

@keyframes shimmer {
  from {
    background-position: 100% 0;
  }
  to {
    background-position: -50% 0;
  }
}
</style>
