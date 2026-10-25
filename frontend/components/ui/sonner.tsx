'use client'

import { Toaster as Sonner } from 'sonner'
import { useLocale } from 'next-intl'

/**
 * The single toast host of the app. Direction follows the active locale
 * (Arabic is RTL) and the text uses the same font as the rest of the UI.
 */
export function Toaster() {
  const locale = useLocale()
  const dir = locale === 'ar' ? 'rtl' : 'ltr'

  return (
    <Sonner
      dir={dir}
      position="top-center"
      richColors
      closeButton
      style={{ fontFamily: 'var(--font-sans), var(--font-arabic), ui-sans-serif, system-ui, sans-serif' }}
      toastOptions={{ style: { fontFamily: 'inherit' } }}
    />
  )
}
