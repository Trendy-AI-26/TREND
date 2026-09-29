'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useLocale, useTranslations } from 'next-intl'
import { Globe2 } from 'lucide-react'
import { apiRequest } from '@/lib/api'
import type { Profile } from '@/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useToast } from '@/hooks/use-toast'

interface ProfileFormProps {
  profile: Profile
  onUpdate: (profile: Profile) => void
}

export function ProfileForm({ profile, onUpdate }: ProfileFormProps) {
  const { toast } = useToast()
  const router = useRouter()
  const locale = useLocale()
  const t = useTranslations()
  const [fullName, setFullName] = useState(profile.full_name ?? '')
  const [avatarUrl, setAvatarUrl] = useState(profile.avatar_url ?? '')
  const [avatarFile, setAvatarFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [imageError, setImageError] = useState<string | null>(null)
  const [errors, setErrors] = useState<{ full_name?: string }>({})

  const initials = fullName.trim()
    ? fullName.trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase()
    : 'TR'

  function handleImageChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.type.startsWith('image/')) {
      setImageError(t('account.imageTypeError'))
      return
    }
    if (file.size > 2 * 1024 * 1024) {
      setImageError(t('account.imageSizeError'))
      return
    }
    setImageError(null)
    setAvatarFile(file)
    const reader = new FileReader()
    reader.onload = () => setAvatarUrl(typeof reader.result === 'string' ? reader.result : '')
    reader.readAsDataURL(file)
  }

  function validate(): boolean {
    const newErrors: typeof errors = {}
    if (fullName.trim() && (fullName.trim().length < 2 || fullName.trim().length > 120)) {
      newErrors.full_name = t('account.fullNameError')
    }
    setErrors(newErrors)
    return Object.keys(newErrors).length === 0 && !imageError
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    if (!validate()) return
    setLoading(true)
    try {
      const updated = await apiRequest<Profile>('/me', {
        method: 'PATCH',
        body: JSON.stringify({ full_name: fullName.trim() || null }),
      })
      let nextProfile = updated
      if (avatarFile) {
        const formData = new FormData()
        formData.append('file', avatarFile)
        const uploaded = await apiRequest<{ avatar_url: string }>('/me/avatar', {
          method: 'POST',
          body: formData,
        })
        nextProfile = { ...updated, avatar_url: uploaded.avatar_url }
        setAvatarFile(null)
      }
      onUpdate(nextProfile)
      toast({ title: t('account.profileUpdated'), description: t('account.changesSaved') })
    } catch (err) {
      toast({ title: t('account.error'), description: err instanceof Error ? err.message : t('account.updateFailed'), variant: 'destructive' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-5">
      <Card className="overflow-hidden rounded-2xl border-[#e2e7ed] bg-white shadow-sm">
        <CardHeader className="px-6 pb-0 pt-7 sm:px-8">
          <CardTitle className="font-el-messiri text-[18px] text-brand-headline">{t('account.profileCardTitle')}</CardTitle>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-7 px-6 py-6 sm:px-8 sm:py-7">
            <div className="space-y-2.5">
              <Label htmlFor="profile-email" className="font-tajawal text-[14px] font-semibold text-brand-headline">{t('account.email')}</Label>
              <div className="relative">
                <Input id="profile-email" value={profile.email} disabled dir="ltr" className="h-11 rounded-lg border-[#dce2e9] bg-[#f8f9fa] px-3 font-tajawal" />
              </div>
              <p className="font-tajawal text-[12px] text-muted-foreground">{t('account.emailHint')}</p>
            </div>

            <div className="space-y-2.5">
              <Label htmlFor="full_name" className="font-tajawal text-[14px] font-semibold text-brand-headline">{t('account.fullName')}</Label>
              <div className="relative">
                <Input id="full_name" value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder={t('account.fullNamePlaceholder')} dir="auto" className="h-11 rounded-lg border-[#dce2e9] px-3 font-tajawal" />
              </div>
              {errors.full_name && <p className="font-tajawal text-[13px] text-destructive">{errors.full_name}</p>}
            </div>

            <div className="space-y-2.5">
              <Label htmlFor="avatar-file" className="font-tajawal text-[14px] font-semibold text-brand-headline">{t('account.avatarUrl')}</Label>
              <div className="flex flex-col gap-4 rounded-xl border border-dashed border-[#dce2e9] bg-[#fafbfc] p-4 sm:flex-row sm:items-center">
                <div className="relative shrink-0">
                  {avatarUrl ? <img src={avatarUrl} alt="" className="h-12 w-12 rounded-full object-cover" /> : <span className="flex h-12 w-12 items-center justify-center rounded-full bg-brand-primary font-tajawal text-sm font-bold text-white">{initials}</span>}
                  <span aria-hidden="true" className="absolute -bottom-0.5 -end-0.5 h-3 w-3 rounded-full border-2 border-white bg-[#2f9e44]" />
                </div>
                <div className="min-w-0 flex-1 space-y-2">
                  <p className="font-tajawal text-[13px] text-brand-headline/70">{t('account.avatarUploadHint')}</p>
                  <label htmlFor="avatar-file" className="inline-flex h-11 w-fit cursor-pointer items-center justify-center rounded-xl border border-brand-accent/30 bg-white px-5 font-tajawal text-[13px] font-semibold text-brand-headline transition hover:border-brand-primary hover:text-brand-primary">
                    {t('account.chooseImage')}
                  </label>
                  <input id="avatar-file" type="file" accept="image/png,image/jpeg,image/webp" onChange={handleImageChange} className="sr-only" />
                  <p className="font-tajawal text-[12px] text-muted-foreground">{t('account.imageRequirements')}</p>
                  {imageError && <p className="font-tajawal text-[13px] text-destructive">{imageError}</p>}
                </div>
              </div>
            </div>

            <div dir="ltr" className="flex justify-end pt-1">
              <Button type="submit" disabled={loading} size="lg" className="h-11 rounded-lg px-6 font-tajawal">{loading ? t('account.saving') : t('account.saveChanges')}</Button>
            </div>
          </CardContent>
        </form>
      </Card>

      <Card id="language-settings" className="rounded-[22px] border-brand-accent/25 bg-white shadow-card">
        <CardHeader className="px-6 py-5 sm:px-8"><CardTitle className="flex items-center gap-2 font-el-messiri text-[18px] text-brand-headline"><Globe2 className="h-4 w-4 text-brand-primary" />{t('account.languageCardTitle')}</CardTitle></CardHeader>
        <CardContent className="space-y-3 px-6 pb-7 sm:px-8">
          <div><Label htmlFor="language-select" className="font-tajawal text-[14px] font-semibold">{t('account.languageLabel')}</Label><p className="mt-1 font-tajawal text-[12px] text-muted-foreground">{t('account.languageHint')}</p></div>
          <select id="language-select" value={locale} onChange={(e) => { document.cookie = `NEXT_LOCALE=${e.target.value};path=/;max-age=31536000;sameSite=lax`; router.refresh() }} className="h-11 w-full rounded-xl border border-brand-accent/25 bg-brand-cream/25 px-3 font-tajawal text-sm focus:outline-none focus:ring-2 focus:ring-brand-ring">
            <option value="en">{t('account.languageEnglish')}</option><option value="ar">{t('account.languageArabic')}</option>
          </select>
        </CardContent>
      </Card>
    </div>
  )
}
