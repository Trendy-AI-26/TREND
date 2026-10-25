'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { UserRound, Settings2 } from 'lucide-react'
import { useProfile } from '@/hooks/use-profile'
import { useBrands } from '@/hooks/use-brands'
import { ProfileForm } from '@/components/account/profile-form'

export default function AccountPage() {
  const { profile, loading, error, mutate } = useProfile()
  const { brands } = useBrands()
  const t = useTranslations()
  const pathname = usePathname()
  const settingsHref = brands[0] ? `/${brands[0].id}/settings` : '/dashboard'

  if (loading) {
    return <div className="mx-auto max-w-[980px] py-8 font-tajawal text-muted-foreground">{t('account.loadingProfile')}</div>
  }

  if (error || !profile) {
    return (
      <div className="mx-auto max-w-[980px] py-8">
        <h1 className="font-el-messiri text-[32px] font-semibold text-brand-headline">{t('account.title')}</h1>
        <p className="mt-4 font-tajawal text-destructive">{error || t('account.failedToLoad')}</p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-[820px] space-y-4 pb-10">
      <header className="border-b border-brand-accent/25 pb-0">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h1 className="font-el-messiri text-[32px] font-semibold leading-tight text-brand-headline">{t('account.title')}</h1>
          </div>
        </div>
        <nav className="mt-3 flex items-center gap-6 font-tajawal text-[14px]" aria-label={t('account.title')}>
          <Link href="/account" className={`flex items-center gap-2 border-b-2 pb-2.5 font-semibold no-underline ${pathname === '/account' ? 'border-brand-primary text-brand-primary' : 'border-transparent text-brand-headline/55'}`}>
            <UserRound className="h-4 w-4" />
            {t('account.title')}
          </Link>
          <Link href={settingsHref} className="flex items-center gap-2 border-b-2 border-transparent pb-2.5 text-brand-headline/55 no-underline hover:text-brand-primary">
            <Settings2 className="h-4 w-4" />
            {t('dashboard.settings')}
          </Link>
        </nav>
      </header>
      <ProfileForm profile={profile} onUpdate={mutate} />
    </div>
  )
}