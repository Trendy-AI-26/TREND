import { describe, expect, it, vi, beforeEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { usePreviewBrief } from '@/hooks/use-preview-brief'
import type { GenerationBrief } from '@/types/generation'

// We mock the API layer (which itself talks to the backend) so this test only
// exercises usePreviewBrief's own logic: dedupe, retry, loading/error state.
const apiRequestMock = vi.fn()
vi.mock('@/lib/api', () => ({
    apiRequest: (...args: unknown[]) => apiRequestMock(...args),
    ApiError: class ApiError extends Error {
        code: string
        constructor(message: string, code = 'UNKNOWN') {
            super(message)
            this.code = code
        }
    },
}))

const brief = { campaign_goal: 'brand_awareness' } as unknown as GenerationBrief

beforeEach(() => {
    apiRequestMock.mockReset()
})

describe('usePreviewBrief', () => {
    it('starts with no preview, not loading, no error', () => {
        const { result } = renderHook(() => usePreviewBrief('brand-1'))
        expect(result.current.preview).toBeNull()
        expect(result.current.loading).toBe(false)
        expect(result.current.error).toBeNull()
    })

    it('sets loading true during the request, then populates preview on success', async () => {
        apiRequestMock.mockResolvedValueOnce({
            creative_direction: { core_idea: 'Great idea' },
            brand_name: 'Acme',
        })
        const { result } = renderHook(() => usePreviewBrief('brand-1'))

        act(() => {
            result.current.fetchPreview(brief, 'instagram_post')
        })
        expect(result.current.loading).toBe(true)

        await waitFor(() => expect(result.current.loading).toBe(false))
        expect(result.current.preview).toEqual({ core_idea: 'Great idea' })
        expect(result.current.error).toBeNull()
        expect(apiRequestMock).toHaveBeenCalledTimes(1)
    })

    it('sets an error message when the request fails', async () => {
        apiRequestMock.mockRejectedValueOnce(new Error('boom'))
        const { result } = renderHook(() => usePreviewBrief('brand-1'))

        await act(async () => {
            await result.current.fetchPreview(brief, 'instagram_post')
        })

        expect(result.current.error).toBe('boom')
        expect(result.current.preview).toBeNull()
    })

    it('does NOT fire a second request for the exact same brand + brief + platform', async () => {
        apiRequestMock.mockResolvedValue({
            creative_direction: { core_idea: 'Same idea' },
            brand_name: 'Acme',
        })
        const { result } = renderHook(() => usePreviewBrief('brand-1'))

        await act(async () => {
            await result.current.fetchPreview(brief, 'instagram_post')
        })
        await act(async () => {
            // Same brief + platform again (e.g. caused by an unrelated re-render)
            await result.current.fetchPreview(brief, 'instagram_post')
        })

        expect(apiRequestMock).toHaveBeenCalledTimes(1)
    })

    it('DOES fire a new request when the brief actually changes', async () => {
        apiRequestMock.mockResolvedValue({
            creative_direction: { core_idea: 'Idea' },
            brand_name: 'Acme',
        })
        const { result } = renderHook(() => usePreviewBrief('brand-1'))

        await act(async () => {
            await result.current.fetchPreview(brief, 'instagram_post')
        })
        await act(async () => {
            await result.current.fetchPreview(
                { ...brief, campaign_goal: 'product_launch' } as unknown as GenerationBrief,
                'instagram_post',
            )
        })

        expect(apiRequestMock).toHaveBeenCalledTimes(2)
    })

    it('retryPreview re-runs the last request even though the key is unchanged', async () => {
        apiRequestMock
            .mockRejectedValueOnce(new Error('first failure'))
            .mockResolvedValueOnce({
                creative_direction: { core_idea: 'Recovered' },
                brand_name: 'Acme',
            })
        const { result } = renderHook(() => usePreviewBrief('brand-1'))

        await act(async () => {
            await result.current.fetchPreview(brief, 'instagram_post')
        })
        expect(result.current.error).toBe('first failure')

        await act(async () => {
            await result.current.retryPreview()
        })

        expect(apiRequestMock).toHaveBeenCalledTimes(2)
        expect(result.current.error).toBeNull()
        expect(result.current.preview).toEqual({ core_idea: 'Recovered' })
    })

    it('sends the brief and platform in the request payload (guards against payload regressions)', async () => {
        apiRequestMock.mockResolvedValueOnce({
            creative_direction: { core_idea: 'x' },
            brand_name: 'Acme',
        })
        const { result } = renderHook(() => usePreviewBrief('brand-42'))

        await act(async () => {
            await result.current.fetchPreview(brief, 'instagram_story')
        })

        expect(apiRequestMock).toHaveBeenCalledWith(
            '/brands/brand-42/preview-brief',
            expect.objectContaining({
                method: 'POST',
                body: JSON.stringify({ brief, platform_preset: 'instagram_story' }),
            }),
        )
    })
})