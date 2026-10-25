import { useState } from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { NextIntlClientProvider } from 'next-intl'
import { describe, expect, it } from 'vitest'
import en from '@/messages/en.json'
import ar from '@/messages/ar.json'
import { buildGenerateRequest } from '../build-request'
import { EMPTY_WIZARD_ANSWERS, validatePlatformStep } from '../wizard-types'
import { StepPlatform } from './step-platform'

function PlatformForm() {
  const [value, setValue] = useState(EMPTY_WIZARD_ANSWERS.platform)
  return <StepPlatform value={value} onChange={setValue} errors={validatePlatformStep(value)} />
}

function notesInRequest(notes: string) {
  return buildGenerateRequest({
    answers: {
      ...EMPTY_WIZARD_ANSWERS,
      platform: { ...EMPTY_WIZARD_ANSWERS.platform, notes },
    },
    brandHasLogo: false,
    locale: 'en',
    productAssetId: null,
  }).brief.optional_notes
}

describe('Platform and Output notes', () => {
  it('accepts empty notes and includes only nonblank notes in the existing brief', () => {
    expect(validatePlatformStep(EMPTY_WIZARD_ANSWERS.platform)).toEqual({})
    expect(notesInRequest('')).toBeNull()
    expect(notesInRequest('   ')).toBeNull()
    expect(notesInRequest(' Offer ends Friday. ')).toBe(
      'Additional notes from the user: Offer ends Friday.',
    )
  })

  it('shows one optional notes field while retaining preset and caption controls', () => {
    render(
      <NextIntlClientProvider locale="en" messages={en}>
        <PlatformForm />
      </NextIntlClientProvider>,
    )

    expect(screen.getByRole('radiogroup', { name: 'Platform & size' })).toBeInTheDocument()
    expect(screen.getByText('Generate a caption with the image?')).toBeInTheDocument()
    expect(screen.getByText(/confirmed factual constraints or things to avoid/)).toBeInTheDocument()
    expect(screen.getByLabelText('Additional notes')).toBeInTheDocument()
    expect(screen.queryByRole('radiogroup', { name: 'Additional notes' })).not.toBeInTheDocument()

    fireEvent.change(screen.getByLabelText('Additional notes'), { target: { value: 'Avoid free shipping' } })
    expect(screen.getByLabelText('Additional notes')).toHaveValue('Avoid free shipping')
  })

  it('provides Arabic guidance for factual constraints', () => {
    render(
      <NextIntlClientProvider locale="ar" messages={ar}>
        <PlatformForm />
      </NextIntlClientProvider>,
    )
    expect(screen.getByText(/الحقائق المؤكدة/)).toBeInTheDocument()
  })
})
