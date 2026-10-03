'use client'

import { useEffect, useRef, useState } from 'react'
import { useTranslations } from 'next-intl'
import { Upload, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import { PRODUCT_IMAGE_MAX_MB } from './wizard-types'

const ACCEPTED_TYPES = ['image/png', 'image/jpeg', 'image/webp']
const MAX_BYTES = PRODUCT_IMAGE_MAX_MB * 1024 * 1024

interface ProductImageUploadProps {
  file: File | null
  onChange: (file: File | null) => void
}

export function ProductImageUpload({ file, onChange }: ProductImageUploadProps) {
  const t = useTranslations('components.generation.wizard')
  const inputRef = useRef<HTMLInputElement>(null)
  const [dragging, setDragging] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)

  // نعمل رابط مؤقت للصورة حتى نعرضها، وننظفه لما تتغير أو تنشال
  useEffect(() => {
    if (!file) {
      setPreviewUrl(null)
      return
    }
    const url = URL.createObjectURL(file)
    setPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  function handleFiles(files: FileList | null) {
    const picked = files?.[0]
    if (!picked) return

    if (!ACCEPTED_TYPES.includes(picked.type)) {
      setError(t('upload_error_type'))
      return
    }
    if (picked.size > MAX_BYTES) {
      setError(t('upload_error_size', { max: PRODUCT_IMAGE_MAX_MB }))
      return
    }

    setError(null)
    onChange(picked)
  }

  const hiddenInput = (
    <input
      ref={inputRef}
      type="file"
      accept={ACCEPTED_TYPES.join(',')}
      className="sr-only"
      tabIndex={-1}
      onChange={(e) => {
        handleFiles(e.target.files)
        // نفضّي الحقل حتى نقدر نختار نفس الملف مرة ثانية
        e.target.value = ''
      }}
    />
  )

  // ===== إذا في صورة مختارة: نعرض معاينة =====
  if (file && previewUrl) {
    const sizeMb = (file.size / 1024 / 1024).toFixed(1)
    return (
      <div className="flex items-center gap-4 rounded-[12px] border border-brand-accent/25 bg-white p-3">
        {/* eslint-disable-next-line @next/next/no-img-element -- معاينة محلية من جهاز المستخدم */}
        <img
          src={previewUrl}
          alt={file.name}
          className="h-20 w-20 shrink-0 rounded-[8px] border border-brand-accent/15 object-cover"
        />
        <div className="min-w-0 flex-1">
          <p className="truncate text-[13px] font-bold text-brand-headline">{file.name}</p>
          <p className="mt-0.5 text-[11.5px] text-brand-headline/40">{t('upload_size', { size: sizeMb })}</p>
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            className="mt-1.5 text-[12px] font-semibold text-brand-primary hover:underline"
          >
            {t('upload_replace')}
          </button>
        </div>
        <button
          type="button"
          onClick={() => onChange(null)}
          aria-label={t('upload_remove')}
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-brand-headline/50 transition-colors hover:bg-brand-cream hover:text-destructive"
        >
          <X className="h-4 w-4" />
        </button>
        {hiddenInput}
      </div>
    )
  }

  // ===== إذا ما في صورة: نعرض منطقة السحب والإفلات =====
  return (
    <div>
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          handleFiles(e.dataTransfer.files)
        }}
        className={cn(
          'flex w-full flex-col items-center justify-center rounded-[12px] border-2 border-dashed px-4 py-8 text-center transition-colors',
          dragging
            ? 'border-brand-primary bg-brand-primary/5'
            : 'border-brand-accent/30 bg-white hover:border-brand-accent/60 hover:bg-brand-cream',
        )}
      >
        <span className="flex h-9 w-9 items-center justify-center rounded-[10px] bg-brand-primary/10 text-brand-primary">
          <Upload className="h-[18px] w-[18px]" />
        </span>
        <span className="mt-3 text-[13px] font-bold text-brand-headline">{t('upload_title')}</span>
        <span className="mt-1 text-[11.5px] text-brand-headline/40">
          {t('upload_formats', { max: PRODUCT_IMAGE_MAX_MB })}
        </span>
      </button>
      {hiddenInput}
      {error && (
        <p role="alert" className="mt-1.5 text-[11.5px] text-destructive">
          {error}
        </p>
      )}
    </div>
  )
}