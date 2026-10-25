'use client'

import Image from 'next/image'
import { useEffect, useRef, useState } from 'react'
import { useTranslations } from 'next-intl'
import { Beaker, CloudUpload, ScanSearch, Upload } from 'lucide-react'
import { KitQuestion } from '@/components/kit/kit-question'
import { Button } from '@/components/ui/button'
import { apiRequest } from '@/lib/api'
import { errorMessage } from '@/lib/errors'
import { toast } from 'sonner'
import type { LogoUploadResponse, ProductAssetResponse, ProductAssetUploadResponse } from '@/types'

interface StepLogoProps {
    brandId: string
    brandName: string
    productAssetId: string | null
    onAssetChange: (productAssetId: string) => void
    logoUrl: string | null
    onLogoChange: (logoUrl: string) => void
}

export function StepLogo({ brandId, brandName, productAssetId, onAssetChange, logoUrl, onLogoChange }: StepLogoProps) {
    const t = useTranslations('components.kit.steps.step-logo')
    const tt = useTranslations('toasts')
    const te = useTranslations('errors')
    const inputRef = useRef<HTMLInputElement>(null)
    const logoInputRef = useRef<HTMLInputElement>(null)
    const [uploading, setUploading] = useState(false)
    const [uploadingLogo, setUploadingLogo] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [logoError, setLogoError] = useState<string | null>(null)
    const [imageUrl, setImageUrl] = useState<string | null>(null)

    useEffect(() => {
        if (!productAssetId) {
            setImageUrl(null)
            return
        }
        let cancelled = false
        apiRequest<ProductAssetResponse>(`/brands/${brandId}/product-assets/${productAssetId}`)
            .then((asset) => {
                if (!cancelled) setImageUrl(asset.image_url)
            })
            .catch((loadError) => {
                if (!cancelled) toast.error(errorMessage(loadError, te))
            })
        return () => { cancelled = true }
    }, [brandId, productAssetId, te])

    async function uploadLogo(file?: File) {
        if (!file) return
        setLogoError(null)
        if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) {
            setLogoError(t('image_type_error'))
            return
        }
        if (file.size > 5 * 1024 * 1024) {
            setLogoError(t('logo_size_error'))
            return
        }

        setUploadingLogo(true)
        try {
            const body = new FormData()
            body.append('file', file)
            const response = await apiRequest<LogoUploadResponse>(`/brands/${brandId}/logo`, {
                method: 'POST',
                body,
            })
            onLogoChange(response.logo_url)
            toast.success(tt('logoUploaded'))
        } catch (uploadError) {
            toast.error(errorMessage(uploadError, te))
        } finally {
            setUploadingLogo(false)
            if (logoInputRef.current) logoInputRef.current.value = ''
        }
    }

    async function uploadProductImage(file?: File) {
        if (!file) return
        setError(null)
        if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) {
            setError(t('image_type_error'))
            return
        }
        if (file.size > 10 * 1024 * 1024) {
            setError(t('image_size_error'))
            return
        }

        setUploading(true)
        try {
            const body = new FormData()
            body.append('file', file)
            const response = await apiRequest<ProductAssetUploadResponse>(`/brands/${brandId}/product-assets`, {
                method: 'POST',
                body,
            })
            setImageUrl(response.image_url)
            onAssetChange(response.id)
            toast.success(tt('productImageUploaded'))
        } catch (uploadError) {
            toast.error(errorMessage(uploadError, te))
        } finally {
            setUploading(false)
            if (inputRef.current) inputRef.current.value = ''
        }
    }

    return (
        <div className="space-y-7">
            <div className="mx-auto flex w-full max-w-[640px] flex-col items-center gap-3 rounded-xl border border-brand-accent/20 bg-white p-6 text-center">
                <h2 className="font-tajawal text-[16px] font-bold text-brand-headline">{t('brand_logo_label')}</h2>
                <p className="font-tajawal text-[12px] text-muted-foreground">{t('brand_logo_hint')}</p>
                {logoUrl && <Image src={logoUrl} alt={t('brand_logo_alt', { brandName })} width={80} height={80} unoptimized className="h-20 w-20 object-contain" />}
                <input
                    ref={logoInputRef}
                    type="file"
                    accept="image/png,image/jpeg,image/webp"
                    aria-label={t('brand_logo_label')}
                    className="sr-only"
                    onChange={(event) => void uploadLogo(event.target.files?.[0])}
                />
                <Button type="button" variant="outline" onClick={() => logoInputRef.current?.click()} disabled={uploadingLogo}>
                    {uploadingLogo ? t('uploading') : logoUrl ? t('replace_logo') : t('choose_logo')}
                </Button>
                {logoError && <p role="alert" className="font-tajawal text-[13px] text-destructive">{logoError}</p>}
            </div>
            <KitQuestion
                align="center"
                before={t('question_before')}
                emphasis={t('question_emphasis')}
                after={t('question_after')}
                helper={t('helper', { brandName })}
            />
            <p className="text-center font-tajawal text-[12px] text-muted-foreground">{t('product_optional_hint')}</p>
            <div
                onDragOver={(event) => event.preventDefault()}
                onDrop={(event) => {
                    event.preventDefault()
                    void uploadProductImage(event.dataTransfer.files[0])
                }}
                className="mx-auto flex min-h-[240px] w-full flex-col items-center justify-center gap-4 rounded-xl border border-dashed border-brand-headline/45 bg-white/35 px-6 py-8 text-center sm:min-h-[245px]"
            >
                <div className="relative flex h-14 w-14 items-center justify-center overflow-hidden rounded-xl border border-brand-primary/20 bg-white text-brand-primary">
                    {imageUrl ? <Image src={imageUrl} alt={t('product_image_alt', { brandName })} fill unoptimized className="object-contain p-1" /> : <CloudUpload className="h-5 w-5" />}
                </div>
                <div className="space-y-1">
                    <p className="font-tajawal text-[15px] font-semibold text-brand-headline">{t('drop_prompt')}</p>
                    <p className="font-tajawal text-[12px] text-muted-foreground">{t('requirements')}</p>
                </div>
                <input
                    ref={inputRef}
                    type="file"
                    accept="image/png,image/jpeg,image/webp"
                    aria-label={t('product_image_label')}
                    className="sr-only"
                    onChange={(event) => void uploadProductImage(event.target.files?.[0])}
                />
                <Button type="button" variant="outline" className="h-9 rounded-full px-4 text-[12px]" onClick={() => inputRef.current?.click()} disabled={uploading}>
                    <Upload className="h-4 w-4" />
                    {uploading ? t('uploading') : productAssetId ? t('replace_image') : t('choose_image')}
                </Button>
                {error && <p role="alert" className="font-tajawal text-[13px] text-destructive">{error}</p>}
                <div className="flex flex-wrap items-center justify-center gap-2 pt-1">
                    <span className="inline-flex items-center gap-1.5 rounded-full border border-brand-accent/20 bg-white px-3 py-1.5 font-tajawal text-[11px] text-muted-foreground"><Beaker className="h-3 w-3 text-brand-primary" />{t('background_removal')}</span>
                    <span className="inline-flex items-center gap-1.5 rounded-full border border-brand-accent/20 bg-white px-3 py-1.5 font-tajawal text-[11px] text-muted-foreground"><ScanSearch className="h-3 w-3 text-brand-primary" />{t('preserve_details')}</span>
                </div>
            </div>
        </div>
    )
}
