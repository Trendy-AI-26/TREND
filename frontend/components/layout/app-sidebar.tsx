'use client'

import Image from 'next/image'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { Bot, Clock, CreditCard, LogOut, Palette, Pencil, Plus, Settings, Sliders, User } from 'lucide-react'
import { createClient } from '@/lib/supabase/client'
import { normalizeHex, TRENDY_AI_ACCENT } from '@/components/brand/brand-workspace'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import { useTranslations } from 'next-intl'
import type { BrandListItem, Profile } from '@/types'

interface AppSidebarProps {
  brands: BrandListItem[]
  accents: Record<string, string>
  currentBrandId?: string
  profile: Profile | null
  onCreateBrand: () => void
}

export function AppSidebar({
  brands,
  accents,
  currentBrandId,
  profile,
  onCreateBrand,
}: AppSidebarProps) {
  const pathname = usePathname()
  const router = useRouter()
  const t = useTranslations()
  const activeBrand = brands.find((b) => b.id === currentBrandId) ?? brands[0]
  const workspaceId = currentBrandId ?? activeBrand?.id

  async function handleLogout() {
    const supabase = createClient()
    await supabase.auth.signOut()
    router.push('/login')
    router.refresh()
  }

  const nav = workspaceId
    ? [
        { href: `/${workspaceId}/kit`, label: t('dashboard.brandIdentity'), icon: Palette, match: 'prefix' as const },
        { href: `/${workspaceId}`, label: t('dashboard.aiContent'), icon: Bot, match: 'exact' as const },
        { href: `/${workspaceId}/studio`, label: t('dashboard.designStudio'), icon: Pencil, match: 'prefix' as const },
        { href: `/${workspaceId}/history`, label: t('dashboard.activityLog'), icon: Clock, match: 'prefix' as const },
        // BYOK is intentionally hidden while provider-key management is disabled.
      ]
    : []

  return (
    <aside className="flex h-full w-[224px] shrink-0 flex-col overflow-y-auto border-e border-brand-accent/30 bg-brand-cream px-3 font-readex text-brand-headline">
      <Link
        href="/brands"
        className="flex shrink-0 flex-col gap-1 border-b border-brand-accent/30 px-1 py-3 no-underline"
      >
        <span className="flex items-center gap-2">
          <Image
            src="/trendy_logo.png"
            alt="TRENDY AI"
            width={32}
            height={32}
            className="h-8 w-8 object-contain"
          />
          <span className="font-logo text-[22px] font-semibold leading-none text-brand-headline">
            TRENDY AI
          </span>
          <Badge>{t('dashboard.proBadge')}</Badge>
        </span>
        <span className="text-[11px] text-brand-headline/50">{t('dashboard.tagline')}</span>
      </Link>

      <div className="mt-3 rounded-[10px] border border-brand-accent/30 bg-brand-bg/40 px-3 py-[10px]">
        <Link
          href="/brands"
          className="flex items-center gap-1 text-[11px] text-brand-primary no-underline hover:underline"
        >
          <span className="inline-block ltr:order-last ltr:rotate-180">‹</span>
          <span>{t('dashboard.allBrandsShort')}</span>
        </Link>
        <p className="mt-[6px] truncate text-[13px] font-bold leading-[20px]">
          {t('dashboard.currentBrand')} : {activeBrand?.name ?? t('dashboard.workspace')}
        </p>
        <div className="mt-[6px] flex flex-wrap items-center gap-[4px]">
          {brands.map((brand) => {
            const selected = brand.id === currentBrandId
            const hex = normalizeHex(accents[brand.id] ?? '')
            return (
              <Link
                key={brand.id}
                href={`/${brand.id}`}
                title={brand.name}
                aria-label={brand.name}
                className="flex flex-col items-center gap-[2px] rounded-[4px] no-underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary/40"
              >
                <span
                  className={cn(
                    'block h-[26px] w-[26px] rounded-[6px] ring-1 ring-inset ring-black/10',
                    selected && 'shadow-[0_1px_4px_rgba(26,26,26,0.3)]',
                  )}
                  style={{ background: hex ? `#${hex}` : TRENDY_AI_ACCENT }}
                />
                <span
                  className={cn(
                    'h-[2px] w-[26px] rounded-full',
                    selected ? 'bg-brand-headline/50' : 'bg-transparent',
                  )}
                />
              </Link>
            )
          })}
          <button
            type="button"
            onClick={onCreateBrand}
            title={t('dashboard.createBrand')}
            aria-label={t('dashboard.createBrand')}
            className="mb-[2px] inline-flex h-[26px] w-[26px] items-center justify-center rounded-[6px] border border-brand-accent/40 bg-brand-bg/60 text-brand-headline/60 transition-colors duration-fast hover:border-brand-primary hover:text-brand-primary"
          >
            <Plus className="h-[13px] w-[13px]" />
          </button>
        </div>
        <p className="mt-1 text-[11px] text-brand-headline/50">{t('dashboard.identityColors')}</p>
      </div>

      <nav className="-mx-3 mt-4 flex flex-col gap-[2px]" aria-label={t('dashboard.workspaceNavigation')}>
        {nav.map((item) => {
          const active =
            item.match === 'exact'
              ? pathname === item.href
              : pathname === item.href || pathname.startsWith(`${item.href}/`)
          const Icon = item.icon
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? 'page' : undefined}
              className={cn(
                'flex h-[42px] items-center gap-3 border-s-[3px] ps-[23px] pe-4 text-[13.5px] no-underline transition-colors duration-fast',
                active
                  ? 'rounded-e-lg border-brand bg-brand-weaker font-bold'
                  : 'border-transparent text-brand-headline/70 hover:bg-brand-bg/60',
              )}
            >
              <Icon className={cn('h-[17px] w-[17px]', active ? 'text-brand' : 'text-brand-headline/60')} />
              <span className="flex-1">{item.label}</span>
            </Link>
          )
        })}
      </nav>

      <div className="mt-auto pb-5">
        {profile?.is_admin && (
          <Link
            href="/admin"
            className={cn(
              'mb-2 flex h-9 items-center gap-3 rounded-lg px-2 text-[13.5px] text-brand-headline/70 no-underline transition-colors duration-fast hover:bg-brand-bg/60',
              pathname.startsWith('/admin') && 'bg-brand-bg/60 font-bold text-brand-headline',
            )}
          >
            <Sliders className="h-[17px] w-[17px] text-brand-headline/60" />
            <span className="flex-1">{t('dashboard.admin')}</span>
            <Badge>Op</Badge>
          </Link>
        )}
        <div className="border-t border-brand-accent/30 pt-[10px]">
          <Link
            href="/account"
            className="flex items-center gap-[10px] rounded-lg px-1 py-1 no-underline transition-colors duration-fast hover:bg-brand-bg/60"
          >
            {profile?.avatar_url ? (
              <img src={profile.avatar_url} alt="" className="h-8 w-8 shrink-0 rounded-full object-cover" />
            ) : (
              <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-primary">
                <User className="h-[15px] w-[15px] text-white" />
              </span>
            )}
            <span className="truncate text-[13px] font-medium">{profile?.full_name || t('dashboard.you')}</span>
          </Link>

          <div className="mt-1 flex flex-col gap-[2px]">
            <Link
              href="#"
              className="flex h-9 items-center gap-3 rounded-lg px-2 text-[13px] text-brand-headline/70 no-underline transition-colors duration-fast hover:bg-brand-bg/60"
            >
              <CreditCard className="h-[16px] w-[16px] text-brand-headline/60" />
              <span>{t('dashboard.subscription')}</span>
            </Link>
            {workspaceId && (
              <Link
                href={`/${workspaceId}/settings`}
                className={cn(
                  'flex h-9 items-center gap-3 rounded-lg px-2 text-[13px] no-underline transition-colors duration-fast hover:bg-brand-bg/60',
                  pathname.startsWith(`/${workspaceId}/settings`)
                    ? 'font-bold text-brand-headline'
                    : 'text-brand-headline/70',
                )}
              >
                <Settings className="h-[16px] w-[16px] text-brand-headline/60" />
                <span>{t('dashboard.settings')}</span>
              </Link>
            )}
          </div>

          <button
            type="button"
            onClick={handleLogout}
            className="mt-3 flex h-[34px] w-full items-center justify-center gap-2 rounded-md border border-brand-primary text-[12px] text-brand-headline/60 transition-colors duration-fast hover:bg-brand-primary hover:text-white"
          >
            <LogOut className="h-[13px] w-[13px] rtl:-scale-x-100" />
            {t('dashboard.logout')}
          </button>
        </div>
      </div>
    </aside>
  )
}
