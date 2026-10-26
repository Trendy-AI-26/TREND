import { cleanup, renderHook } from '@testing-library/react'
import { NextIntlClientProvider } from 'next-intl'
import { afterEach, describe, expect, it } from 'vitest'
import { useAdminFormat } from './shared'

afterEach(cleanup)

describe('useAdminFormat percent', () => {
  it.each(['en', 'ar'])('formats a 0–1 fraction as a percentage in %s', locale => {
    function wrapper({ children }: { children: React.ReactNode }) {
      return <NextIntlClientProvider locale={locale} messages={{}}>{children}</NextIntlClientProvider>
    }
    const { result } = renderHook(() => useAdminFormat(), { wrapper })
    const expected = new Intl.NumberFormat(locale, {
      style: 'percent',
      maximumFractionDigits: 2,
    }).format(0.95)

    expect(result.current.percent(0.95)).toBe(expected)
    if (locale === 'en') expect(result.current.percent(0.95)).toBe('95%')
    expect(result.current.percent(null)).toBe('—')
  })
})
