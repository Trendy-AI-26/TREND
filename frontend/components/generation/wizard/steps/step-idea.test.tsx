import { useState } from 'react'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { NextIntlClientProvider } from 'next-intl'
import { describe, expect, it } from 'vitest'
import messages from '@/messages/en.json'
import { buildGenerateRequest } from '../build-request'
import { EMPTY_WIZARD_ANSWERS, validateIdeaStep, type IdeaStepAnswers } from '../wizard-types'
import { StepIdea } from './step-idea'

const requiredAnswers: IdeaStepAnswers = {
  ...EMPTY_WIZARD_ANSWERS.idea,
  coreIdea: 'Confirmed spring offer',
  offering: 'product',
  goal: 'sales_conversion',
  textLanguage: 'en',
}

function IdeaForm() {
  const [value, setValue] = useState(EMPTY_WIZARD_ANSWERS.idea)
  return <StepIdea value={value} onChange={setValue} errors={validateIdeaStep(value)} />
}

describe('Post Idea CTA and guidance', () => {
  it('defaults to no CTA and allows an omitted CTA or image text', () => {
    expect(EMPTY_WIZARD_ANSWERS.idea.cta).toBe('none')
    expect(validateIdeaStep(requiredAnswers)).toEqual({})
    expect(validateIdeaStep({ ...requiredAnswers, cta: '' })).toEqual({})

    const request = buildGenerateRequest({
      answers: { ...EMPTY_WIZARD_ANSWERS, idea: requiredAnswers },
      brandHasLogo: false,
      locale: 'en',
      productAssetId: null,
    })
    expect(request.brief.text_to_include).toBeNull()
  })

  it('requires text only for a custom CTA', () => {
    expect(validateIdeaStep({ ...requiredAnswers, cta: 'other' })).toEqual({
      ctaCustom: 'error_custom_required',
    })
    expect(validateIdeaStep({ ...requiredAnswers, cta: 'other', ctaCustom: 'Call us' })).toEqual({})
  })

  it('explains campaign facts and visible text, and shows custom input only for Other', () => {
    render(
      <NextIntlClientProvider locale="en" messages={messages}>
        <IdeaForm />
      </NextIntlClientProvider>,
    )

    expect(screen.getByText(/Include only confirmed facts/)).toBeInTheDocument()
    expect(screen.getByText(/words you want visible in the design/)).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: 'No CTA' })).toHaveAttribute('aria-checked', 'true')
    expect(screen.queryByPlaceholderText('Write your call to action...')).not.toBeInTheDocument()

    const ctaChoices = screen.getByRole('radiogroup', { name: 'Call to action in the image' })
    fireEvent.click(within(ctaChoices).getByRole('radio', { name: 'Other' }))
    expect(screen.getByPlaceholderText('Write your call to action...')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('radio', { name: 'No CTA' }))
    expect(screen.queryByPlaceholderText('Write your call to action...')).not.toBeInTheDocument()
  })
})
