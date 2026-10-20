import { beforeEach, expect, it, vi } from 'vitest'
import { GenerationIntent } from './generation-intent'

beforeEach(() => sessionStorage.clear())
it('retains the key through retries and remounts, with canonical object order', () => {
  const first = new GenerationIntent('brand')
  const key = first.key({ b: 2, a: 1 })
  expect(first.key({ a: 1, b: 2 })).toBe(key)
  expect(new GenerationIntent('brand').key({ a: 1, b: 2 })).toBe(key)
  expect(() => first.key({ a: 3 })).toThrow(/Resolve/)
  expect(() => first.newIntent()).toThrow(/not resolved/)
})
it('rotates only for an explicit new intent after success', () => {
  const intent = new GenerationIntent('brand')
  const key = intent.key({ a: 1 })
  intent.succeed()
  expect(intent.key({ a: 1 })).toBe(key)
  intent.newIntent()
  // The successful replay above persisted the prior receipt; new intent must clear it.
  expect(intent.key({ a: 1 })).not.toBe(key)
})
it('does not send an unpersisted intent after storage failure', () => {
  const intent = new GenerationIntent('brand')
  const spy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw Error('storage failed') })
  expect(() => intent.key({})).toThrow()
  expect(() => intent.key({})).toThrow()
  spy.mockRestore()
})
it('keeps brands separate and does not clear an unresolved request when editing', () => {
  const a = new GenerationIntent('a')
  const key = a.key({ prompt: 'same' })
  a.editAfterSuccess()
  expect(a.key({ prompt: 'same' })).toBe(key)
  expect(new GenerationIntent('b').key({ prompt: 'same' })).not.toBe(key)
})
