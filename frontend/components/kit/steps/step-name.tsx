'use client'

import { useEffect, useRef, useState } from 'react'
import { useTranslations } from 'next-intl'
import Image from 'next/image'
import { KitQuestion } from '@/components/kit/kit-question'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { apiRequest } from '@/lib/api'
import { errorMessage } from '@/lib/errors'
import type { Brand } from '@/types'

interface StepProps {
  brandId: string
  brandName: string
  logoUrl?: string | null
  onNameSaved: (brand: Brand) => void
}

export function StepName({ brandId, brandName, logoUrl, onNameSaved }: StepProps) {
  const t = useTranslations('components.kit.steps.step-name')
  const te = useTranslations('errors')
  const [name, setName] = useState(brandName)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const submitting = useRef(false)

  useEffect(() => { setName(brandName) }, [brandName])

  const trimmed = name.trim()
  const valid = trimmed.length >= 2 && trimmed.length <= 120
  const changed = trimmed !== brandName

  async function handleSave(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (submitting.current || !valid || !changed) return
    submitting.current = true
    setSaving(true)
    setError(null)
    try {
      const updated = await apiRequest<Brand>(`/brands/${brandId}`, {
        method: 'PATCH',
        body: JSON.stringify({ name: trimmed }),
      })
      onNameSaved(updated)
      setName(updated.name)
      setSaved(true)
    } catch (saveError) {
      setError(errorMessage(saveError, te))
    } finally {
      submitting.current = false
      setSaving(false)
    }
  }

  return (
    <div className="space-y-7">
      <KitQuestion
        align="center"
        before={t('this_is_prefix')}
        emphasis={brandName}
        after="."
        helper={t('registered_name_help')}
      />
      <div className="mx-auto flex w-full max-w-[440px] flex-col items-center gap-5 rounded-xl border border-brand-accent/15 bg-white px-6 py-8 shadow-xs">
        {logoUrl ? (
          <Image src={logoUrl} alt="" width={64} height={64} className="h-16 w-16 rounded-xl border border-brand-accent/15 bg-brand-cream object-contain p-2" />
        ) : (
          <span className="flex h-16 w-16 items-center justify-center rounded-xl border border-brand-accent/20 bg-brand-cream font-el-messiri text-2xl font-bold text-brand-primary">{brandName.slice(0, 1).toUpperCase()}</span>
        )}
        <form onSubmit={(event) => void handleSave(event)} className="w-full space-y-3">
          <Label htmlFor="kit-brand-name" className="font-tajawal text-[13px]">{t('name_label')}</Label>
          <Input
            id="kit-brand-name"
            type="text"
            dir="auto"
            value={name}
            disabled={saving}
            onChange={(event) => { setName(event.target.value); setError(null); setSaved(false) }}
            aria-invalid={changed && !valid}
            aria-describedby="kit-brand-name-hint kit-brand-name-feedback"
            className="font-tajawal text-[14px]"
          />
          <p id="kit-brand-name-hint" className="font-tajawal text-[12px] text-muted-foreground">{t('name_requirements')}</p>
          <Button type="submit" disabled={saving || !valid || !changed} className="w-full">
            {saving ? t('saving_name') : t('save_name')}
          </Button>
          <div id="kit-brand-name-feedback" aria-live="polite">
            {changed && !valid ? <p role="alert" className="font-tajawal text-[12px] text-destructive">{t('name_invalid')}</p> : null}
            {error ? <p role="alert" className="font-tajawal text-[12px] text-destructive">{error}</p> : null}
            {saved ? <p role="status" className="font-tajawal text-[12px] text-emerald-700">{t('name_saved')}</p> : null}
          </div>
        </form>
      </div>
    </div>
  )
}
