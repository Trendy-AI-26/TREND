import { render, screen } from '@testing-library/react'
import { NextIntlClientProvider } from 'next-intl'
import { describe, expect, it, vi } from 'vitest'
import en from '@/messages/en.json'
import type { BrandListItem } from '@/types'
import { AppSidebar } from './app-sidebar'

vi.mock('next/navigation', () => ({
  usePathname: () => '/brand-1/kit',
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}))

const brand: BrandListItem = {
  id: 'brand-1', name: 'Acme', logo_url: 'http://localhost/logo.png',
  kit_status: 'complete', created_at: '2026-01-01',
}

function renderSidebar(withLogo: boolean, collapsed: boolean) {
  return render(
    <NextIntlClientProvider locale="en" messages={{ ...en, layout: { 'app-shell': { close_menu: 'Close menu' } } }}>
      <AppSidebar brands={[{ ...brand, logo_url: withLogo ? brand.logo_url : null }]} accents={{ 'brand-1': '#112233' }} currentBrandId="brand-1" profile={null} collapsed={collapsed} onCreateBrand={vi.fn()} />
    </NextIntlClientProvider>,
  )
}

describe('sidebar brand indicator', () => {
  it.each([false, true])('shows the logo when collapsed is %s', (collapsed) => {
    renderSidebar(true, collapsed)
    const logo = screen.getByTitle('Acme').querySelector('img')
    expect(logo).toHaveAttribute('src', 'http://localhost/logo.png')
    expect(logo).toHaveClass('object-contain')
  })

  it.each([false, true])('keeps the brand color fallback when collapsed is %s', (collapsed) => {
    renderSidebar(false, collapsed)
    const indicator = collapsed
      ? screen.getByTitle('Acme')
      : screen.getByRole('link', { name: 'Acme' }).querySelector('span[style]')!
    expect(indicator).toHaveStyle({ background: '#112233' })
    expect(indicator.querySelector('img')).toBeNull()
  })
})
