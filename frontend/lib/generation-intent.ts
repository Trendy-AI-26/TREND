// Keep an unresolved intent across retries/remounts in this browser tab.
// Never rotate its key because a request failed or its response was lost.
export function canonicalPayload(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalPayload).join(',')}]`
  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>
    return `{${Object.keys(record).filter(k => record[k] !== undefined).sort()
      .map(k => `${JSON.stringify(k)}:${canonicalPayload(record[k])}`).join(',')}}`
  }
  return JSON.stringify(value)
}

export class GenerationIntent {
  private intent: { payload: string; key: string } | null = null
  private completed = false
  constructor(private readonly brandId: string) {}

  key(body: unknown): string {
    const payload = canonicalPayload(body)
    const storageKey = `generation-intent:${this.brandId}`
    if (!this.intent) {
      const stored = sessionStorage.getItem(storageKey)
      if (stored) {
        const parsed = JSON.parse(stored)
        if (typeof parsed.payload !== 'string' || typeof parsed.key !== 'string') {
          throw new Error('Stored generation request is invalid. Do not retry automatically.')
        }
        this.intent = parsed
      }
    }
    if (this.intent && this.intent.payload !== payload) {
      throw new Error('Resolve the previous generation request before changing its inputs.')
    }
    if (!this.intent) {
      this.intent = { payload, key: crypto.randomUUID() }
      this.completed = false
      // Fail before sending if persistence is unavailable.
    }
    sessionStorage.setItem(storageKey, JSON.stringify(this.intent))
    return this.intent.key
  }

  succeed() {
    this.completed = true
    sessionStorage.removeItem(`generation-intent:${this.brandId}`)
  }

  newIntent() {
    if (!this.completed) throw new Error('The previous request is not resolved.')
    this.intent = null
    this.completed = false
    sessionStorage.removeItem(`generation-intent:${this.brandId}`)
  }

  editAfterSuccess() {
    if (this.completed) this.newIntent()
  }
}
