import { describe, expect, it } from 'vitest'
import { isValidTrendSlug, suggestTrendSlug } from './trend-slug'

describe('trend slug', () => {
  it('suggests a lowercase ASCII slug and normalizes accents', () => {
    expect(suggestTrendSlug('  Café & Summer 2026! ')).toBe('cafe-summer-2026')
    expect(suggestTrendSlug('Already---a slug')).toBe('already-a-slug')
  })
  it('leaves Arabic-only names for an explicit Latin slug', () => {
    expect(suggestTrendSlug('اتجاه جديد')).toBe('')
    expect(isValidTrendSlug('')).toBe(false)
  })
  it.each(['summer-2026', 'a', '123'])('accepts %s', value => {
    expect(isValidTrendSlug(value)).toBe(true)
  })
  it.each(['A', '-trend', 'trend-', 'two--hyphens', 'two words', 'عربي', 'path/name', 'a_b'])('rejects %s', value => {
    expect(isValidTrendSlug(value)).toBe(false)
  })
})
