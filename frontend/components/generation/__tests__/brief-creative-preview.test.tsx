import type { ReactElement } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { NextIntlClientProvider } from 'next-intl'
import { BriefCreativePreview } from '@/components/generation/brief-creative-preview'
import type { CreativeDirection } from '@/types/generation'
import messages from '@/messages/en.json'

// The component now calls useTranslations(), which requires a
// NextIntlClientProvider ancestor. Tests run the component in isolation
// (no RootLayout), so we provide that context manually here. We render
// in English so the existing assertions (which check English strings)
// keep working unchanged.
function renderWithIntl(ui: ReactElement) {
    return render(
        <NextIntlClientProvider locale="en" messages={messages}>
            {ui}
        </NextIntlClientProvider>,
    )
}

const mockPreview: CreativeDirection = {
    campaign_goal: 'brand_awareness',
    content_type: 'social_post',
    target_audience: 'marketers_creators',
    core_idea: 'Show the product in real-life use',
    voice_tone: 'friendly',
    platform: { name: 'instagram_post', note: '1080x1080' },
    text_to_include: 'New drop!',
    optional_notes: 'Keep it bright',
}

describe('BriefCreativePreview — regression: single instance only', () => {
    it('renders exactly ONE preview element while loading', () => {
        renderWithIntl(<BriefCreativePreview preview={null} loading error={null} brandName="Acme" />)
        expect(screen.getAllByTestId('brief-creative-preview')).toHaveLength(1)
    })

    it('renders exactly ONE preview element on error', () => {
        renderWithIntl(
            <BriefCreativePreview
                preview={null}
                loading={false}
                error="Something went wrong"
                brandName="Acme"
            />,
        )
        expect(screen.getAllByTestId('brief-creative-preview')).toHaveLength(1)
    })

    it('renders exactly ONE preview element on success, with exactly ONE "Creative Direction" heading', () => {
        renderWithIntl(
            <BriefCreativePreview preview={mockPreview} loading={false} error={null} brandName="Acme" />,
        )
        expect(screen.getAllByTestId('brief-creative-preview')).toHaveLength(1)
        expect(screen.getAllByText('Creative Direction')).toHaveLength(1)
    })

    it('re-rendering with new preview data still yields exactly one instance (no card is appended)', () => {
        const { rerender } = renderWithIntl(
            <BriefCreativePreview preview={mockPreview} loading={false} error={null} brandName="Acme" />,
        )
        rerender(
            <NextIntlClientProvider locale="en" messages={messages}>
                <BriefCreativePreview
                    preview={{ ...mockPreview, core_idea: 'A different idea now' }}
                    loading={false}
                    error={null}
                    brandName="Acme"
                />
            </NextIntlClientProvider>,
        )
        expect(screen.getAllByTestId('brief-creative-preview')).toHaveLength(1)
        expect(screen.getByText('A different idea now')).toBeInTheDocument()
    })
})

describe('BriefCreativePreview — loading / error / success states', () => {
    it('shows a loading indicator while loading is true', () => {
        renderWithIntl(<BriefCreativePreview preview={null} loading error={null} brandName="Acme" />)
        expect(screen.getByText(/Translating your brief/i)).toBeInTheDocument()
    })

    it('shows the error message and a Retry button when error is set', () => {
        renderWithIntl(
            <BriefCreativePreview
                preview={null}
                loading={false}
                error="Network error"
                brandName="Acme"
                retryPreview={vi.fn()}
            />,
        )
        expect(screen.getByText('Network error')).toBeInTheDocument()
        expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
    })

    it('calls retryPreview when the Retry button is clicked', async () => {
        const retryPreview = vi.fn()
        const user = userEvent.setup()
        renderWithIntl(
            <BriefCreativePreview
                preview={null}
                loading={false}
                error="Network error"
                brandName="Acme"
                retryPreview={retryPreview}
            />,
        )
        await user.click(screen.getByRole('button', { name: /retry/i }))
        expect(retryPreview).toHaveBeenCalledTimes(1)
    })

    it('renders nothing when there is no preview, no error, and not loading', () => {
        const { container } = renderWithIntl(
            <BriefCreativePreview preview={null} loading={false} error={null} brandName="Acme" />,
        )
        expect(container).toBeEmptyDOMElement()
    })

    it('shows the brief fields once preview data is available', () => {
        renderWithIntl(
            <BriefCreativePreview preview={mockPreview} loading={false} error={null} brandName="Acme" />,
        )
        expect(screen.getByText('Show the product in real-life use')).toBeInTheDocument()
        expect(screen.getByText('"New drop!"')).toBeInTheDocument()
    })
})

describe('BriefCreativePreview — inline Edit affordance', () => {
    it('calls onEdit with the right step number for each field', async () => {
        const onEdit = vi.fn()
        const user = userEvent.setup()
        renderWithIntl(
            <BriefCreativePreview
                preview={mockPreview}
                loading={false}
                error={null}
                brandName="Acme"
                onEdit={onEdit}
            />,
        )

        await user.click(screen.getByRole('button', { name: /edit campaign goal/i }))
        expect(onEdit).toHaveBeenLastCalledWith(0)

        await user.click(screen.getByRole('button', { name: /edit content type/i }))
        expect(onEdit).toHaveBeenLastCalledWith(1)

        await user.click(screen.getByRole('button', { name: /edit target audience/i }))
        expect(onEdit).toHaveBeenLastCalledWith(2)

        await user.click(screen.getByRole('button', { name: /edit core idea/i }))
        expect(onEdit).toHaveBeenLastCalledWith(3)

        await user.click(screen.getByRole('button', { name: /edit voice & tone/i }))
        expect(onEdit).toHaveBeenLastCalledWith(4)

        expect(onEdit).toHaveBeenCalledTimes(5)
    })

    it('does not render any edit buttons when onEdit is not provided', () => {
        renderWithIntl(
            <BriefCreativePreview preview={mockPreview} loading={false} error={null} brandName="Acme" />,
        )
        expect(screen.queryByRole('button', { name: /edit campaign goal/i })).not.toBeInTheDocument()
    })
})