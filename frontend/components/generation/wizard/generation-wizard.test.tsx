import { fireEvent, render, screen, within } from '@testing-library/react'
import { NextIntlClientProvider } from 'next-intl'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import messages from '@/messages/en.json'
import { GenerationWizard } from './generation-wizard'

const { runMock } = vi.hoisted(() => ({ runMock: vi.fn() }))

vi.mock('next/navigation', () => ({ useRouter: () => ({ back: vi.fn() }) }))
vi.mock('@/hooks/use-notifications', () => ({ addGenerationNotification: vi.fn() }))
vi.mock('./use-wizard-generation', () => ({
  useWizardGeneration: () => ({ state: { status: 'idle' }, run: runMock, reset: vi.fn() }),
}))

function choose(group: string, option: string) {
  fireEvent.click(within(screen.getByRole('radiogroup', { name: group })).getByRole('radio', { name: option }))
}

function next() {
  fireEvent.click(screen.getByRole('button', { name: 'Next' }))
}

describe('four-step generation Wizard', () => {
  beforeEach(() => {
    runMock.mockReset()
    Object.defineProperty(window, 'scrollTo', { configurable: true, value: vi.fn() })
  })

  it('validates navigation and maps a complete brief with optional audience fields omitted', () => {
    render(
      <NextIntlClientProvider locale="en" messages={messages}>
        <GenerationWizard brandId="brand-1" brandName="Acme" brandHasLogo />
      </NextIntlClientProvider>,
    )

    expect(screen.getByRole('button', { name: /Audience/ })).toBeDisabled()
    next()
    expect(screen.getByText('Please write the post idea.')).toBeInTheDocument()

    fireEvent.change(screen.getByPlaceholderText('What are you promoting? Add any confirmed offer details...'), {
      target: { value: 'Confirmed spring offer' },
    })
    choose('What do you offer?', 'Product')
    choose('What is the goal of your post?', 'Increase sales')
    choose('Call to action in the image', 'Shop now')
    choose('Which language should the design text use?', 'Arabic and English together')
    fireEvent.change(screen.getByPlaceholderText('e.g. 20% off this week'), {
      target: { value: 'خصم 20% / 20% off' },
    })
    next()

    expect(screen.getByRole('button', { name: /Audience/ })).toHaveAttribute('aria-current', 'step')
    next()
    expect(screen.getByText('Choose at least one group.')).toBeInTheDocument()
    fireEvent.click(within(screen.getByRole('group', { name: 'Who is your target audience?' }))
      .getByRole('button', { name: 'Companies (business customers)' }))
    next()

    next()
    expect(screen.getAllByText('Please choose an option.').length).toBeGreaterThan(0)
    choose('How should the image look?', 'Modern')
    choose('What tone should the campaign convey?', 'Trust')
    choose('How should the logo appear?', 'Depends on the design')
    choose('Use an uploaded product reference image?', 'Upload and use as the product reference')
    next()
    expect(screen.getByText('Upload a product image or choose to generate without one.')).toBeInTheDocument()
    choose('Use an uploaded product reference image?', 'Generate without a product reference image')
    next()

    expect(screen.getByRole('button', { name: /Platform & output/ })).toHaveAttribute('aria-current', 'step')
    const caption = screen.getByRole('switch')
    expect(caption).toHaveAttribute('aria-checked', 'true')
    fireEvent.click(caption)
    expect(caption).toHaveAttribute('aria-checked', 'false')
    fireEvent.change(screen.getByLabelText('Additional notes'), {
      target: { value: 'Offer ends Friday. Avoid free shipping claims.' },
    })

    fireEvent.click(screen.getByRole('button', { name: 'Generate content' }))
    expect(runMock).toHaveBeenCalledOnce()
    const [file, buildRequest] = runMock.mock.calls[0]
    expect(file).toBeNull()
    const request = buildRequest(null)
    expect(request.brief.target_audience).toEqual({
      segments: ['custom'],
      location: null,
      age_range: null,
      gender_focus: null,
      details: 'Audience segment: businesses and organizations',
    })
    expect(request.brief.text_to_include).toBe('خصم 20% / 20% off\nتسوّق الآن')
    expect(request.brief.optional_notes).toContain('Arabic and English together')
    expect(request.brief.optional_notes).toContain('Offer ends Friday. Avoid free shipping claims.')
    expect(request.logo_mode).toBe('prompt')
    expect(request.logo_placement).toBe('auto')
    expect(request.product_asset_id).toBeNull()
    expect(request.product_edit_instruction).toBeNull()
  })
})
