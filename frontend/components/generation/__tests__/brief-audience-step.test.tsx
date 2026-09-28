import type { ReactElement } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { NextIntlClientProvider } from 'next-intl'
import { BriefAudienceStep } from '@/components/generation/brief-audience-step'
import { AUDIENCE_SEGMENTS } from '@/lib/generation-options'
import type { TargetAudienceBrief } from '@/types/generation'
import messages from '@/messages/en.json'

function renderWithIntl(ui: ReactElement) {
    return render(
        <NextIntlClientProvider locale="en" messages={messages}>
            {ui}
        </NextIntlClientProvider>,
    )
}

const EMPTY_AUDIENCE: TargetAudienceBrief = {
    segments: [],
    location: null,
    age_range: null,
    gender_focus: null,
    details: null,
}

// The first 5 selectable (non-"custom") segment values, used to click
// through 0/1/2/3/4 selections in order.
const SEGMENT_VALUES = AUDIENCE_SEGMENTS.filter((s) => s.value !== 'custom')
    .slice(0, 5)
    .map((s) => s.value)

describe('BriefAudienceStep — regression: 3-segment cap', () => {
    it('allows selecting a 1st, 2nd and 3rd segment', async () => {
        const user = userEvent.setup()
        const onChange = vi.fn()
        let audience = EMPTY_AUDIENCE

        const { rerender } = renderWithIntl(
            <BriefAudienceStep audience={audience} onChange={onChange} />,
        )

        for (let i = 0; i < 3; i++) {
            const buttons = screen.getAllByRole('button')
            await user.click(buttons[i])
            audience = onChange.mock.calls[onChange.mock.calls.length - 1][0]
            rerender(
                <NextIntlClientProvider locale="en" messages={messages}>
                    <BriefAudienceStep audience={audience} onChange={onChange} />
                </NextIntlClientProvider>,
            )
        }

        expect(audience.segments).toHaveLength(3)
    })

    it('rejects a 4th selection once 3 are already selected', async () => {
        const user = userEvent.setup()
        const onChange = vi.fn()
        const audience: TargetAudienceBrief = {
            ...EMPTY_AUDIENCE,
            segments: SEGMENT_VALUES.slice(0, 3),
        }

        renderWithIntl(<BriefAudienceStep audience={audience} onChange={onChange} />)

        const buttons = screen.getAllByRole('button')
        // The 4th, not-yet-selected segment's button should be disabled.
        expect(buttons[3]).toBeDisabled()

        await user.click(buttons[3])
        expect(onChange).not.toHaveBeenCalled()
    })

    it('shows the "up to three" hint once 3 segments are selected', () => {
        const audience: TargetAudienceBrief = {
            ...EMPTY_AUDIENCE,
            segments: SEGMENT_VALUES.slice(0, 3),
        }

        renderWithIntl(<BriefAudienceStep audience={audience} onChange={vi.fn()} />)
        expect(
            screen.getByText('You can select up to three audience groups.'),
        ).toBeInTheDocument()
    })

    it('does not show the limit hint with only 2 segments selected', () => {
        const audience: TargetAudienceBrief = {
            ...EMPTY_AUDIENCE,
            segments: SEGMENT_VALUES.slice(0, 2),
        }

        renderWithIntl(<BriefAudienceStep audience={audience} onChange={vi.fn()} />)
        expect(
            screen.queryByText('You can select up to three audience groups.'),
        ).not.toBeInTheDocument()
    })

    it('still allows de-selecting a segment while at the 3-segment cap', async () => {
        const user = userEvent.setup()
        const onChange = vi.fn()
        const audience: TargetAudienceBrief = {
            ...EMPTY_AUDIENCE,
            segments: SEGMENT_VALUES.slice(0, 3),
        }

        renderWithIntl(<BriefAudienceStep audience={audience} onChange={onChange} />)

        const [selectedButton] = screen.getAllByRole('button', { pressed: true })
        await user.click(selectedButton)

        expect(onChange).toHaveBeenCalledWith({
            ...audience,
            segments: audience.segments.slice(1),
        })
    })

    it('typing in the audience notes field does not clear the selected segments', async () => {
        const user = userEvent.setup()
        const onChange = vi.fn()
        const audience: TargetAudienceBrief = {
            ...EMPTY_AUDIENCE,
            segments: SEGMENT_VALUES.slice(0, 2),
        }

        renderWithIntl(<BriefAudienceStep audience={audience} onChange={onChange} />)

        const notesField = screen.getByLabelText('Tell us more about this audience (optional)')
        await user.type(notesField, 'x')

        const lastCall = onChange.mock.calls[onChange.mock.calls.length - 1][0]
        expect(lastCall.segments).toEqual(audience.segments)
    })
})