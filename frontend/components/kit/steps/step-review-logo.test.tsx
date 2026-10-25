import { render, screen, waitFor } from '@testing-library/react'
import { NextIntlClientProvider } from 'next-intl'
import { describe, expect, it, vi } from 'vitest'
import en from '@/messages/en.json'
import { StepReview } from './step-review'

const { apiRequestMock } = vi.hoisted(() => ({ apiRequestMock: vi.fn() }))
vi.mock('@/lib/api', () => ({ apiRequest: apiRequestMock }))

describe('Brand Kit review assets', () => {
  it('shows the brand logo separately from the saved product reference', async () => {
    apiRequestMock.mockResolvedValue({ image_url: 'http://localhost/product.png' })
    render(
      <NextIntlClientProvider locale="en" messages={en}>
        <StepReview brandId="brand-1" brandName="Acme" logoUrl="http://localhost/logo.png" savedStatus="complete" isDirty={false} onChange={vi.fn()} answers={{
          product_asset_id: 'asset-1', tagline: null, audience: 'Everyone', colors: ['#112233'], avoid_words: null, industry: 'retail',
        }} />
      </NextIntlClientProvider>,
    )

    expect(screen.getByRole('img', { name: 'Brand logo for Acme' })).toHaveAttribute('src', 'http://localhost/logo.png')
    await waitFor(() => expect(screen.getByRole('img', { name: 'Product image for Acme' })).toHaveAttribute('src', 'http://localhost/product.png'))
    expect(apiRequestMock).toHaveBeenCalledWith('/brands/brand-1/product-assets/asset-1')
  })
})
