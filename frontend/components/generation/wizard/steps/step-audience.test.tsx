import { useState } from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { NextIntlClientProvider } from 'next-intl'
import { describe, expect, it } from 'vitest'
import en from '@/messages/en.json'
import ar from '@/messages/ar.json'
import { EMPTY_WIZARD_ANSWERS, validateAudienceStep } from '../wizard-types'
import { StepAudience } from './step-audience'

function AudienceForm() {
  const [value, setValue] = useState(EMPTY_WIZARD_ANSWERS.audience)
  return <StepAudience value={value} onChange={setValue} errors={validateAudienceStep(value)} />
}

describe('Audience step', () => {
  it('shows optional audience choices and country only for Specific country', () => {
    render(
      <NextIntlClientProvider locale="en" messages={en}>
        <AudienceForm />
      </NextIntlClientProvider>,
    )

    expect(screen.getByRole('button', { name: 'Companies (business customers)' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Business owners (individuals)' })).toBeInTheDocument()
    expect(screen.getAllByText('(optional)')).toHaveLength(4)
    expect(screen.queryByPlaceholderText('Write the country name...')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('radio', { name: 'Specific country' }))
    expect(screen.getByPlaceholderText('Write the country name...')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('radio', { name: 'Global' }))
    expect(screen.queryByPlaceholderText('Write the country name...')).not.toBeInTheDocument()
  })

  it('distinguishes companies from individual business owners in Arabic', () => {
    render(
      <NextIntlClientProvider locale="ar" messages={ar}>
        <AudienceForm />
      </NextIntlClientProvider>,
    )

    expect(screen.getByRole('button', { name: 'شركات (عملاء من مؤسسات)' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'أصحاب مشاريع (أفراد)' })).toBeInTheDocument()
  })
})
