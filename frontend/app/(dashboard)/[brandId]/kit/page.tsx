'use client'

import { useTranslations } from 'next-intl';
import { useParams } from 'next/navigation'
import { useKit } from '@/hooks/use-kit'
import { KitWizard } from '@/components/kit/kit-wizard'

export default function KitPage() {
  const t = useTranslations('app.(dashboard).[brandId].kit.page');
  const params = useParams()
  const brandId = Array.isArray(params.brandId) ? params.brandId[0] : params.brandId ?? ''
  const { kit, loading, error } = useKit(brandId)

  if (loading) {
    return <p className="text-muted-foreground">{t('loading')}</p>
  }

  if (error || !kit) {
    return <p className="text-destructive">{t('failed_to_load_brand')}</p>
  }

  return <KitWizard brandId={brandId} brandName={kit.brand_name} initialKit={kit} />
}
