import { act, renderHook } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { useGenerate } from './use-generate'
import { useWizardGeneration } from '@/components/generation/wizard/use-wizard-generation'
import { apiRequest } from '@/lib/api'
import type { GenerateRequest } from '@/types'
vi.mock('@/lib/api', () => ({ apiRequest: vi.fn(), ApiError: class extends Error {} }))
const body = { brief: { core_idea: 'test' } } as GenerateRequest
beforeEach(() => { sessionStorage.clear(); vi.mocked(apiRequest).mockReset() })
for (const wizard of [false, true]) {
  it(`${wizard ? 'wizard' : 'legacy'} suppresses duplicates and reuses key after network failure`, async () => {
    let reject!: (error: Error) => void
    vi.mocked(apiRequest).mockImplementationOnce(() => new Promise((_, r) => { reject = r }))
    const hook = renderHook(() => wizard ? useWizardGeneration('brand') : useGenerate('brand'))
    const submit = () => 'run' in hook.result.current
      ? hook.result.current.run(null, () => body as never)
      : hook.result.current.generate(body)
    let first!: Promise<void>
    await act(async () => { first = submit(); await submit() })
    expect(apiRequest).toHaveBeenCalledTimes(1)
    const key = (vi.mocked(apiRequest).mock.calls[0][1]?.headers as Record<string,string>)['Idempotency-Key']
    await act(async () => { reject(Error('network')); await first })
    vi.mocked(apiRequest).mockRejectedValueOnce(Error('still unknown'))
    await act(async () => { await submit() })
    expect(apiRequest).toHaveBeenCalledTimes(2)
    expect((vi.mocked(apiRequest).mock.calls[1][1]?.headers as Record<string,string>)['Idempotency-Key']).toBe(key)
  })
}
it('wizard creates a new key only for explicit regeneration after success', async () => {
  vi.mocked(apiRequest).mockResolvedValue({ status: 'succeeded', image_url: 'test' })
  const hook = renderHook(() => useWizardGeneration('brand'))
  await act(async () => { await hook.result.current.run(null, () => body as never) })
  const first = (vi.mocked(apiRequest).mock.calls[0][1]?.headers as Record<string,string>)['Idempotency-Key']
  await act(async () => { await hook.result.current.run(null, () => body as never, true) })
  const second = (vi.mocked(apiRequest).mock.calls[1][1]?.headers as Record<string,string>)['Idempotency-Key']
  expect(second).not.toBe(first)
})
