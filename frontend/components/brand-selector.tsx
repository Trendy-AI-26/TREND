'use client'

import { useTranslations } from 'next-intl';
import { useRouter } from 'next/navigation'
import { BrandListItem } from '@/types'

interface BrandSelectorProps {
  brands: BrandListItem[]
  currentBrandId?: string
}

export function BrandSelector({ brands, currentBrandId }: BrandSelectorProps) {
  const t = useTranslations('components.brand-selector');
  const router = useRouter()

  return (
    <select
      value={currentBrandId || ''}
      onChange={(e) => {
        if (e.target.value) {
          router.push(`/${e.target.value}`)
        }
      }}
      className="rounded-md border bg-white px-3 py-1.5 text-sm"
    >
      <option value="">{t('select_a_brand')}</option>
      {brands.map((brand) => (
        <option key={brand.id} value={brand.id}>
          {brand.name}
        </option>
      ))}
    </select>
  )
}
