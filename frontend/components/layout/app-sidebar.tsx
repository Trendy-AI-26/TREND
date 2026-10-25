'use client'

import Image from 'next/image'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { Bot, CreditCard, FolderOpen, Gauge, LogOut, Palette, Plus, Settings, Sliders, User, X } from 'lucide-react'
import { logout } from '@/lib/api'
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
  collapsed?: boolean
  onCreateBrand: () => void
  onClose?: () => void
}

export function AppSidebar({
  brands,
  accents,
  currentBrandId,
  profile,
  collapsed = false,
  onCreateBrand,
  onClose,
}: AppSidebarProps) {
  const pathname = usePathname()
  const router = useRouter()
  const t = useTranslations()
  const activeBrand = brands.find((b) => b.id === currentBrandId) ?? brands[0]
  const workspaceId = currentBrandId ?? activeBrand?.id

  async function handleLogout() {
    await logout()
    router.push('/login')
    router.refresh()
  }

  const nav = workspaceId
    ? [
      { href: `/dashboard?brandId=${workspaceId}`, label: t('dashboard.overview'), icon: Gauge, match: 'exact' as const },
      { href: `/${workspaceId}/kit`, label: t('dashboard.brandIdentity'), icon: Palette, match: 'prefix' as const },
      { href: `/${workspaceId}/generate`, label: t('dashboard.aiContent'), icon: Bot, match: 'prefix' as const },
      { href: `/${workspaceId}/history`, label: t('dashboard.myLibrary'), icon: FolderOpen, match: 'prefix' as const },
      // BYOK is intentionally hidden while provider-key management is disabled.
    ]
    : []

  return (
    <aside className={cn('flex h-full shrink-0 flex-col overflow-y-auto border-e border-brand-accent/30 bg-brand-cream font-readex text-brand-headline transition-[width,padding] duration-fast', collapsed ? 'w-[84px] px-2' : 'w-[224px] px-3')}>
      <div className={cn('relative shrink-0 border-b border-brand-accent/30 py-3', collapsed ? 'flex items-center justify-center' : '')}>
        {!collapsed && (
          <button
            type="button"
            onClick={onClose}
            aria-label={t('layout.app-shell.close_menu')}
            className="absolute end-0 top-3 inline-flex h-8 w-8 items-center justify-center rounded-md text-brand-headline/60 transition-colors hover:bg-brand-bg/60 hover:text-brand-primary"
          >
            <X className="h-4 w-4" />
          </button>
        )}
        <Link
          href="/dashboard"
          className={cn('flex flex-col gap-1 no-underline', collapsed ? 'items-center px-1' : 'px-1 pe-10')}
        >
          <span className="flex items-center gap-2">
            <Image
              src="/trendy_logo.png"
              alt="TRENDY AI"
              width={32}
              height={32}
              className="h-8 w-8 object-contain"
            />
            <span className={cn('font-logo text-[22px] font-semibold leading-none text-brand-headline', collapsed && 'sr-only')}>
              TRENDY AI
            </span>
          </span>
          {!collapsed && <span className="text-[11px] text-brand-headline/50">{t('dashboard.tagline')}</span>}
        </Link>
      </div>

      <div className={cn('mt-3 rounded-[10px] border border-brand-accent/30 bg-brand-bg/40', collapsed ? 'flex flex-col items-center px-1 py-2' : 'px-3 py-[10px]')}>
        {collapsed ? (
          <div className="flex flex-wrap items-center justify-center gap-2" aria-label={t('dashboard.currentBrand')}>
            {activeBrand && (() => {
              const hex = normalizeHex(accents[activeBrand.id] ?? '')
              return <span className="flex h-8 w-8 items-center justify-center overflow-hidden rounded-lg ring-1 ring-inset ring-black/10" style={{ background: hex ? `#${hex}` : TRENDY_AI_ACCENT }} title={activeBrand.name}>
                {activeBrand.logo_url && <Image src={activeBrand.logo_url} alt="" width={32} height={32} unoptimized className="h-full w-full object-contain" />}
              </span>
            })()}
            <button type="button" onClick={onCreateBrand} title={t('dashboard.createBrand')} aria-label={t('dashboard.createBrand')} className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-brand-accent/40 bg-brand-bg/60 text-brand-headline/60 transition-colors hover:border-brand-primary hover:text-brand-primary">
              <Plus className="h-[14px] w-[14px]" />
            </button>
          </div>
        ) : (
          <>
            <Link
              href="/dashboard"
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
                const selected = brand.id === currentBrandId || (!currentBrandId && brand.id === activeBrand?.id)
                const hex = normalizeHex(accents[brand.id] ?? '')
                return (
                  <Link
                    key={brand.id}
                    href={`/dashboard?brandId=${brand.id}`}
                    title={brand.name}
                    aria-label={brand.name}
                    className="flex flex-col items-center gap-[2px] rounded-[4px] no-underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary/40"
                  >
                    <span
                      className={cn(
                        'flex h-[26px] w-[26px] items-center justify-center overflow-hidden rounded-[6px] ring-1 ring-inset ring-black/10',
                        selected && 'shadow-[0_1px_4px_rgba(26,26,26,0.3)]',
                      )}
                      style={{ background: hex ? `#${hex}` : TRENDY_AI_ACCENT }}
                    >
                      {brand.logo_url && <Image src={brand.logo_url} alt="" width={26} height={26} unoptimized className="h-full w-full object-contain" />}
                    </span>
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
          </>
        )}
      </div>

      <nav className={cn('mt-4 flex flex-col gap-[6px]', collapsed ? '' : '-mx-3 gap-[2px]')} aria-label={t('dashboard.workspaceNavigation')}>
        {nav.map((item) => {
          const itemPath = item.href.split('?')[0]
          const active =
            itemPath === '/dashboard'
              ? pathname === '/dashboard'
              : item.match === 'exact'
                ? pathname === item.href
                : pathname === item.href || pathname.startsWith(`${item.href}/`)
          const Icon = item.icon
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? 'page' : undefined}
              className={cn(
                'flex h-[42px] items-center border-s-[3px] text-[13.5px] no-underline transition-colors duration-fast',
                collapsed ? 'justify-center rounded-lg border-transparent px-0' : 'gap-3 ps-[23px] pe-4',
                active
                  ? cn('rounded-e-lg border-brand bg-brand-weaker font-bold', collapsed && 'rounded-lg')
                  : 'border-transparent text-brand-headline/70 hover:bg-brand-bg/60',
              )}
              title={collapsed ? item.label : undefined}
            >
              <Icon className={cn('h-[17px] w-[17px]', active ? 'text-brand' : 'text-brand-headline/60')} />
              {!collapsed && <span className="flex-1">{item.label}</span>}
            </Link>
          )
        })}
      </nav>

      <div className={cn('mt-auto pb-5', collapsed && 'flex flex-col items-center')}>
        {profile?.is_admin && (
          <Link
            href="/admin"
            className={cn(
              'mb-2 flex h-9 items-center gap-3 rounded-lg text-[13.5px] text-brand-headline/70 no-underline transition-colors duration-fast hover:bg-brand-bg/60',
              collapsed ? 'w-10 justify-center px-0' : 'px-2',
              pathname.startsWith('/admin') && 'bg-brand-bg/60 font-bold text-brand-headline',
            )}
          >
            <Sliders className="h-[17px] w-[17px] text-brand-headline/60" />
            {!collapsed && <span className="flex-1">{t('dashboard.admin')}</span>}
            {!collapsed && <Badge>Op</Badge>}
          </Link>
        )}
        <div className="border-t border-brand-accent/30 pt-[10px]">
          <Link
            href="/account"
            className={cn('flex items-center gap-[10px] rounded-lg py-1 no-underline transition-colors duration-fast hover:bg-brand-bg/60', collapsed ? 'justify-center px-0' : 'px-1')}
            title={collapsed ? (profile?.full_name || t('dashboard.you')) : undefined}
          >
            {profile?.avatar_url ? (
              <img src={profile.avatar_url} alt="" className="h-8 w-8 shrink-0 rounded-full object-cover" />
            ) : (
              <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-primary">
                <User className="h-[15px] w-[15px] text-white" />
              </span>
            )}
            {!collapsed && <span className="truncate text-[13px] font-medium">{profile?.full_name || t('dashboard.you')}</span>}
          </Link>

          <div className={cn('mt-1 flex flex-col gap-[2px]', collapsed && 'items-center')}>
            <Link
              href="#"
              aria-label={t('dashboard.subscription')}
              title={collapsed ? t('dashboard.subscription') : undefined}
              className={cn('flex h-9 items-center gap-3 rounded-lg text-[13px] text-brand-headline/70 no-underline transition-colors duration-fast hover:bg-brand-bg/60', collapsed ? 'w-10 justify-center px-0' : 'px-2')}
            >
              <CreditCard className="h-[16px] w-[16px] text-brand-headline/60" />
              {!collapsed && <span>{t('dashboard.subscription')}</span>}
            </Link>
            {workspaceId && (
              <Link
                href={`/${workspaceId}/settings`}
                className={cn(
                  'flex h-9 items-center gap-3 rounded-lg text-[13px] no-underline transition-colors duration-fast hover:bg-brand-bg/60',
                  collapsed ? 'w-10 justify-center px-0' : 'px-2',
                  pathname.startsWith(`/${workspaceId}/settings`)
                    ? 'font-bold text-brand-headline'
                    : 'text-brand-headline/70',
                )}
              >
                <Settings className="h-[16px] w-[16px] text-brand-headline/60" />
                {!collapsed && <span>{t('dashboard.settings')}</span>}
              </Link>
            )}
          </div>

          <button
            type="button"
            onClick={handleLogout}
            aria-label={t('dashboard.logout')}
            title={collapsed ? t('dashboard.logout') : undefined}
            className={cn(
              'mt-3 flex h-[34px] items-center justify-center gap-2 rounded-md border border-brand-primary text-[12px] text-brand-headline/60 transition-colors duration-fast hover:bg-brand-primary hover:text-white',
              collapsed ? 'w-10' : 'w-full',
            )}
          >
            <LogOut className="h-[13px] w-[13px] rtl:-scale-x-100" />
            {!collapsed && t('dashboard.logout')}
          </button>
        </div>
      </div>
    </aside>
  )
}
