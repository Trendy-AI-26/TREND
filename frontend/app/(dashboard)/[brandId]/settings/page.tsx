'use client'

import { useTranslations } from 'next-intl'
import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { Upload } from 'lucide-react'
import { useParams, useRouter } from 'next/navigation'
import { useBrand } from '@/hooks/use-brand'
import { useBrands } from '@/hooks/use-brands'
import { apiRequest } from '@/lib/api'
import { errorMessage } from '@/lib/errors'
import { toast } from 'sonner'
import { DeleteBrandDialog } from '@/components/brand/delete-brand-dialog'
import { BrandDot } from '@/components/brand/brand-dot'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import type { Brand, LogoUploadResponse } from '@/types'

export default function BrandSettingsPage() {
  const t = useTranslations('app.(dashboard).[brandId].settings.page')
  const tt = useTranslations('toasts')
  const te = useTranslations('errors')
  const params = useParams()
  const router = useRouter()
  const brandId = Array.isArray(params.brandId) ? params.brandId[0] : params.brandId ?? ''
  const { brand, loading, error, mutate } = useBrand(brandId)
  const { updateBrand, removeBrand, accents } = useBrands()
  const [newName, setNewName] = useState('')
  const [renameLoading, setRenameLoading] = useState(false)
  const [logoLoading, setLogoLoading] = useState(false)
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const nameDirty = useRef(false)

  useEffect(() => {
    if (brand && !nameDirty.current) setNewName(brand.name)
  }, [brand])

  if (loading) return <p className="font-tajawal text-muted-foreground">{t('loading')}</p>
  if (error || !brand) return <p className="font-tajawal text-destructive">{t('failed_to_load_brand')}</p>

  const handleRename = async () => {
    setRenameLoading(true)
    try {
      const updated = await apiRequest<Brand>(`/brands/${brandId}`, { method: 'PATCH', body: JSON.stringify({ name: newName.trim() }) })
      mutate(updated)
      updateBrand(updated)
      nameDirty.current = false
      toast.success(tt('brandRenamed'))
    } catch (err) {
      toast.error(errorMessage(err, te))
    } finally {
      setRenameLoading(false)
    }
  }

  const handleLogoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setLogoLoading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const result = await apiRequest<LogoUploadResponse>(`/brands/${brandId}/logo`, { method: 'POST', body: formData })
      const updatedBrand = { ...brand, logo_url: result.logo_url }
      mutate(updatedBrand)
      updateBrand(updatedBrand)
      toast.success(tt('logoUploaded'))
    } catch (err) {
      toast.error(errorMessage(err, te))
    } finally {
      setLogoLoading(false)
      e.target.value = ''
    }
  }

  const handleLogoRemove = async () => {
    setLogoLoading(true)
    try {
      await apiRequest(`/brands/${brandId}/logo`, { method: 'DELETE' })
      const updatedBrand = { ...brand, logo_url: null }
      mutate(updatedBrand)
      updateBrand(updatedBrand)
      toast.success(tt('logoRemoved'))
    } catch (err) {
      toast.error(errorMessage(err, te))
    } finally {
      setLogoLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-[870px] space-y-5 pb-10 pt-4">
      <header className="border-b border-brand-accent/25 pb-2">
        <h1 className="font-el-messiri text-[32px] font-semibold leading-tight text-brand-headline">{t('settings')}</h1>
        <nav className="mt-3 flex items-center gap-7 font-tajawal text-[14px]" aria-label={t('settings')}>
          <Link href="/account" className="border-b-2 border-transparent pb-2.5 text-brand-headline/60 no-underline hover:text-brand-primary">{t('account_tab')}</Link>
          <Link href={`/${brandId}/settings`} className="border-b-2 border-brand-primary pb-2.5 font-semibold text-brand-primary no-underline">{t('settings')}</Link>
        </nav>
      </header>

      <Card className="rounded-2xl border-[#e2e7ed] bg-white shadow-sm">
        <CardContent className="space-y-3 px-6 py-6">
          <CardTitle className="font-tajawal text-[16px] font-semibold text-brand-headline">{t('brand_name')}</CardTitle>
          <div dir="ltr" className="flex flex-col gap-3 sm:flex-row">
            <Input type="text" value={newName} onChange={(e) => { setNewName(e.target.value); nameDirty.current = true }} dir="rtl" className="h-11 rounded-lg border-[#dce2e9] font-tajawal" />
            <Button type="button" onClick={handleRename} disabled={renameLoading || !newName.trim()} size="lg" className="h-11 rounded-lg px-5 font-tajawal">
              {renameLoading ? t('saving') : t('save')}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-2xl border-[#e2e7ed] bg-white shadow-sm">
        <CardContent className="space-y-4 px-6 py-6">
          <CardTitle className="font-tajawal text-[16px] font-semibold text-brand-headline">{t('brand_logo')}</CardTitle>
          <div className="flex items-center justify-between gap-4">
            <div dir="rtl" className="flex flex-wrap items-center justify-end gap-3">
              <label className="inline-flex h-11 w-fit cursor-pointer items-center gap-2 rounded-lg border border-[#dce2e9] bg-white px-4 font-tajawal text-[13px] font-medium text-brand-headline shadow-sm transition hover:border-brand-primary hover:text-brand-primary">
                <Upload className="h-4 w-4" />
                {logoLoading ? t('uploading') : t('upload_logo')}
                <input type="file" accept="image/png,image/jpeg,image/webp" onChange={handleLogoUpload} disabled={logoLoading} className="hidden" />
              </label>
              <p className="font-tajawal text-[12px] text-muted-foreground">{t('png_jpg_or_webp')}</p>
              {brand.logo_url && <button type="button" onClick={handleLogoRemove} disabled={logoLoading} className="w-fit font-tajawal text-[13px] text-destructive hover:underline disabled:opacity-50">{t('remove_logo')}</button>}
            </div>
            <BrandDot color={accents[brandId]} logoUrl={brand.logo_url} name={brand.name} size={48} />
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-2xl border-[#f4dada] bg-white shadow-none">
        <CardContent className="space-y-2 px-6 py-6">
          <CardTitle className="font-tajawal text-[16px] font-semibold text-destructive">{t('danger_zone')}</CardTitle>
          <p className="font-tajawal text-[12px] text-muted-foreground">{t('permanently_delete_this_brand')}</p>
          <div dir="ltr" className="flex justify-end pt-1">
            <Button type="button" className="h-11 rounded-lg font-tajawal" onClick={() => setShowDeleteDialog(true)}>
              {t('delete_brand')}
            </Button>
          </div>
        </CardContent>
      </Card>

      <DeleteBrandDialog
        brand={brand}
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        onBrandDeleted={() => { removeBrand(brandId); router.push('/dashboard') }}
      />
    </div>
  )
}