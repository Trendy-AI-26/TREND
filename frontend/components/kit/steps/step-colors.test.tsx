import { fireEvent, render, screen } from '@testing-library/react'
import { NextIntlClientProvider } from 'next-intl'
import { describe, expect, it, vi } from 'vitest'
import en from '@/messages/en.json'
import type { KitAnswers } from '@/types'
import { StepColors } from './step-colors'

const answers = (colors: string[]): KitAnswers => ({
  product_asset_id: null, tagline: null, audience: null,
  colors, avoid_words: null, industry: null,
})

describe('Brand Kit palette', () => {
  it('adds a fourth color in order and blocks a fifth', () => {
    const onChange = vi.fn()
    const original = ['#111111', '#222222', '#333333']
    const { rerender } = render(
      <NextIntlClientProvider locale="en" messages={en}>
        <StepColors answers={answers(original)} onChange={onChange} />
      </NextIntlClientProvider>,
    )

    fireEvent.click(screen.getByRole('button', { name: 'Add color' }))
    expect(onChange).toHaveBeenCalledWith({ colors: [...original, '#334155'] })
    expect(original).toEqual(['#111111', '#222222', '#333333'])

    rerender(
      <NextIntlClientProvider locale="en" messages={en}>
        <StepColors answers={answers([...original, '#334155'])} onChange={onChange} />
      </NextIntlClientProvider>,
    )
    expect(screen.getByRole('button', { name: 'Add color' })).toBeDisabled()
    onChange.mockClear()
    fireEvent.click(screen.getByRole('button', { name: 'Add color' }))
    expect(onChange).not.toHaveBeenCalled()
  })

  it('reorders four colors when the fourth becomes primary', () => {
    const onChange = vi.fn()
    render(
      <NextIntlClientProvider locale="en" messages={en}>
        <StepColors answers={answers(['#111111', '#222222', '#333333', '#444444'])} onChange={onChange} />
      </NextIntlClientProvider>,
    )
    fireEvent.click(screen.getAllByRole('button', { name: 'Make primary' })[2])
    expect(onChange).toHaveBeenCalledWith({ colors: ['#444444', '#111111', '#222222', '#333333'] })
  })
})
