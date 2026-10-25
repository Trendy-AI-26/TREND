import { describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { NextIntlClientProvider } from 'next-intl'
import { GenerationBriefForm } from '@/components/generation/generation-brief-form'
import messages from '@/messages/en.json'
import type { GenerationBrief } from '@/types'

const { fetchPreviewMock, retryPreviewMock } = vi.hoisted(() => ({
    fetchPreviewMock: vi.fn(),
    retryPreviewMock: vi.fn(),
}))

vi.mock('@/hooks/use-preview-brief', () => ({
    usePreviewBrief: () => ({
        preview: {
            campaign_goal: 'brand_awareness',
            content_type: 'product_showcase',
            target_audience: 'general_consumers',
            core_idea: 'A complete brief preview',
            voice_tone: 'friendly',
            platform: { name: 'instagram_post', note: 'Square format' },
            text_to_include: null,
            optional_notes: null,
        },
        loading: false,
        error: null,
        fetchPreview: fetchPreviewMock,
        retryPreview: retryPreviewMock,
    }),
}))

const completeBrief: GenerationBrief = {
    campaign_goal: 'brand_awareness',
    campaign_goal_custom: null,
    content_type: 'product_showcase',
    content_type_custom: null,
    target_audience: {
        segments: ['general_consumers'],
        location: 'Amman',
        age_range: '25_34',
        gender_focus: 'all',
        details: 'People interested in premium products',
    },
    core_idea: 'Show the product in a premium lifestyle setting',
    voice_tone: 'friendly',
    voice_tone_custom: null,
    optional_notes: null,
    text_to_include: null,
}

describe('GenerationBriefForm — Preview Brief integration regression', () => {
    it('mounts one preview on Summary and keeps one after leaving and returning', async () => {
        const user = userEvent.setup()
        render(
            <NextIntlClientProvider locale="en" messages={messages}>
                <GenerationBriefForm
                    value={completeBrief}
                    onChange={vi.fn()}
                    onComplete={vi.fn()}
                    platformPreset="instagram_post"
                    brandId="brand-1"
                    brandName="Acme"
                />
            </NextIntlClientProvider>,
        )

        const nextButton = () => screen.getByRole('button', { name: /^Next$/i })
        for (let index = 0; index < 5; index += 1) {
            await user.click(nextButton())
        }

        await waitFor(() => {
            expect(screen.getAllByTestId('brief-creative-preview')).toHaveLength(1)
        })
        expect(screen.getAllByText('Creative Direction')).toHaveLength(1)
        expect(fetchPreviewMock).toHaveBeenCalledTimes(1)

        await user.click(screen.getByRole('button', { name: /^Back$/i }))
        await user.click(nextButton())

        await waitFor(() => {
            expect(screen.getAllByTestId('brief-creative-preview')).toHaveLength(1)
        })
        expect(screen.getAllByText('Creative Direction')).toHaveLength(1)
        expect(fetchPreviewMock).toHaveBeenCalledTimes(2)
    })
})
