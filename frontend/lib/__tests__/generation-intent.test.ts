import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
  GenerationIntent,
  IntentUnresolvedError,
  isDefiniteFailure,
} from '@/lib/generation-intent'

beforeEach(() => sessionStorage.clear())

describe('GenerationIntent', () => {
  it('retains the key through retries and remounts, with canonical object order', () => {
    const first = new GenerationIntent('brand')
    const key = first.key({ b: 2, a: 1 })
    expect(first.key({ a: 1, b: 2 })).toBe(key)
    expect(new GenerationIntent('brand').key({ a: 1, b: 2 })).toBe(key)
    expect(() => first.key({ a: 3 })).toThrow(/Resolve/)
    expect(() => first.newIntent()).toThrow(/not resolved/)
  })

  it('reports changed inputs with a translatable code', () => {
    const intent = new GenerationIntent('brand')
    intent.key({ a: 1 })
    let caught: unknown
    try {
      intent.key({ a: 2 })
    } catch (err) {
      caught = err
    }
    expect(caught).toBeInstanceOf(IntentUnresolvedError)
    expect((caught as IntentUnresolvedError).code).toBe('GENERATION_INTENT_UNRESOLVED')
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
    const spy = vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw Error('storage failed')
    })
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

  it('abandon lets the next attempt use a new key and other inputs', () => {
    const intent = new GenerationIntent('brand')
    const key = intent.key({ a: 1 })
    intent.abandon()
    expect(intent.key({ a: 2 })).not.toBe(key)
    expect(new GenerationIntent('brand').key({ a: 2 })).toBe(intent.key({ a: 2 }))
  })
})

describe('isDefiniteFailure', () => {
  const failure = (status: number, code: string) => ({ status, code })

  it('treats a definite server answer as settled', () => {
    expect(isDefiniteFailure(failure(402, 'INSUFFICIENT_CREDITS'))).toBe(true)
    expect(isDefiniteFailure(failure(502, 'INVALID_KEY'))).toBe(true)
    expect(isDefiniteFailure(failure(503, 'GENERATION_OUTCOME_UNKNOWN'))).toBe(true)
    expect(isDefiniteFailure(failure(409, 'IDEMPOTENCY_KEY_REUSED'))).toBe(true)
  })

  it('keeps the key when the outcome is ambiguous or resumable', () => {
    expect(isDefiniteFailure(failure(0, 'NETWORK_ERROR'))).toBe(false)
    expect(isDefiniteFailure(failure(409, 'GENERATION_IN_PROGRESS'))).toBe(false)
    expect(isDefiniteFailure(failure(503, 'GENERATION_SETTLEMENT_PENDING'))).toBe(false)
    expect(isDefiniteFailure(failure(504, 'GATEWAY_TIMEOUT'))).toBe(false)
    expect(isDefiniteFailure(failure(502, 'BACKEND_UNREACHABLE'))).toBe(false)
    expect(isDefiniteFailure(failure(502, 'UNKNOWN'))).toBe(false)
    expect(isDefiniteFailure(new Error('network'))).toBe(false)
    expect(isDefiniteFailure(undefined)).toBe(false)
  })
})
