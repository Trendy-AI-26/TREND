import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { NextIntlClientProvider } from 'next-intl'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import en from '@/messages/en.json'
import { toast } from 'sonner'
import { StepLogo } from './step-logo'

const { apiRequestMock } = vi.hoisted(() => ({ apiRequestMock: vi.fn() }))
vi.mock('@/lib/api', () => ({ apiRequest: apiRequestMock }))
vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }))

function renderStep(onLogoChange = vi.fn(), onAssetChange = vi.fn()) {
  render(
    <NextIntlClientProvider locale="en" messages={en}>
      <StepLogo brandId="brand-1" brandName="Acme" logoUrl={null} onLogoChange={onLogoChange} productAssetId={null} onAssetChange={onAssetChange} />
    </NextIntlClientProvider>,
  )
}

describe('Brand Kit asset uploads', () => {
  beforeEach(() => apiRequestMock.mockReset())

  it('uploads a logo through the brand logo endpoint without selecting a product', async () => {
    const onLogoChange = vi.fn()
    const onAssetChange = vi.fn()
    apiRequestMock.mockResolvedValueOnce({ logo_url: 'http://localhost/logo.png' })
    renderStep(onLogoChange, onAssetChange)

    expect(screen.getByText(/Product reference image \(optional\)/)).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Brand logo (optional)'), {
      target: { files: [new File(['logo'], 'logo.png', { type: 'image/png' })] },
    })

    await waitFor(() => expect(onLogoChange).toHaveBeenCalledWith('http://localhost/logo.png'))
    expect(apiRequestMock).toHaveBeenCalledWith('/brands/brand-1/logo', expect.objectContaining({ method: 'POST' }))
    expect(onAssetChange).not.toHaveBeenCalled()
  })

  it('keeps product uploads on the product asset endpoint', async () => {
    const onLogoChange = vi.fn()
    const onAssetChange = vi.fn()
    apiRequestMock.mockResolvedValueOnce({ id: 'asset-1', image_url: 'http://localhost/product.png' })
    renderStep(onLogoChange, onAssetChange)

    fireEvent.change(screen.getByLabelText('Product reference image (optional)'), {
      target: { files: [new File(['product'], 'product.png', { type: 'image/png' })] },
    })

    await waitFor(() => expect(onAssetChange).toHaveBeenCalledWith('asset-1'))
    expect(apiRequestMock).toHaveBeenCalledWith('/brands/brand-1/product-assets', expect.objectContaining({ method: 'POST' }))
    expect(onLogoChange).not.toHaveBeenCalled()
  })

  it('does not mark a failed logo upload as successful', async () => {
    const onLogoChange = vi.fn()
    apiRequestMock.mockRejectedValueOnce(new Error('Upload failed'))
    renderStep(onLogoChange)
    fireEvent.change(screen.getByLabelText('Brand logo (optional)'), {
      target: { files: [new File(['logo'], 'logo.png', { type: 'image/png' })] },
    })
    await waitFor(() => expect(toast.error).toHaveBeenCalled())
    expect(onLogoChange).not.toHaveBeenCalled()
  })
})
