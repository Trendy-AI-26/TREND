'use client'

import Link from 'next/link'
import { useTranslations, useLocale } from 'next-intl'
import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useParams, usePathname, useRouter } from 'next/navigation'
import { Bell, PanelLeft } from 'lucide-react'
import { BrandWorkspace } from '@/components/brand/brand-workspace'
import { CreateBrandModal } from '@/components/brand/create-brand-modal'
import { AppSidebar } from '@/components/layout/app-sidebar'
import LanguageSwitcher from '@/components/language-switcher'
import { useBrands } from '@/hooks/use-brands'
import { useProfile } from '@/hooks/use-profile'
import { cn } from '@/lib/utils'
import type { Brand } from '@/types'

function isNeutralRoute(pathname: string) {
  return (
    pathname === '/brands' ||
    pathname.startsWith('/brands/') ||
    pathname === '/account' ||
    pathname.startsWith('/account/') ||
    pathname === '/notifications' ||
    pathname.startsWith('/notifications/') ||
    pathname === '/admin' ||
    pathname.startsWith('/admin/')
  )
}

function getPageLabelKey(pathname: string, currentBrandId?: string) {
  if (pathname === '/brands') return 'breadcrumb_brands'
  if (pathname === '/notifications' || pathname.startsWith('/notifications/')) return 'breadcrumb_notifications'
  if (pathname === '/account' || pathname.startsWith('/account/')) return 'breadcrumb_account'
  if (pathname === '/admin' || pathname.startsWith('/admin/')) return 'breadcrumb_admin'
  if (!currentBrandId || isNeutralRoute(pathname)) return null
  const brandPath = pathname.replace(`/${currentBrandId}`, '') || '/'
  if (brandPath === '/') return 'breadcrumb_content'
  if (brandPath === '/kit') return 'breadcrumb_brand_kit'
  if (brandPath === '/studio') return 'breadcrumb_studio'
  if (brandPath === '/history') return 'breadcrumb_library'
  if (brandPath.startsWith('/history/')) return 'breadcrumb_generation_detail'
  if (brandPath === '/settings') return 'breadcrumb_settings'
  return null
}

export function AppShell({ children }: { children: ReactNode }) {
  const t = useTranslations('components.layout.app-shell')
  const locale = useLocale()
  const params = useParams()
  const pathname = usePathname()
  const router = useRouter()
  const currentBrandId = typeof params.brandId === 'string' ? params.brandId : undefined
  const { brands, accents, addBrand } = useBrands()
  const { profile } = useProfile()
  const [createOpen, setCreateOpen] = useState(false)
  const [navOpen, setNavOpen] = useState(false)
  const [sidebarClosed, setSidebarClosed] = useState(false)
  const [narrow, setNarrow] = useState(false)
  const drawerRef = useRef<HTMLDivElement>(null)

  const wearBrand = Boolean(currentBrandId) && !isNeutralRoute(pathname)
  const accent = currentBrandId ? accents[currentBrandId] : undefined
  const crumbBrand = brands.find((b) => b.id === currentBrandId)
  const pageLabelKey = getPageLabelKey(pathname, currentBrandId)
  const pageLabels = {
    breadcrumb_brands: t('breadcrumb_brands'),
    breadcrumb_notifications: t('breadcrumb_notifications'),
    breadcrumb_account: t('breadcrumb_account'),
    breadcrumb_admin: t('breadcrumb_admin'),
    breadcrumb_content: t('breadcrumb_content'),
    breadcrumb_brand_kit: t('breadcrumb_brand_kit'),
    breadcrumb_studio: t('breadcrumb_studio'),
    breadcrumb_library: t('breadcrumb_library'),
    breadcrumb_generation_detail: t('breadcrumb_generation_detail'),
    breadcrumb_settings: t('breadcrumb_settings'),
  }
  const fallbackPageLabels = locale === 'ar'
    ? {
      breadcrumb_brands: 'العلامات التجارية',
      breadcrumb_notifications: 'الإشعارات',
      breadcrumb_account: 'الحساب الشخصي',
      breadcrumb_admin: 'الإدارة',
      breadcrumb_content: 'توليد المحتوى بالذكاء الاصطناعي',
      breadcrumb_brand_kit: 'الهوية البصرية',
      breadcrumb_studio: 'استوديو التصاميم',
      breadcrumb_library: 'مكتبتي',
      breadcrumb_generation_detail: 'تفاصيل التوليد',
      breadcrumb_settings: 'الإعدادات',
    }
    : {
      breadcrumb_brands: 'Brands',
      breadcrumb_notifications: 'Notifications',
      breadcrumb_account: 'Personal account',
      breadcrumb_admin: 'Administration',
      breadcrumb_content: 'AI content generation',
      breadcrumb_brand_kit: 'Brand identity',
      breadcrumb_studio: 'Design studio',
      breadcrumb_library: 'My Library',
      breadcrumb_generation_detail: 'Generation details',
      breadcrumb_settings: 'Settings',
    }
  const translatedPageLabel = pageLabelKey ? pageLabels[pageLabelKey as keyof typeof pageLabels] : null
  const pageLabel = translatedPageLabel?.startsWith('components.')
    ? (pageLabelKey ? fallbackPageLabels[pageLabelKey as keyof typeof fallbackPageLabels] : null)
    : translatedPageLabel

  useEffect(() => setNavOpen(false), [pathname])

  useEffect(() => {
    const media = window.matchMedia('(max-width: 767px)')
    const sync = () => setNarrow(media.matches)
    sync()
    media.addEventListener('change', sync)
    return () => media.removeEventListener('change', sync)
  }, [])

  useEffect(() => {
    const el = drawerRef.current
    if (!el) return
    if (narrow && !navOpen) el.setAttribute('inert', '')
    else el.removeAttribute('inert')
  }, [narrow, navOpen])

  function handleBrandCreated(brand: Brand) {
    addBrand(brand)
    router.push(`/${brand.id}`)
  }

  const shell = (
    <div className={cn('grid h-screen grid-cols-1 overflow-hidden bg-background', sidebarClosed ? 'md:grid-cols-[0_1fr]' : 'md:grid-cols-[224px_1fr]')}>
      {navOpen && <button type="button" aria-label={t('close_menu')} className="fixed inset-0 z-30 bg-[#0B1220]/40 md:hidden" onClick={() => setNavOpen(false)} />}
      <div ref={drawerRef} className={cn('z-40 h-full w-[224px] bg-brand-cream max-md:fixed max-md:inset-y-0 max-md:start-0 max-md:shadow-lg max-md:transition-transform max-md:duration-fast max-md:ease-out md:static md:translate-x-0 md:transform-none md:transition-all md:duration-fast', sidebarClosed && 'md:w-0 md:-translate-x-full md:overflow-hidden', navOpen ? 'max-md:translate-x-0' : 'max-md:-translate-x-full rtl:max-md:translate-x-full')}>
        <AppSidebar brands={brands} accents={accents} currentBrandId={currentBrandId} profile={profile} onCreateBrand={() => setCreateOpen(true)} onClose={() => { setNavOpen(false); setSidebarClosed(true) }} />
      </div>
      <div className="flex min-w-0 flex-col overflow-hidden">
        <header className="flex h-[60px] shrink-0 items-center gap-2 border-b border-brand-accent/30 bg-brand-cream px-3 md:px-[52px]">
          <button type="button" onClick={() => { setSidebarClosed(false); setNavOpen(true) }} aria-label={t('open_menu')} className={cn('inline-flex h-9 w-9 items-center justify-center rounded-md hover:bg-accent', !sidebarClosed && 'md:hidden')}><PanelLeft className="h-4 w-4" /></button>
          <span className="font-logo text-[20px] font-semibold leading-none text-brand-headline md:hidden">TRENDY AI</span>
          <div dir={locale === 'ar' ? 'ltr' : 'rtl'} className="flex min-w-0 flex-1 items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Link href="/notifications" aria-label={t('notifications')} aria-current={pathname === '/notifications' ? 'page' : undefined} className={cn('relative inline-flex h-9 w-9 items-center justify-center rounded-full text-brand-headline/70 no-underline transition-colors duration-fast hover:bg-brand-bg/60', pathname === '/notifications' && 'bg-brand-bg text-brand-primary')}>
                <Bell className="h-[18px] w-[18px]" />
                <span className="absolute end-2 top-2 h-1.5 w-1.5 rounded-full bg-brand-primary" />
              </Link>
              <LanguageSwitcher />
            </div>
            <nav dir={locale} aria-label={t('breadcrumb_label')} className="hidden items-center gap-[5px] font-readex text-[13px] md:flex">
              {crumbBrand && <span className="text-brand-headline/50">{crumbBrand.name}</span>}
              {pageLabel && <><span className="text-brand-headline/40">/</span><span className="font-semibold text-brand-primary">{pageLabel}</span></>}
            </nav>
          </div>
        </header>
        <main className="min-w-0 flex-1 overflow-y-auto px-4 py-5 md:px-[30px] md:py-6">{children}</main>
      </div>
      <CreateBrandModal open={createOpen} onOpenChange={setCreateOpen} onBrandCreated={handleBrandCreated} />
    </div>
  )

  if (wearBrand) return <BrandWorkspace color={accent}>{shell}</BrandWorkspace>
  return shell
}