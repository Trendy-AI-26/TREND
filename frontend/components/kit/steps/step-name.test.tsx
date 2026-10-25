import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { NextIntlClientProvider } from 'next-intl'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import en from '@/messages/en.json'
import ar from '@/messages/ar.json'
import { ApiError } from '@/lib/api'
import { StepName } from './step-name'

const { apiRequestMock } = vi.hoisted(() => ({ apiRequestMock: vi.fn() }))
vi.mock('@/lib/api', async (importOriginal) => ({ ...(await importOriginal<typeof import('@/lib/api')>()), apiRequest: apiRequestMock }))

const updatedBrand = { id: 'brand-1', name: 'New Name', logo_url: null, kit_status: 'complete', created_at: '2026-01-01', updated_at: '2026-01-02' }

function renderStep(onNameSaved = vi.fn(), locale: 'en' | 'ar' = 'en') {
  render(
    <NextIntlClientProvider locale={locale} messages={locale === 'en' ? en : ar}>
      <StepName brandId="brand-1" brandName="Acme" logoUrl={null} onNameSaved={onNameSaved} />
    </NextIntlClientProvider>,
  )
  return onNameSaved
}

describe('Brand Kit name editing', () => {
  beforeEach(() => apiRequestMock.mockReset())

  it('prefills the saved name and disables saving an unchanged name', () => {
    renderStep()
    expect(screen.getByRole('textbox', { name: 'Brand name' })).toHaveValue('Acme')
    expect(screen.getByText(/2 to 120 characters/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Save name' })).toBeDisabled()
  })

  it('allows clearing and rewriting but prevents empty, short, and long names', () => {
    renderStep()
    const input = screen.getByRole('textbox', { name: 'Brand name' })
    for (const name of ['', ' ', 'A', 'A'.repeat(121)]) {
      fireEvent.change(input, { target: { value: name } })
      expect(screen.getByRole('button', { name: 'Save name' })).toBeDisabled()
      expect(screen.getByRole('alert')).toHaveTextContent('Enter a brand name with 2 to 120 characters.')
    }
    fireEvent.change(input, { target: { value: '  Acme  ' } })
    expect(screen.getByRole('button', { name: 'Save name' })).toBeDisabled()
    expect(apiRequestMock).not.toHaveBeenCalled()
  })

  it('saves a trimmed valid name once and updates the saved display only on success', async () => {
    let resolveRequest!: (value: typeof updatedBrand) => void
    apiRequestMock.mockReturnValueOnce(new Promise((resolve) => { resolveRequest = resolve }))
    const onNameSaved = renderStep()
    fireEvent.change(screen.getByRole('textbox', { name: 'Brand name' }), { target: { value: '  New Name  ' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save name' }))
    expect(screen.getByRole('button', { name: 'Saving name…' })).toBeDisabled()
    expect(screen.getByText('Acme')).toBeInTheDocument()
    expect(apiRequestMock).toHaveBeenCalledWith('/brands/brand-1', { method: 'PATCH', body: JSON.stringify({ name: 'New Name' }) })
    expect(apiRequestMock).toHaveBeenCalledTimes(1)
    resolveRequest(updatedBrand)
    await waitFor(() => expect(onNameSaved).toHaveBeenCalledWith(updatedBrand))
    expect(screen.getByRole('status')).toHaveTextContent('Brand name saved.')
  })

  it('shows the duplicate-name error without changing the saved name', async () => {
    apiRequestMock.mockRejectedValueOnce(new ApiError('Duplicate', 'DUPLICATE_BRAND_NAME', undefined, 409))
    const onNameSaved = renderStep()
    fireEvent.change(screen.getByRole('textbox', { name: 'Brand name' }), { target: { value: 'New Name' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save name' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('You already have a brand with this name')
    expect(screen.getByText('Acme')).toBeInTheDocument()
    expect(onNameSaved).not.toHaveBeenCalled()
  })

  it('shows a server failure and permits a retry', async () => {
    apiRequestMock.mockRejectedValueOnce(new ApiError('Server error', 'INTERNAL_ERROR', undefined, 500))
    const onNameSaved = renderStep()
    fireEvent.change(screen.getByRole('textbox', { name: 'Brand name' }), { target: { value: 'New Name' } })
    fireEvent.click(screen.getByRole('button', { name: 'Save name' }))
    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Save name' })).toBeEnabled()
    expect(onNameSaved).not.toHaveBeenCalled()
  })

  it('provides Arabic labeling and feedback', () => {
    renderStep(vi.fn(), 'ar')
    expect(screen.getByRole('textbox', { name: 'اسم العلامة التجارية' })).toHaveAttribute('dir', 'auto')
    expect(screen.getByText(/2 إلى 120/)).toBeInTheDocument()
  })
})
