<template>
  <header class="site-header">
    <div class="container site-header__inner">
      <RouterLink :to="{ name: 'leaderboard' }" class="brand" aria-label="Free Stop home">
        <span class="brand__mark">FS</span>
        <span class="brand__text">Free <strong>Stop</strong></span>
      </RouterLink>
      <nav class="nav" aria-label="Main">
        <RouterLink :to="{ name: 'leaderboard' }" class="nav__link">Standings</RouterLink>
        <RouterLink :to="{ name: 'methodology' }" class="nav__link">How it works</RouterLink>
      </nav>
    </div>
  </header>

  <main class="container site-main">
    <RouterView v-slot="{ Component, route }">
      <Transition name="page" mode="out-in">
        <component :is="Component" :key="route.path" />
      </Transition>
    </RouterView>
  </main>

  <footer class="site-footer">
    <div class="chequered" />
    <div class="container site-footer__inner">
      <span>Data from <a href="https://openf1.org" target="_blank" rel="noopener">OpenF1</a></span>
      <span>Unofficial fan project — not affiliated with Formula 1.</span>
    </div>
  </footer>
</template>

<style scoped>
.site-header {
  position: sticky;
  top: 0;
  z-index: 10;
  border-top: 3px solid var(--f1-red);
  background: rgba(11, 11, 16, 0.78);
  backdrop-filter: blur(14px) saturate(140%);
  border-bottom: 1px solid var(--line);
}

.site-header__inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 64px;
  gap: 1rem;
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.brand__mark {
  display: grid;
  place-items: center;
  height: 30px;
  padding: 0 0.7rem 0 0.6rem;
  font-size: 0.95rem;
  font-weight: 900;
  font-style: italic;
  letter-spacing: 0.04em;
  color: #fff;
  background: var(--f1-red);
  clip-path: polygon(8px 0, 100% 0, calc(100% - 8px) 100%, 0 100%);
  transition: transform 0.35s var(--ease-out);
}

.brand:hover .brand__mark {
  transform: translateX(3px) skewX(-6deg);
}

.brand__text {
  font-size: 1.05rem;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.brand__text strong {
  font-weight: 900;
}

.nav {
  display: flex;
  gap: clamp(0.75rem, 3vw, 2rem);
}

.nav__link {
  position: relative;
  padding: 0.4rem 0;
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--text-muted);
  transition: color 0.2s;
}

.nav__link::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: -2px;
  height: 3px;
  background: var(--f1-red);
  transform: scaleX(0);
  transform-origin: left;
  transition: transform 0.35s var(--ease-out);
}

.nav__link:hover,
.nav__link.router-link-exact-active {
  color: var(--text);
}

.nav__link:hover::after,
.nav__link.router-link-exact-active::after {
  transform: scaleX(1);
}

.site-main {
  min-height: calc(100vh - 64px - 120px);
  padding-top: clamp(1.5rem, 5vw, 3rem);
  padding-bottom: 4rem;
}

.site-footer {
  margin-top: 2rem;
  border-top: 1px solid var(--line);
}

.site-footer__inner {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 0.5rem 2rem;
  padding-top: 1.25rem;
  padding-bottom: 1.5rem;
  font-size: 0.8rem;
  color: var(--text-dim);
}

.site-footer a {
  color: var(--text-muted);
  text-decoration: underline;
  text-underline-offset: 3px;
}

@media (max-width: 560px) {
  .brand__text {
    display: none;
  }
}
</style>
