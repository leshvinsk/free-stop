import { createRouter, createWebHistory, type LocationQuery } from 'vue-router'
import { CURRENT_SEASON, FIRST_SEASON } from '@/utils/format'

function seasonFrom(query: LocationQuery): number {
  const year = Number(query.year)
  return Number.isInteger(year) && year >= FIRST_SEASON && year <= CURRENT_SEASON
    ? year
    : CURRENT_SEASON
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  scrollBehavior: (to, _from, saved) => {
    if (saved) return saved
    if (to.hash) {
      // The target element may not exist yet (data still loading).
      // Poll briefly so hash scrolls work after async content renders.
      return new Promise((resolve) => {
        const attempt = (tries: number) => {
          const el = document.querySelector(to.hash)
          if (el) {
            resolve({ el: to.hash, behavior: 'smooth', top: 80 })
          } else if (tries > 0) {
            setTimeout(() => attempt(tries - 1), 120)
          } else {
            resolve({ top: 0 })
          }
        }
        attempt(25) // up to ~3 seconds
      })
    }
    return { top: 0 }
  },
  routes: [
    {
      path: '/',
      name: 'leaderboard',
      component: () => import('@/views/LeaderboardView.vue'),
      props: (route) => ({ year: seasonFrom(route.query) }),
    },
    {
      path: '/race/:sessionKey',
      name: 'race',
      component: () => import('@/views/RaceView.vue'),
      props: (route) => ({ sessionKey: Number(route.params.sessionKey) }),
    },
    {
      path: '/driver/:driverNumber',
      name: 'driver',
      component: () => import('@/views/DriverView.vue'),
      props: (route) => ({
        driverNumber: Number(route.params.driverNumber),
        year: seasonFrom(route.query),
      }),
    },
    {
      path: '/team/:teamKey',
      name: 'team',
      component: () => import('@/views/TeamView.vue'),
      props: (route) => ({ teamKey: String(route.params.teamKey), year: seasonFrom(route.query) }),
    },
    {
      path: '/methodology',
      name: 'methodology',
      component: () => import('@/views/MethodologyView.vue'),
    },
    { path: '/:pathMatch(.*)*', redirect: { name: 'leaderboard' } },
  ],
})

export default router
