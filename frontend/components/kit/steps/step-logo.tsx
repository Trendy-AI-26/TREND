'use client'

import Image from 'next/image'
import { useEffect, useRef, useState } from 'react'
import { useTranslations } from 'next-intl'
import { Beaker, CloudUpload, ScanSearch, Upload } from 'lucide-react'
import { KitQuestion } from '@/components/kit/kit-question'
import { Button } from '@/components/ui/button'
import { apiRequest } from '@/lib/api'
import type { ProductAssetResponse, ProductAssetUploadResponse } from '@/types'

interface StepLogoProps {
    brandId: string
    brandName: string
    productAssetId: string | null
    onAssetChange: (productAssetId: string) => void
}

export function StepLogo({ brandId, brandName, productAssetId, onAssetChange }: StepLogoProps) {
    const t = useTranslations('components.kit.steps.step-logo')
    const inputRef = useRef<HTMLInputElement>(null)
    const [uploading, setUploading] = useState(false)
    const [error, setError] = useState<string | null>(null)
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
            .catch(() => {
                if (!cancelled) setError(t('image_load_failed'))
            })
        return () => { cancelled = true }
    }, [brandId, productAssetId, t])

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
        } catch (uploadError) {
            setError(uploadError instanceof Error ? uploadError.message : t('upload_failed'))
        } finally {
            setUploading(false)
            if (inputRef.current) inputRef.current.value = ''
        }
    }

    return (
        <div className="space-y-7">
            <KitQuestion
                align="center"
                before={t('question_before')}
                emphasis={t('question_emphasis')}
                after={t('question_after')}
                helper={t('helper', { brandName })}
            />
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