'use client'

import { Suspense, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { Plus, Sparkles } from 'lucide-react'
import { BrandDashboard } from '@/components/brand/brand-dashboard'
import { CreateBrandModal } from '@/components/brand/create-brand-modal'
import { Button } from '@/components/ui/button'
import { useBrands } from '@/hooks/use-brands'

function DashboardContent() {
  const { brands, loading, error, addBrand } = useBrands()
  const searchParams = useSearchParams()
  const brandIdParam = searchParams.get('brandId')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const t = useTranslations('app.(dashboard).[brandId].page')
  const tBrands = useTranslations('app.(dashboard).brands.page')

  if (loading) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <p className="text-[14px] text-brand-headline/50">{t('loading')}</p>
      </div>
    )
  }

  if (error) {
    return (
      <div
        role="alert"
        className="mx-auto max-w-[1120px] rounded-xl border border-destructive/20 bg-destructive/5 px-4 py-3 text-[13px] text-destructive"
      >
        {error}
      </div>
    )
  }

  const selectedBrand =
    (brandIdParam ? brands.find((brand) => brand && brand.id === brandIdParam) : null) ??
    brands.find((brand) => brand && brand.id)

  if (!selectedBrand) {
    return (
      <div className="mx-auto flex min-h-[400px] max-w-[600px] flex-col items-center justify-center p-6 text-center">
        <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-weaker text-brand-primary">
          <Sparkles className="h-8 w-8" />
        </div>
        <h2 className="font-heading text-[22px] font-bold text-brand-headline">
          {tBrands('no_studios_yet')}
        </h2>
        <p className="mt-2 text-[14px] text-brand-headline/60">
          {tBrands('create_your_first_brand')}
        </p>
        <Button
          type="button"
          onClick={() => setShowCreateModal(true)}
          className="mt-6 gap-2"
        >
          <Plus className="h-4 w-4" />
          {tBrands('create_brand2')}
        </Button>
        <CreateBrandModal
          open={showCreateModal}
          onOpenChange={setShowCreateModal}
          onBrandCreated={(brand) => {
            addBrand(brand)
            setShowCreateModal(false)
          }}
        />
      </div>
    )
  }

  return <BrandDashboard key={selectedBrand.id} brandId={selectedBrand.id} />
}

export default function DashboardPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[400px] items-center justify-center">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-brand-primary border-t-transparent" />
        </div>
      }
    >
      <DashboardContent />
    </Suspense>
  )
}
