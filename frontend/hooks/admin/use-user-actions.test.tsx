import { act, cleanup, renderHook } from '@testing-library/react'
import { NextIntlClientProvider } from 'next-intl'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/lib/api'
import messages from '@/messages/en.json'
import { useUserActions, type UserAction } from './use-user-actions'

const mocks = vi.hoisted(() => ({ confirm: vi.fn(), api: vi.fn(), success: vi.fn(), error: vi.fn() }))
vi.mock('@/components/ui/confirm-dialog', () => ({ useConfirm: () => mocks.confirm }))
vi.mock('@/lib/api', async importOriginal => ({ ...await importOriginal<typeof import('@/lib/api')>(), apiRequest: mocks.api }))
vi.mock('sonner', () => ({ toast: { success: mocks.success, error: mocks.error } }))
function wrapper({ children }: { children: React.ReactNode }) { return <NextIntlClientProvider locale="en" messages={messages}>{children}</NextIntlClientProvider> }
beforeEach(() => { vi.resetAllMocks(); mocks.confirm.mockResolvedValue(true); mocks.api.mockResolvedValue({ id: 'u1' }) })
afterEach(cleanup)
describe('user actions flow', () => {
  it.each(['disable', 'delete', 'reset-daily-usage'] as UserAction[])('confirms %s before API, then toast and refresh', async action => {
    const events: string[] = []; const refresh = vi.fn(() => { events.push('refresh') })
    mocks.confirm.mockImplementation(async () => { events.push('confirm'); return true })
    mocks.api.mockImplementation(async () => { events.push('api'); return { id: 'u1' } })
    mocks.success.mockImplementation(() => { events.push('toast') })
    const { result } = renderHook(() => useUserActions('u1', refresh), { wrapper })
    await act(async () => { await result.current.run(action) })
    expect(mocks.confirm).toHaveBeenCalledWith(expect.objectContaining({ tone: 'danger' }))
    expect(mocks.api).toHaveBeenCalledWith(`/admin/users/u1${action === 'delete' ? '' : `/${action}`}`, expect.objectContaining({ method: action === 'delete' ? 'DELETE' : 'POST' }))
    expect(events).toEqual(['confirm', 'api', 'toast', 'refresh'])
    expect(refresh).toHaveBeenCalledWith(action === 'delete')
  })
  it('does nothing after cancellation', async () => {
    mocks.confirm.mockResolvedValue(false)
    const refresh = vi.fn(); const { result } = renderHook(() => useUserActions('u1', refresh), { wrapper })
    await act(async () => { await result.current.run('disable') })
    expect(mocks.api).not.toHaveBeenCalled(); expect(mocks.success).not.toHaveBeenCalled(); expect(refresh).not.toHaveBeenCalled()
  })
  it.each([
    ['verify-email', undefined], ['enable', undefined], ['grant-generations', { amount: 10, note: 'Support' }], ['extend-trial', { days: 7 }],
  ] as [UserAction, object | undefined][])('posts %s and refreshes without destructive confirmation', async (action, body) => {
    const refresh = vi.fn(); const { result } = renderHook(() => useUserActions('u1', refresh), { wrapper })
    await act(async () => { await result.current.run(action, body) })
    expect(mocks.confirm).not.toHaveBeenCalled()
    expect(mocks.api).toHaveBeenCalledWith(`/admin/users/u1/${action}`, { method: 'POST', ...(body ? { body: JSON.stringify(body) } : {}) })
    expect(mocks.success).toHaveBeenCalledOnce(); expect(refresh).toHaveBeenCalledWith(false)
  })
  it('uses translated error toast and does not report success on forbidden target', async () => {
    mocks.api.mockRejectedValue(new ApiError('Forbidden', 'ADMIN_TARGET_FORBIDDEN', undefined, 403))
    const refresh = vi.fn(); const { result } = renderHook(() => useUserActions('u1', refresh), { wrapper })
    await act(async () => { await result.current.run('delete') })
    expect(mocks.error).toHaveBeenCalledWith(messages.errors.codes.ADMIN_TARGET_FORBIDDEN)
    expect(mocks.success).not.toHaveBeenCalled(); expect(refresh).not.toHaveBeenCalled()
    expect(result.current.busy).toBe(false)
  })
})
