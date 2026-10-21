<script setup lang="ts">
withDefaults(defineProps<{ label?: string; detail?: string }>(), {
  label: 'Lights out in a moment',
  detail: '',
})
</script>

<template>
  <div class="start" role="status" aria-live="polite">
    <div class="gantry" aria-hidden="true">
      <div v-for="n in 5" :key="n" class="pod" :style="{ '--n': n }">
        <span class="lamp lamp--off" />
        <span class="lamp lamp--red" />
      </div>
    </div>
    <p class="label">{{ label }}<span class="dots" /></p>
    <p v-if="detail" class="detail">{{ detail }}</p>
  </div>
</template>

<style scoped>
.start {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: clamp(2rem, 6vw, 3.5rem) 1rem;
  text-align: center;
}

.gantry {
  display: flex;
  gap: clamp(0.4rem, 1.5vw, 0.8rem);
  padding: 0.75rem clamp(0.6rem, 2vw, 1rem);
  background: #050507;
  border: 1px solid var(--line-strong);
  border-radius: 10px;
  box-shadow: inset 0 2px 12px rgba(0, 0, 0, 0.8);
}

.pod {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  padding: 0.5rem;
  background: #111117;
  border-radius: 8px;
}

.lamp {
  width: clamp(18px, 5vw, 28px);
  aspect-ratio: 1;
  border-radius: 50%;
  background: #23232b;
  box-shadow: inset 0 -3px 6px rgba(0, 0, 0, 0.6);
}

/* Each red lamp comes on half a second after the previous one; all go out together. */
.lamp--red {
  animation: 4s infinite linear;
}
.pod:nth-child(1) .lamp--red {
  animation-name: light-1;
}
.pod:nth-child(2) .lamp--red {
  animation-name: light-2;
}
.pod:nth-child(3) .lamp--red {
  animation-name: light-3;
}
.pod:nth-child(4) .lamp--red {
  animation-name: light-4;
}
.pod:nth-child(5) .lamp--red {
  animation-name: light-5;
}

@keyframes light-1 {
  0%,
  4% {
    background: #23232b;
    box-shadow: none;
  }
  5%,
  74% {
    background: var(--f1-red);
    box-shadow: 0 0 18px 4px var(--f1-red-glow);
  }
  75%,
  100% {
    background: #23232b;
    box-shadow: none;
  }
}
@keyframes light-2 {
  0%,
  16% {
    background: #23232b;
    box-shadow: none;
  }
  17%,
  74% {
    background: var(--f1-red);
    box-shadow: 0 0 18px 4px var(--f1-red-glow);
  }
  75%,
  100% {
    background: #23232b;
    box-shadow: none;
  }
}
@keyframes light-3 {
  0%,
  29% {
    background: #23232b;
    box-shadow: none;
  }
  30%,
  74% {
    background: var(--f1-red);
    box-shadow: 0 0 18px 4px var(--f1-red-glow);
  }
  75%,
  100% {
    background: #23232b;
    box-shadow: none;
  }
}
@keyframes light-4 {
  0%,
  41% {
    background: #23232b;
    box-shadow: none;
  }
  42%,
  74% {
    background: var(--f1-red);
    box-shadow: 0 0 18px 4px var(--f1-red-glow);
  }
  75%,
  100% {
    background: #23232b;
    box-shadow: none;
  }
}
@keyframes light-5 {
  0%,
  54% {
    background: #23232b;
    box-shadow: none;
  }
  55%,
  74% {
    background: var(--f1-red);
    box-shadow: 0 0 18px 4px var(--f1-red-glow);
  }
  75%,
  100% {
    background: #23232b;
    box-shadow: none;
  }
}

.label {
  margin: 1.5rem 0 0;
  font-size: 0.85rem;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.dots::after {
  content: '';
  animation: dots 1.2s steps(4) infinite;
}

@keyframes dots {
  0% {
    content: '';
  }
  25% {
    content: '.';
  }
  50% {
    content: '..';
  }
  75% {
    content: '...';
  }
}

.detail {
  margin: 0.4rem 0 0;
  font-size: 0.85rem;
  color: var(--text-muted);
}
</style>
