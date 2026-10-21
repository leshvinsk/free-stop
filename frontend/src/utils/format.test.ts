import { describe, expect, it } from 'vitest'
import { formatFullName, formatLuck, luckClass, splitName, teamColour } from './format'

describe('formatLuck', () => {
  it('shows times to the thousandth with a sign', () => {
    expect(formatLuck(3.616)).toBe('+3.616s')
    expect(formatLuck(-4.654)).toBe('-4.654s')
    expect(formatLuck(18.19)).toBe('+18.190s')
  })

  it('keeps tiny values distinct from zero rather than rounding them away', () => {
    expect(formatLuck(-0.049)).toBe('-0.049s')
    expect(formatLuck(0)).toBe('0.000s')
  })

  it('shows a dash when there is no score', () => {
    expect(formatLuck(null)).toBe('—')
  })
})

describe('luckClass', () => {
  it('colours by sign, with zero and missing scores neutral', () => {
    expect(luckClass(1.2)).toBe('lucky')
    expect(luckClass(-0.001)).toBe('unlucky')
    expect(luckClass(0)).toBe('muted')
    expect(luckClass(null)).toBe('muted')
  })
})

describe('names and colours', () => {
  it("title-cases OpenF1's all-caps surnames", () => {
    expect(formatFullName('Charles LECLERC')).toBe('Charles Leclerc')
    expect(formatFullName('Nyck DE VRIES')).toBe('Nyck De Vries')
  })

  it('splits off the surname for the driver cards', () => {
    expect(splitName('Kimi Antonelli')).toEqual({ first: 'Kimi', last: 'Antonelli' })
  })

  it('turns bare hex team colours into CSS colours', () => {
    expect(teamColour('3671C6')).toBe('#3671C6')
    expect(teamColour(null)).toBe('#6b6b76')
  })
})
