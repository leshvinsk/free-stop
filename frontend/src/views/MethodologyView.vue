<script setup lang="ts">
// A tour of the site, in the order a visitor meets it
const guide = [
  {
    where: 'Standings',
    title: 'Start with the season',
    body: 'Every driver is ranked by the time their pit stop timing saved them per race. Green means the timing helped them, red means it cost them. It is an average, so a stand-in with a handful of races is compared fairly with a full-season driver.',
    points: [
      'Luckiest and unluckiest need at least a third of the season (and three races) to qualify.',
      'Pick 2024, 2025 or 2026 from the season switcher.',
    ],
  },
  {
    where: 'Race page',
    title: 'Open a race to see why',
    body: 'Click any Grand Prix. The timeline shows when the safety cars and red flags came out, and every pit stop against them.',
    points: [
      'Race highlights pick out the big moments: who got lucky, who just missed out.',
      'Stop conditions shows how each stop was made, e.g. "1 x VSC" and "1 x GREEN", with a key above the table. That is why one driver saves 15 seconds and another loses them.',
      "Pit crew execution ranks the crews separately, with each crew's best stop.",
    ],
  },
  {
    where: 'Driver page',
    title: 'Follow a driver race by race',
    body: 'Each row is one Grand Prix: the time their timing saved on the right, what the pit crew saved in the middle, and a bar for how lucky or unlucky it was.',
    points: [
      'DNF, DNS or DSQ means the race ended early for them, so their timing is not scored and does not count in their season. Stops they completed still count for the crew.',
      'A dash under Crew saved means there was no normal stop to time, such as a tyre change under a red flag.',
    ],
  },
  {
    where: 'Team page',
    title: 'Compare the two cars',
    body: "A team's score is both drivers added together. Each race shows both drivers' scores side by side, and the pit crew cards show the team's average, best and worst races.",
    points: [
      'Teams that changed name keep one page: RB became Racing Bulls, Kick Sauber became Audi.',
    ],
  },
] as const

const steps = [
  {
    title: 'Measure what each stop really cost',
    body: 'The pit lane takes just as long under a safety car. What changes is that rivals are crawling round behind it. So we time the lap into the pits and the lap out, and compare them with what the rest of the field did at the same moments, matched to the second.',
    formula: 'time_lost = (in-lap + out-lap) − field pace over the same two laps',
  },
  {
    title: 'Take the pit crew out of it',
    body: "A stuck wheel nut is not bad luck, it is the crew. Time spent in the pit lane beyond the race's normal stop goes to the crew score instead. Penalties served at a stop are taken out of both.",
    formula:
      'crew = typical lane time − (lane time − penalty)\nstop_cost = time_lost − (lane time − typical lane time)',
  },
  {
    title: 'Compare with a normal stop',
    body: 'The normal stop is what a stop cost under green flags at that race (an average that ignores the odd outlier). Cost less and you were lucky, up to a completely free stop. That is the most anyone can save.',
    formula:
      'normal = trimmed average of fully green stops\nstop_luck = normal − max(0, stop_cost)',
  },
  {
    title: 'Charge the ones that just missed it',
    body: 'Pitting a lap or two before a safety car is the classic heartbreak: rivals stop for almost nothing and you paid full price. You are charged what they saved. A red flag lets everyone change tyres for free, so a stop just before one costs a whole stop. If most of the field got caught out the same way, nobody lost out and nothing is charged.',
    formula: 'missed = −(what rivals saved − your stop luck)',
  },
  {
    title: 'Compare with the rest of the field',
    body: "Luck is about rivals. If the whole field pits under the same safety car, nobody gained on anybody. So a driver's stops and near misses are added up, then the race's field average is taken away. Roughly half the grid ends up lucky and half unlucky.",
    formula: 'race_luck = Σ (stop_luck + missed) − field average',
  },
  {
    title: 'Leave out races that ended early',
    body: 'A retirement, a car that never started or a disqualification means there is no full race to judge. Those races show DNF, DNS or DSQ, carry no timing score and stay out of the field average and the season luck. The crew still did every stop made before the race ended, so those stops keep their crew score.',
    formula: 'DNF / DNS / DSQ → timing not scored, crew still scored',
  },
] as const

const labels = [
  [
    'LUCKY',
    'lucky',
    'Pitted under a safety car, VSC or red flag while rivals had paid full price.',
  ],
  ['MISSED', 'unlucky', 'Pitted just before a neutralisation and watched rivals stop for less.'],
  ['PENALTY', 'flag', 'A penalty was served at the stop. Counted separately, not as luck.'],
  ['SLOW PIT', 'crew', 'The crew took noticeably longer than a normal stop.'],
  [
    'DNF · DNS · DSQ',
    'muted',
    'Did not finish, did not start, or disqualified. Timing not scored; completed stops still count for the crew.',
  ],
  ['N/A', 'muted', 'No luck score for this race, usually because it ended early.'],
  ['—', 'muted', 'No crew time to measure, such as a tyre change under a red flag.'],
  ['No stops', 'muted', 'Ran the whole race without pitting.'],
  [
    'Estimated',
    'muted',
    'Every stop came under a neutralisation, so the normal stop is estimated.',
  ],
] as const

const limits = [
  [
    'Estimates, not stopwatches',
    "A stop's cost compares the driver's in-lap and out-lap with the rest of the field's pace at that moment. Traffic, fresh tyres and fuel load move that by fractions of a second, sometimes more. There is no official luck figure to check against, so the scores are the best estimate the timing data allows.",
  ],
  [
    'Close gaps are ties',
    "Drivers a few tenths of a second per race apart are effectively level. A gap of a second or more per race is meaningful. Early in a season one safety car can move a driver's average by a couple of seconds, which is why the luckiest and unluckiest need a third of the season to qualify.",
  ],
  [
    'Strategy is not luck',
    'A brilliant early stop still scores neutral. We only measure timing against safety cars, VSCs and red flags.',
  ],
  [
    'Track position',
    'Places gained or lost at restarts are not captured. The safety car queue closes gaps, which is why a stop can never score better than free.',
  ],
  [
    'Mixed conditions',
    'In changing weather, stopping for the right tyre on the right lap can show up as luck, even when it was a smart call.',
  ],
  [
    'Unusual stops',
    'Repairs, red-flag waits and drives through the pit lane behind the safety car are left unscored, as are stops where the car lost lots of time on the way in or out.',
  ],
] as const
</script>

<template>
  <div class="methodology">
    <section class="rise">
      <span class="tag">How it works</span>
      <h1 class="display">What makes<br />a stop <em>free</em></h1>
      <p class="lede">
        A normal pit stop costs around 20 seconds. Box under a safety car and it can cost almost
        nothing. Free Stop measures who got that gift and who just missed it, using only official
        timing data.
      </p>
    </section>

    <section class="section">
      <h2 class="section__title">Find your way around</h2>
      <ol class="guide">
        <li
          v-for="(stop, i) in guide"
          :key="stop.where"
          class="guide__stop card rise"
          :style="{ '--i': i + 1 }"
        >
          <span class="guide__where">{{ i + 1 }}. {{ stop.where }}</span>
          <h3>{{ stop.title }}</h3>
          <p>{{ stop.body }}</p>
          <ul>
            <li v-for="point in stop.points" :key="point">{{ point }}</li>
          </ul>
        </li>
      </ol>
    </section>

    <section class="section">
      <h2 class="section__title">How a stop is scored</h2>
      <ol class="steps">
        <li
          v-for="(step, i) in steps"
          :key="step.title"
          class="step card rise"
          :style="{ '--i': i + 1 }"
        >
          <span class="step__num num">{{ String(i + 1).padStart(2, '0') }}</span>
          <div>
            <h3>{{ step.title }}</h3>
            <p>{{ step.body }}</p>
            <details>
              <summary>Show the maths</summary>
              <code>{{ step.formula }}</code>
            </details>
          </div>
        </li>
      </ol>
    </section>

    <section class="section">
      <h2 class="section__title">Reading the numbers</h2>
      <div class="legend">
        <div class="card legend__item rise" style="--i: 1">
          <span class="legend__value lucky num">+8.400s</span>
          <p>
            Saved 8.4 seconds on the average rival, usually by pitting under a safety car they
            didn't get.
          </p>
        </div>
        <div class="card legend__item rise" style="--i: 2">
          <span class="legend__value unlucky num">−12.000s</span>
          <p>
            Pitted under green two laps before the safety car, while rivals stopped for 12 seconds
            less.
          </p>
        </div>
        <div class="card legend__item rise" style="--i: 3">
          <span class="legend__value unlucky num">−2.500s</span>
          <p>On the crew score: 2.5 seconds longer in the pit lane than a normal stop.</p>
        </div>
      </div>
      <p class="note muted">
        Times are shown to the thousandth of a second, exactly as calculated. Nothing is rounded,
        but that is the precision of the arithmetic, not of the estimate. See Known limitations.
      </p>
    </section>

    <section class="section">
      <h2 class="section__title">Labels you'll see</h2>
      <dl class="labels card">
        <div v-for="[label, tone, meaning] in labels" :key="label" class="labels__row">
          <dt :class="`chip chip--${tone}`">{{ label }}</dt>
          <dd>{{ meaning }}</dd>
        </div>
      </dl>
    </section>

    <section class="section">
      <h2 class="section__title">Known limitations</h2>
      <div class="limits">
        <div
          v-for="([title, body], i) in limits"
          :key="title"
          class="limit card rise"
          :style="{ '--i': i + 1 }"
        >
          <h3>{{ title }}</h3>
          <p>{{ body }}</p>
        </div>
      </div>
    </section>

    <section class="section">
      <h2 class="section__title">Data source</h2>
      <p class="muted">
        All timing and race control data comes from the
        <a href="https://openf1.org" target="_blank" rel="noopener">OpenF1 API</a>, a free,
        open-source Formula 1 data service. Free Stop covers the 2024, 2025 and 2026 seasons.
      </p>
    </section>
  </div>
</template>

<style scoped>
.methodology {
  max-width: 900px;
}

.methodology .tag {
  margin-bottom: 1rem;
}

.guide,
.steps {
  display: grid;
  gap: 0.75rem;
  margin: 0;
  padding: 0;
  list-style: none;
}

.guide {
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 380px), 1fr));
}

.guide__stop {
  padding: 1.3rem 1.4rem;
  border-top: 3px solid var(--f1-red);
}

.guide__where {
  display: inline-block;
  margin-bottom: 0.7rem;
  padding: 0.2rem 0.6rem;
  font-size: 0.85rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: #fff;
  background: var(--f1-red);
  border-radius: 3px;
}

.guide__stop ul {
  display: grid;
  gap: 0.35rem;
  margin: 0.8rem 0 0;
  padding-left: 1.1rem;
  font-size: 0.88rem;
  line-height: 1.55;
  color: var(--text-muted);
}

.step {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 1.25rem;
  padding: 1.4rem 1.5rem;
}

.step__num {
  font-size: 2.6rem;
  font-weight: 900;
  font-style: italic;
  line-height: 1;
  color: var(--f1-red);
}

h3 {
  margin: 0 0 0.4rem;
  font-size: 1.1rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

p {
  margin: 0;
  line-height: 1.65;
  color: var(--text-muted);
}

details {
  margin-top: 0.8rem;
}

summary {
  width: fit-content;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-dim);
  cursor: pointer;
}

summary:hover {
  color: var(--text);
}

code {
  display: block;
  margin-top: 0.6rem;
  padding: 0.7rem 1rem;
  font-family: 'JetBrains Mono', 'Cascadia Code', Consolas, monospace;
  font-size: 0.85rem;
  white-space: pre-wrap;
  color: var(--text);
  background: #08080c;
  border-left: 3px solid var(--f1-red);
  border-radius: 0 4px 4px 0;
}

.legend,
.limits {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 260px), 1fr));
  gap: 0.75rem;
}

.legend__item,
.limit {
  padding: 1.2rem 1.3rem;
}

.legend__value {
  display: block;
  margin-bottom: 0.4rem;
  font-size: 2rem;
  font-weight: 900;
}

.note {
  margin-top: 0.9rem;
  font-size: 0.85rem;
}

.labels {
  display: grid;
  margin: 0;
  padding: 0.4rem 1.3rem;
}

.labels__row {
  display: grid;
  grid-template-columns: 10.5rem 1fr;
  align-items: center;
  gap: 1rem;
  padding: 0.7rem 0;
  border-bottom: 1px solid var(--line);
}

.labels__row:last-child {
  border-bottom: none;
}

.labels dd {
  margin: 0;
  font-size: 0.9rem;
  line-height: 1.5;
  color: var(--text-muted);
}

.chip {
  justify-self: start;
  padding: 0.2rem 0.6rem;
  font-size: 0.85rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  border-radius: 3px;
  color: var(--text);
  background: var(--bg-elev-2);
}

/* Same colours as the race highlight badges */
.chip--lucky {
  background: #1fe08a;
  color: #041a0e;
}

.chip--unlucky {
  background: #ff3b47;
  color: #1a0003;
}

.chip--flag {
  background: #ffd60a;
  color: #1a1500;
}

.chip--crew {
  background: #b14dff;
  color: #0f0020;
}

a {
  color: var(--text);
  text-decoration: underline;
  text-decoration-color: var(--f1-red);
  text-underline-offset: 3px;
}

@media (max-width: 520px) {
  .step {
    grid-template-columns: 1fr;
    gap: 0.5rem;
  }

  .labels__row {
    grid-template-columns: 1fr;
    gap: 0.35rem;
  }
}
</style>
