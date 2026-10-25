import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { NextIntlClientProvider } from 'next-intl'
import { describe, expect, it, vi } from 'vitest'
import en from '@/messages/en.json'
import { KitWizard } from './kit-wizard'

const { updateBrandMock, refetchMock, refreshMock } = vi.hoisted(() => ({
  updateBrandMock: vi.fn(), refetchMock: vi.fn().mockResolvedValue(undefined), refreshMock: vi.fn(),
}))
vi.mock('next/navigation', () => ({ useRouter: () => ({ refresh: refreshMock, push: vi.fn() }) }))
vi.mock('@/hooks/use-brands', () => ({ useBrands: () => ({ updateBrand: updateBrandMock, refetch: refetchMock, setAccent: vi.fn() }) }))
vi.mock('@/hooks/use-brand', () => ({ useBrand: () => ({ brand: { logo_url: null } }) }))
vi.mock('@/components/ui/confirm-dialog', () => ({ useConfirm: () => vi.fn() }))
vi.mock('./steps/step-logo', () => ({ StepLogo: ({ onLogoChange }: { onLogoChange: (url: string) => void }) => (
  <button onClick={() => onLogoChange('http://localhost/logo.png')}>Simulate completed logo upload</button>
) }))

describe('Brand Kit logo state', () => {
  it('refreshes shared brand state after a successful logo upload', async () => {
    updateBrandMock.mockClear()
    refetchMock.mockClear()
    refreshMock.mockClear()
    render(
      <NextIntlClientProvider locale="en" messages={en}>
        <KitWizard brandId="brand-1" brandName="Acme" initialKit={{
          brand_id: 'brand-1', brand_name: 'Acme', status: 'not_started', summary: null,
          completed_at: null, updated_at: null,
          answers: { product_asset_id: null, tagline: null, audience: null, colors: [], avoid_words: null, industry: null },
        }} />
      </NextIntlClientProvider>,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Simulate completed logo upload' }))
    expect(updateBrandMock).toHaveBeenCalledWith({ id: 'brand-1', logo_url: 'http://localhost/logo.png' })
    await waitFor(() => expect(refetchMock).toHaveBeenCalled())
    expect(refreshMock).toHaveBeenCalled()
  })
})
