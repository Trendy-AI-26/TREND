import { render, screen } from '@testing-library/react'
import { NextIntlClientProvider } from 'next-intl'
import { describe, expect, it, vi } from 'vitest'
import en from '@/messages/en.json'
import { StepReview } from './step-review'

describe('Brand Kit review palette', () => {
  it('displays all four saved colors', () => {
    const colors = ['#111111', '#222222', '#333333', '#444444']
    render(
      <NextIntlClientProvider locale="en" messages={en}>
        <StepReview brandId="brand-1" brandName="Acme" logoUrl={null}
          savedStatus="complete" isDirty={false} onChange={vi.fn()}
          answers={{ product_asset_id: null, tagline: null, audience: 'Everyone', colors, avoid_words: null, industry: 'retail' }} />
      </NextIntlClientProvider>,
    )
    for (const color of colors) expect(screen.getByTitle(color)).toBeInTheDocument()
  })
})
