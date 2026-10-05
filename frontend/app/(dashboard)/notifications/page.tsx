'use client'

import Link from 'next/link'
import { ArrowLeft, Bell, CheckCircle2, Palette, WandSparkles } from 'lucide-react'
import { useTranslations } from 'next-intl'
import { useEffect } from 'react'
import { useNotifications, type NotificationType } from '@/hooks/use-notifications'

export default function NotificationsPage() {
    const t = useTranslations('notifications')
    const { notifications, markAllAsRead } = useNotifications()

    useEffect(() => {
        if (notifications.some((notification) => notification.unread)) markAllAsRead()
    }, [notifications, markAllAsRead])

    function icon(type: NotificationType) {
        if (type === 'generation') return <WandSparkles className="h-5 w-5" />
        if (type === 'brand') return <Palette className="h-5 w-5" />
        return <Bell className="h-5 w-5" />
    }

    return (
        <div className="-mx-4 -my-5 min-h-full w-[calc(100%+2rem)] bg-brand-cream px-5 py-6 sm:px-8 md:-mx-[30px] md:-my-6 md:w-[calc(100%+60px)] md:px-10 md:py-8">
            <div className="w-full min-w-0">
                <div className="mb-8 flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
                    <div>
                        <p className="font-tajawal text-[13px] text-brand-primary">{t('eyebrow')}</p>
                        <h1 className="mt-2 font-el-messiri text-[38px] font-bold leading-tight text-brand-headline sm:text-[48px]">{t('title')}</h1>
                        <p className="mt-2 max-w-[620px] font-tajawal text-[14px] text-brand-headline/60">{t('description')}</p>
                    </div>
                    <Link href="/dashboard" className="inline-flex h-10 shrink-0 items-center justify-center gap-2 rounded-xl border border-brand-accent/30 bg-white px-4 font-tajawal text-[13px] text-brand-headline no-underline transition hover:border-brand-primary hover:text-brand-primary">
                        <ArrowLeft className="h-4 w-4 rtl:rotate-180" />
                        {t('backToDashboard')}
                    </Link>
                </div>

                {notifications.length > 0 ? (
                    <section className="w-full overflow-hidden rounded-[22px] border border-brand-accent/25 bg-white shadow-card">
                        {notifications.map((notification, index) => (
                            <article key={notification.id} className={`flex min-h-[112px] items-center gap-5 px-6 py-5 transition-colors hover:bg-brand-cream/30 sm:px-8 ${index !== notifications.length - 1 ? 'border-b border-brand-accent/20' : ''}`}>
                                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-brand-bg text-brand-primary">{icon(notification.type)}</div>
                                <div className="min-w-0 flex-1 text-start">
                                    <div className="flex items-start gap-2">
                                        <h2 className="font-tajawal text-[15px] font-bold text-brand-headline">{notification.title}</h2>
                                        {notification.unread && <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-brand-primary" aria-label={t('unread')} />}
                                    </div>
                                    <p className="mt-1 font-tajawal text-[13px] text-brand-headline/55">{notification.description}</p>
                                </div>
                                <time className="shrink-0 font-tajawal text-[12px] text-brand-headline/45">{notification.time}</time>
                            </article>
                        ))}
                    </section>
                ) : (
                    <section className="flex min-h-[310px] w-full flex-col items-center justify-center rounded-[22px] border border-brand-accent/25 bg-white px-6 text-center shadow-card">
                        <span className="flex h-16 w-16 items-center justify-center rounded-full bg-brand-bg text-brand-primary"><Bell className="h-7 w-7" /></span>
                        <h2 className="mt-5 font-el-messiri text-[21px] font-semibold text-brand-headline">{t('emptyTitle')}</h2>
                        <p className="mt-2 max-w-[430px] font-tajawal text-[13px] text-brand-headline/55">{t('emptyDescription')}</p>
                    </section>
                )}

                <div className="mt-5 flex items-center justify-center gap-2 font-tajawal text-[12px] text-brand-headline/45">
                    <CheckCircle2 className="h-4 w-4 text-brand-primary/70" />
                    {notifications.length > 0 ? t('allCaughtUp') : t('waitingForGeneration')}
                </div>
            </div>
        </div>
    )
}