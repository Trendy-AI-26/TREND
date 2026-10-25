import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { NextIntlClientProvider } from 'next-intl'
import { describe, expect, it, vi } from 'vitest'
import en from '@/messages/en.json'
import { KitWizard } from './kit-wizard'

const { apiRequestMock, updateBrandMock, refetchMock, refreshMock, saveKitMock } = vi.hoisted(() => ({
  apiRequestMock: vi.fn(), updateBrandMock: vi.fn(), refetchMock: vi.fn().mockResolvedValue(undefined),
  refreshMock: vi.fn(), saveKitMock: vi.fn(),
}))
vi.mock('@/lib/api', () => ({ apiRequest: apiRequestMock }))
vi.mock('next/navigation', () => ({ useRouter: () => ({ refresh: refreshMock, push: vi.fn() }) }))
vi.mock('@/hooks/use-brands', () => ({ useBrands: () => ({ updateBrand: updateBrandMock, refetch: refetchMock, setAccent: vi.fn() }) }))
vi.mock('@/hooks/use-brand', () => ({ useBrand: () => ({ brand: { logo_url: null } }) }))
vi.mock('@/hooks/use-kit', () => ({ saveKit: saveKitMock }))
vi.mock('@/components/ui/confirm-dialog', () => ({ useConfirm: () => vi.fn() }))
vi.mock('./steps/step-logo', () => ({ StepLogo: () => <div>Logo step</div> }))

describe('Brand Kit rename state', () => {
  it('updates the Kit and shared brand state without saving Kit answers', async () => {
    apiRequestMock.mockReset()
    updateBrandMock.mockClear()
    refetchMock.mockClear()
    refreshMock.mockClear()
    saveKitMock.mockClear()
    const brand = { id: 'brand-1', name: 'New Name', logo_url: null, kit_status: 'complete', created_at: '2026-01-01', updated_at: '2026-01-02' }
    apiRequestMock.mockResolvedValueOnce(brand)
    render(
      <NextIntlClientProvider locale="en" messages={en}>
        <KitWizard brandId="brand-1" brandName="Acme" initialKit={{
          brand_id: 'brand-1', brand_name: 'Acme', status: 'complete', summary: null,
          completed_at: null, updated_at: null,
          answers: { product_asset_id: null, tagline: null, audience: 'Everyone', colors: ['#112233'], avoid_words: null, industry: 'retail' },
        }} />
      </NextIntlClientProvider>,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Continue' }))
    fireEvent.change(screen.getByRole('textbox', { name: 'Brand name' }), { target: { value: 'New Name' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save name' }))

    await waitFor(() => expect(updateBrandMock).toHaveBeenCalledWith(brand))
    expect(refetchMock).toHaveBeenCalled()
    expect(refreshMock).toHaveBeenCalled()
    expect(screen.getByRole('textbox', { name: 'Brand name' })).toHaveValue('New Name')
    expect(saveKitMock).not.toHaveBeenCalled()
  })
})
