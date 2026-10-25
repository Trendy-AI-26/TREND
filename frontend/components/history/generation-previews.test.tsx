import { render, screen } from '@testing-library/react'
import { NextIntlClientProvider } from 'next-intl'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import en from '@/messages/en.json'
import type { GenerationHistoryItem } from '@/types'
import { BrandDashboard } from '@/components/brand/brand-dashboard'
import { LibraryView } from './library-view'

const mockState = vi.hoisted(() => ({
  items: [] as GenerationHistoryItem[],
  push: vi.fn(),
}))

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: mockState.push }),
  useSearchParams: () => new URLSearchParams(),
}))
vi.mock('@/hooks/use-generation-history', () => ({
  useGenerationHistory: () => ({
    items: mockState.items, loading: false, loadingMore: false, error: null,
    hasNext: false, loadMore: vi.fn(), removeItem: vi.fn(),
  }),
}))
vi.mock('@/hooks/use-brand', () => ({
  useBrand: () => ({ brand: { id: 'brand-1', name: 'Acme', logo_url: null }, loading: false, error: null }),
}))
vi.mock('@/hooks/use-kit', () => ({
  useKit: () => ({ kit: null, loading: false, error: null }),
}))
vi.mock('@/hooks/use-profile', () => ({
  useProfile: () => ({ profile: null }),
}))
vi.mock('@/hooks/use-brands', () => ({
  useBrands: () => ({ brands: [] }),
}))
vi.mock('@/hooks/use-quota', () => ({
  useQuota: () => ({ quota: null, loading: true, error: null, refetch: vi.fn() }),
}))
vi.mock('@/hooks/use-delete-generation', () => ({
  useDeleteGeneration: () => ({ deleteGeneration: vi.fn() }),
}))

function historyItem(platform_preset: GenerationHistoryItem['platform_preset'], width: number, height: number): GenerationHistoryItem {
  return {
    id: 'generation-1', prompt_excerpt: 'Campaign image', provider: 'openai',
    model: 'gpt-image-2', platform_preset, width, height, logo_mode: 'none',
    status: 'succeeded', image_url: 'https://example.com/generated.png',
    error_message: null, created_at: '2026-10-25T10:00:00Z', completed_at: '2026-10-25T10:01:00Z',
  }
}

function renderPreview(view: 'dashboard' | 'library') {
  return render(
    <NextIntlClientProvider locale="en" messages={en}>
      {view === 'dashboard' ? <BrandDashboard brandId="brand-1" /> : <LibraryView brandId="brand-1" />}
    </NextIntlClientProvider>,
  )
}

beforeEach(() => {
  mockState.items = []
  mockState.push.mockClear()
})

describe.each(['dashboard', 'library'] as const)('%s generated-image previews', (view) => {
  it.each([
    ['instagram_post', 1080, 1080],
    ['instagram_story', 1080, 1920],
    ['facebook_post', 1200, 630],
    ['linkedin_banner', 1584, 396],
  ] as const)('shows the full %s image in its fixed card and links to details', (preset, width, height) => {
    mockState.items = [historyItem(preset, width, height)]
    renderPreview(view)

    const image = screen.getByRole('img', { name: 'Campaign image' })
    expect(image).toHaveAttribute('src', 'https://example.com/generated.png')
    expect(image).toHaveClass('object-contain', 'h-full', 'w-full')
    expect(image).not.toHaveClass('object-cover')
    expect(image.parentElement).toHaveClass('bg-neutral-100')
    expect(image.closest('a')).toHaveAttribute('href', '/brand-1/history/generation-1')
  })

  it('keeps the missing-image fallback and detail navigation', () => {
    mockState.items = [{ ...historyItem('instagram_post', 1080, 1080), image_url: null }]
    renderPreview(view)

    expect(screen.queryByRole('img', { name: 'Campaign image' })).not.toBeInTheDocument()
    expect(screen.getAllByRole('link').some((link) =>
      link.getAttribute('href') === '/brand-1/history/generation-1',
    )).toBe(true)
  })
})
