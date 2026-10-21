<script setup lang="ts">
defineProps<{ message: string }>()
const emit = defineEmits<{ retry: [] }>()
</script>

<template>
  <div class="red-flag card" role="alert">
    <!-- Flag icon: pole + waving cloth, both in the same reserved block -->
    <div class="flag" aria-hidden="true">
      <div class="flag__pole" />
      <div class="flag__cloth" />
    </div>

    <div class="body">
      <p class="title">RED FLAG</p>
      <p class="message">{{ message }}</p>
      <button type="button" class="retry" @click="emit('retry')">Restart session</button>
    </div>
  </div>
</template>

<style scoped>
.red-flag {
  display: flex;
  gap: 1.5rem;
  align-items: flex-start;
  padding: 1.5rem;
  border-color: rgba(225, 6, 0, 0.45);
  background: linear-gradient(135deg, rgba(225, 6, 0, 0.12), transparent 60%), var(--bg-elev);
}

/* Flag: pole + cloth laid out with flex so the cloth never bleeds over the text */
.flag {
  flex: none;
  display: flex;
  align-items: flex-start;
  gap: 0;
  padding-top: 3px;
}

.flag__pole {
  width: 4px;
  height: 52px;
  background: #ccc;
  border-radius: 2px;
  flex-shrink: 0;
}

.flag__cloth {
  width: 34px;
  height: 22px;
  background: var(--f1-red);
  transform-origin: left;
  animation: wave 1.6s ease-in-out infinite;
}

@keyframes wave {
  50% {
    transform: skewY(5deg) scaleX(0.88);
  }
}

.body {
  flex: 1;
  min-width: 0;
}

.title {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 900;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: var(--f1-red);
}

.message {
  margin: 0.4rem 0 1.1rem;
  line-height: 1.55;
  color: var(--text-muted);
}

.retry {
  padding: 0.55rem 1.2rem;
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #fff;
  background: var(--f1-red);
  border: 0;
  cursor: pointer;
  clip-path: polygon(8px 0, 100% 0, calc(100% - 8px) 100%, 0 100%);
  transition: background 0.2s;
}

.retry:hover {
  background: var(--f1-red-dark);
}
</style>
