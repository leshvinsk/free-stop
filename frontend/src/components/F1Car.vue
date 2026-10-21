<script setup lang="ts">
// Top-down F1 car, nose pointing right. Carbon-black with white livery so it reads clearly
// against the red progress fill.
const id = `car-${Math.random().toString(36).slice(2, 8)}`
</script>

<template>
  <svg viewBox="0 0 120 44" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <defs>
      <!-- Rounded bodywork: lighter along the spine, darker at the edges -->
      <linearGradient :id="`${id}-body`" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#1a1a22" />
        <stop offset="0.5" stop-color="#3b3b46" />
        <stop offset="1" stop-color="#121218" />
      </linearGradient>
      <linearGradient :id="`${id}-tyre`" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#2b2b2f" />
        <stop offset="0.5" stop-color="#050506" />
        <stop offset="1" stop-color="#2b2b2f" />
      </linearGradient>
      <radialGradient :id="`${id}-helmet`" cx="0.35" cy="0.35" r="0.7">
        <stop offset="0" stop-color="#ffffff" />
        <stop offset="1" stop-color="#ffd60a" />
      </radialGradient>
    </defs>

    <!-- Rear wing: main plane, DRS flap, endplates -->
    <rect x="2" y="7" width="10" height="30" rx="1.5" fill="#0d0d12" />
    <rect x="3.5" y="8" width="2" height="28" fill="#f5f5f7" opacity="0.9" />
    <rect x="2" y="6" width="10" height="2.5" rx="1" fill="#e10600" />
    <rect x="2" y="35.5" width="10" height="2.5" rx="1" fill="#e10600" />

    <!-- Rear tyres -->
    <g :fill="`url(#${id}-tyre)`">
      <rect x="16" y="1" width="21" height="10" rx="3.5" />
      <rect x="16" y="33" width="21" height="10" rx="3.5" />
    </g>
    <g stroke="#55555f" stroke-width="0.6" opacity="0.8">
      <line x1="17.5" y1="3.2" x2="35.5" y2="3.2" />
      <line x1="17.5" y1="40.8" x2="35.5" y2="40.8" />
    </g>

    <!-- Wishbones -->
    <g stroke="#6b6b76" stroke-width="1" stroke-linecap="round">
      <path d="M28 11 L42 17 M24 11 L40 19" />
      <path d="M28 33 L42 27 M24 33 L40 25" />
      <path d="M93 11 L82 18.5 M97 11 L86 19.5" />
      <path d="M93 33 L82 25.5 M97 33 L86 24.5" />
    </g>

    <!-- Floor -->
    <path d="M14 14 C30 10 58 9 76 13.5 L76 30.5 C58 35 30 34 14 30 Z" fill="#08080b" />

    <!-- Sidepods with inlets -->
    <path
      d="M40 11.5 C52 8 66 8.5 73 13 L73 31 C66 35.5 52 36 40 32.5 C36.5 26 36.5 18 40 11.5 Z"
      :fill="`url(#${id}-body)`"
    />
    <path d="M70 12.5 C72 13 73 14 73 15.5 L67 15.5 Z" fill="#000" />
    <path d="M70 31.5 C72 31 73 30 73 28.5 L67 28.5 Z" fill="#000" />

    <!-- Chassis, engine cover and nose -->
    <path
      d="M12 17.5 L40 15.5 C60 14.5 74 15.5 84 17.8 L104 20.4 L115 21.4 Q117.5 22 115 22.6 L104 23.6 L84 26.2 C74 28.5 60 29.5 40 28.5 L12 26.5 Z"
      :fill="`url(#${id}-body)`"
    />
    <!-- Livery: white spine stripe with a red pinstripe -->
    <path
      d="M14 20.6 L64 20.2 C80 20.4 96 21 112 21.6 L112 22.4 C96 23 80 23.6 64 23.8 L14 23.4 Z"
      fill="#f5f5f7"
    />
    <path d="M18 21.7 L108 21.85 L108 22.15 L18 22.3 Z" fill="#e10600" />
    <!-- Shark fin -->
    <path d="M14 21.2 L44 21.6 L44 22.4 L14 22.8 Z" fill="#0d0d12" opacity="0.6" />

    <!-- Cockpit, halo, helmet -->
    <ellipse cx="74" cy="22" rx="7.5" ry="3.8" fill="#000" />
    <circle cx="73" cy="22" r="2.8" :fill="`url(#${id}-helmet)`" />
    <path
      d="M67 22 C70 17 78 17 81.5 22 C78 27 70 27 67 22 M81.5 22 L85 22"
      fill="none"
      stroke="#8a8a96"
      stroke-width="1.1"
    />

    <!-- Front tyres -->
    <g :fill="`url(#${id}-tyre)`">
      <rect x="88" y="3" width="15" height="8.5" rx="3" />
      <rect x="88" y="32.5" width="15" height="8.5" rx="3" />
    </g>

    <!-- Front wing: swept elements and endplates -->
    <path d="M106 5 L111 6.5 L111 37.5 L106 39 Z" fill="#0d0d12" />
    <path d="M110.5 6.5 L114 8.5 L114 35.5 L110.5 37.5 Z" fill="#f5f5f7" opacity="0.9" />
    <rect x="105" y="4" width="10" height="2.4" rx="1" fill="#e10600" />
    <rect x="105" y="37.6" width="10" height="2.4" rx="1" fill="#e10600" />
  </svg>
</template>
