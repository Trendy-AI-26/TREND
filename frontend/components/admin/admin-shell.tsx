'use client'

import { createContext, useContext, useState } from 'react'
import Image from 'next/image'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { Menu, LayoutDashboard, Users, Palette, Images, TrendingUp, ScrollText, LogOut } from 'lucide-react'
import { logout } from '@/lib/api'
import type { AuthUser } from '@/lib/auth/session'
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

const AdminContext = createContext('')
export const useAdminId = () => useContext(AdminContext)
export const adminLinks = [
  { href: '/admin', key: 'overview', icon: LayoutDashboard },
  { href: '/admin/users', key: 'users', icon: Users },
  { href: '/admin/brands', key: 'brands', icon: Palette },
  { href: '/admin/generations', key: 'generations', icon: Images },
  { href: '/admin/trends', key: 'trends', icon: TrendingUp },
  { href: '/admin/audit-log', key: 'audit', icon: ScrollText },
] as const

export function AdminSidebar({ user, onNavigate }: { user: AuthUser; onNavigate?: () => void }) {
  const t = useTranslations('adminUI'); const pathname = usePathname(); const router = useRouter()
  async function handleLogout() { await logout(); router.push('/login'); router.refresh() }
  return <aside className="flex h-full w-60 flex-col border-e border-brand-accent/30 bg-brand-cream p-4 text-brand-headline">
    <Link href="/admin" onClick={onNavigate} className="mb-2 flex items-center gap-2 py-3 no-underline"><Image src="/trendy_logo.png" alt="TRENDY AI" width={36} height={36} /><span className="font-logo text-xl">TRENDY AI</span></Link>
    <p className="mb-6 text-xs text-brand-primary">{t('section')}</p>
    <nav aria-label={t('section')} className="space-y-2">{adminLinks.map(({ href, key, icon: Icon }) => <Link key={href} href={href} onClick={onNavigate} aria-current={pathname === href ? 'page' : undefined} className={cn('flex items-center gap-3 rounded-lg border-s-2 border-transparent px-3 py-3 text-sm no-underline hover:bg-brand-bg', pathname === href && 'border-brand-primary bg-brand-weaker font-semibold text-brand-primary')}><Icon className="h-4 w-4" />{t(key)}</Link>)}</nav>
    <div className="mt-auto space-y-4 pt-10"><Link href="/dashboard" className="block text-sm text-brand-primary" onClick={onNavigate}>{t('backToApp')}</Link><p className="truncate text-sm" title={user.email}>{user.full_name || user.email}</p><Button variant="outline" className="w-full gap-2" onClick={handleLogout}><LogOut className="h-4 w-4" />{t('logout')}</Button></div>
  </aside>
}

export function AdminShell({ user, children }: { user: AuthUser; children: React.ReactNode }) {
  const [open, setOpen] = useState(false); const t = useTranslations('adminUI')
  return <AdminContext.Provider value={user.id}><div className="min-h-screen bg-brand-bg font-readex text-brand-headline md:flex"><div className="sticky top-0 hidden h-screen md:block"><AdminSidebar user={user} /></div><Dialog open={open} onOpenChange={setOpen}><DialogContent closeLabel={t('close')} aria-describedby={undefined} style={{ left: 'auto', right: 'auto', insetInlineStart: 0, top: 0, transform: 'none' }} className="h-dvh w-60 max-w-none gap-0 border-0 p-0"><DialogTitle className="sr-only">{t('section')}</DialogTitle><AdminSidebar user={user} onNavigate={() => setOpen(false)} /></DialogContent></Dialog><div className="min-w-0 flex-1"><div className="border-b border-brand-accent/30 p-3 md:hidden"><Button variant="outline" aria-label={t('openMenu')} onClick={() => setOpen(true)}><Menu className="h-5 w-5" /></Button></div><main className="mx-auto max-w-[1600px] p-4 md:p-8">{children}</main></div></div></AdminContext.Provider>
}
