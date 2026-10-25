import { useState } from 'react'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { NextIntlClientProvider } from 'next-intl'
import { describe, expect, it, vi } from 'vitest'
import en from '@/messages/en.json'
import ar from '@/messages/ar.json'
import { EMPTY_WIZARD_ANSWERS, validateStyleStep, type StyleStepAnswers } from '../wizard-types'
import { StepStyle } from './step-style'

const basicStyle: StyleStepAnswers = {
  ...EMPTY_WIZARD_ANSWERS.style,
  visualStyle: 'modern',
  feeling: 'trust',
  hasProductPhotos: 'no',
}

function StyleForm({ brandHasLogo = false }: { brandHasLogo?: boolean }) {
  const [value, setValue] = useState(EMPTY_WIZARD_ANSWERS.style)
  return (
    <StepStyle
      value={value}
      onChange={setValue}
      errors={validateStyleStep(value, brandHasLogo)}
      brandId="brand-1"
      brandHasLogo={brandHasLogo}
    />
  )
}

describe('Style and Identity step', () => {
  it('requires tone, preserves logo rules, and keeps occasion optional', () => {
    expect(validateStyleStep(basicStyle, false)).toEqual({})
    expect(validateStyleStep({ ...basicStyle, feeling: '' }, false)).toEqual({
      feeling: 'error_required_choice',
    })
    expect(validateStyleStep(basicStyle, true)).toEqual({
      logoPlacement: 'error_required_choice',
    })
  })

  it.each(['yes', 'yes_needs_edit'] as const)('requires a file for %s', (choice) => {
    expect(validateStyleStep({ ...basicStyle, hasProductPhotos: choice }, false)).toEqual({
      productImage: 'error_product_image_required',
    })
    const productImage = new File(['image'], 'product.png', { type: 'image/png' })
    expect(validateStyleStep({ ...basicStyle, hasProductPhotos: choice, productImage }, false)).toEqual({})
  })

  it('separates visual style and message tone and shows upload only for reference choices', () => {
    render(
      <NextIntlClientProvider locale="en" messages={en}>
        <StyleForm />
      </NextIntlClientProvider>,
    )

    expect(screen.getByText(/visual style of the image/)).toBeInTheDocument()
    expect(screen.getByText(/feeling the message should create/)).toBeInTheDocument()
    expect(screen.queryByText('Product reference image')).not.toBeInTheDocument()

    const photoChoices = screen.getByRole('radiogroup', { name: 'Use an uploaded product reference image?' })
    fireEvent.click(within(photoChoices).getByRole('radio', { name: 'Upload and use as the product reference' }))
    expect(screen.getByText('Product reference image')).toBeInTheDocument()
    expect(screen.getByText('Upload a product image or choose to generate without one.')).toBeInTheDocument()
    fireEvent.click(within(photoChoices).getByRole('radio', { name: 'Generate without a product reference image' }))
    expect(screen.queryByText('Product reference image')).not.toBeInTheDocument()
  })

  it('provides corresponding Arabic guidance', () => {
    render(
      <NextIntlClientProvider locale="ar" messages={ar}>
        <StyleForm />
      </NextIntlClientProvider>,
    )
    expect(screen.getByText(/الأسلوب البصري للصورة/)).toBeInTheDocument()
    expect(screen.getByText(/إحساس الرسالة/)).toBeInTheDocument()
  })

  it('clears an existing reference file when switching to no reference', () => {
    Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: vi.fn(() => 'blob:test') })
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: vi.fn() })
    const productImage = new File(['image'], 'product.png', { type: 'image/png' })
    const value = { ...basicStyle, hasProductPhotos: 'yes' as const, productImage }
    const onChange = vi.fn()
    render(
      <NextIntlClientProvider locale="en" messages={en}>
        <StepStyle value={value} onChange={onChange} errors={{}} brandId="brand-1" brandHasLogo={false} />
      </NextIntlClientProvider>,
    )

    const photoChoices = screen.getByRole('radiogroup', { name: 'Use an uploaded product reference image?' })
    fireEvent.click(within(photoChoices).getByRole('radio', { name: 'Generate without a product reference image' }))
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({
      hasProductPhotos: 'no',
      productImage: null,
    }))
  })
})
