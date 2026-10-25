import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useGenerate } from '@/hooks/use-generate'
import { useWizardGeneration } from '@/components/generation/wizard/use-wizard-generation'
import { apiRequest } from '@/lib/api'
import type { GenerateRequest } from '@/types'

vi.mock('next-intl', () => ({ useTranslations: () => (key: string) => key }))
vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }))
vi.mock('@/lib/api', () => ({
  apiRequest: vi.fn(),
  ApiError: class ApiError extends Error {
    code: string
    status: number
    constructor(message: string, code = 'UNKNOWN', _requestId?: string, status = 0) {
      super(message)
      this.code = code
      this.status = status
    }
  },
}))

const body = { brief: { core_idea: 'test' } } as GenerateRequest
const succeeded = { status: 'succeeded', image_url: 'https://img.example/test.png' }

function keyOf(call: number): string {
  const options = vi.mocked(apiRequest).mock.calls[call][1] as {
    headers?: Record<string, string>
  }
  return options.headers!['Idempotency-Key']
}

function definiteFailure(status: number, code: string) {
  return Object.assign(new Error(code), { status, code })
}

beforeEach(() => {
  sessionStorage.clear()
  vi.mocked(apiRequest).mockReset()
})

for (const wizard of [false, true]) {
  describe(wizard ? 'wizard hook' : 'legacy hook', () => {
    function setup() {
      const hook = renderHook(() => (wizard ? useWizardGeneration('brand') : useGenerate('brand')))
      const submit = () => {
        const current = hook.result.current
        return 'run' in current
          ? current.run(null, () => body as never)
          : current.generate(body)
      }
      return { hook, submit }
    }

    it('suppresses duplicates and reuses the key after a network failure', async () => {
      let reject!: (error: Error) => void
      vi.mocked(apiRequest).mockImplementationOnce(
        () => new Promise((_, r) => { reject = r }),
      )
      const { submit } = setup()
      let first!: Promise<void>
      await act(async () => {
        first = submit()
        await submit()
      })
      expect(apiRequest).toHaveBeenCalledTimes(1)
      const key = keyOf(0)
      await act(async () => {
        reject(Error('network'))
        await first
      })
      vi.mocked(apiRequest).mockRejectedValueOnce(Error('still unknown'))
      await act(async () => { await submit() })
      expect(apiRequest).toHaveBeenCalledTimes(2)
      expect(keyOf(1)).toBe(key)
    })

    it('keeps the key while the server says the request is still in progress', async () => {
      vi.mocked(apiRequest).mockRejectedValue(definiteFailure(409, 'GENERATION_IN_PROGRESS'))
      const { submit } = setup()
      await act(async () => { await submit() })
      await act(async () => { await submit() })
      expect(keyOf(1)).toBe(keyOf(0))
    })

    it('uses a new key after a definite failure so the user is never stuck', async () => {
      vi.mocked(apiRequest).mockRejectedValue(definiteFailure(402, 'INSUFFICIENT_CREDITS'))
      const { submit } = setup()
      await act(async () => { await submit() })
      await act(async () => { await submit() })
      expect(apiRequest).toHaveBeenCalledTimes(2)
      expect(keyOf(1)).not.toBe(keyOf(0))
    })
  })
}

describe('wizard hook', () => {
  it('creates a new key only for explicit regeneration after success', async () => {
    vi.mocked(apiRequest).mockResolvedValue(succeeded)
    const hook = renderHook(() => useWizardGeneration('brand'))
    await act(async () => { await hook.result.current.run(null, () => body as never) })
    await act(async () => { await hook.result.current.run(null, () => body as never, true) })
    expect(keyOf(1)).not.toBe(keyOf(0))
  })

  it('does not change the key when the inputs are unchanged and no regeneration was requested', async () => {
    vi.mocked(apiRequest).mockResolvedValue(succeeded)
    const hook = renderHook(() => useWizardGeneration('brand'))
    await act(async () => { await hook.result.current.run(null, () => body as never) })
    await act(async () => { await hook.result.current.run(null, () => body as never) })
    expect(keyOf(1)).toBe(keyOf(0))
  })
})
