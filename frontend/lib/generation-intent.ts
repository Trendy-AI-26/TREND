// Keep an unresolved generation intent across retries/remounts in this browser tab.
// Never rotate its key because a request failed ambiguously or its response was lost:
// the backend replays the saved outcome for the same Idempotency-Key and never calls
// the provider twice for it.

export function canonicalPayload(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalPayload).join(',')}]`
  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>
    return `{${Object.keys(record).filter(k => record[k] !== undefined).sort()
      .map(k => `${JSON.stringify(k)}:${canonicalPayload(record[k])}`).join(',')}}`
  }
  return JSON.stringify(value)
}

/** Thrown before sending when the inputs changed while a request is still unresolved. */
export class IntentUnresolvedError extends Error {
  code = 'GENERATION_INTENT_UNRESOLVED'

  constructor() {
    super('Resolve the previous generation request before changing its inputs.')
    this.name = 'IntentUnresolvedError'
  }
}

/** Backend codes after which retrying with the SAME key is correct (it resumes or replays). */
const RETRY_WITH_SAME_KEY = new Set([
  'GENERATION_IN_PROGRESS',
  'GENERATION_SETTLEMENT_PENDING',
  'GENERATION_ADMISSION_FAILED',
  'NETWORK_ERROR',
  'BACKEND_UNREACHABLE',
  'GATEWAY_TIMEOUT',
  'TIMEOUT',
])

/**
 * True when the failure of a generate request settles the intent: the server gave a
 * definite answer, so replaying the same key can only return that same failure.
 * Network failures, proxy errors and "still in progress" answers are ambiguous and
 * keep the key.
 */
export function isDefiniteFailure(err: unknown): boolean {
  const { status, code } = (err ?? {}) as { status?: unknown; code?: unknown }
  if (typeof status !== 'number') return false
  if (status === 0) return false
  if (typeof code === 'string' && RETRY_WITH_SAME_KEY.has(code)) return false
  if (status >= 500 && (code === undefined || code === 'UNKNOWN')) return false
  return true
}

export class GenerationIntent {
  private intent: { payload: string; key: string } | null = null
  private completed = false
  constructor(private readonly brandId: string) {}

  private get storageKey() {
    return `generation-intent:${this.brandId}`
  }

  key(body: unknown): string {
    const payload = canonicalPayload(body)
    if (!this.intent) {
      const stored = sessionStorage.getItem(this.storageKey)
      if (stored) {
        const parsed = JSON.parse(stored)
        if (typeof parsed.payload !== 'string' || typeof parsed.key !== 'string') {
          throw new Error('Stored generation request is invalid. Do not retry automatically.')
        }
        this.intent = parsed
      }
    }
    if (this.intent && this.intent.payload !== payload) {
      throw new IntentUnresolvedError()
    }
    if (!this.intent) {
      this.intent = { payload, key: crypto.randomUUID() }
      this.completed = false
    }
    // Fail before sending if persistence is unavailable.
    sessionStorage.setItem(this.storageKey, JSON.stringify(this.intent))
    return this.intent.key
  }

  /** The request succeeded: its key may still be replayed for the same inputs. */
  succeed() {
    this.completed = true
    sessionStorage.removeItem(this.storageKey)
  }

  /** The server rejected the request definitively: the next attempt gets a new key. */
  abandon() {
    this.intent = null
    this.completed = false
    sessionStorage.removeItem(this.storageKey)
  }

  /** Explicit "generate another one" after a success. */
  newIntent() {
    if (this.intent && !this.completed) throw new Error('The previous request is not resolved.')
    this.abandon()
  }

  editAfterSuccess() {
    if (this.completed) this.newIntent()
  }
}
