'use client'

import { useId } from 'react'
import { useLocale, useTranslations } from 'next-intl'
import type { Overview } from '@/hooks/admin/types'

export function DailyChart({ daily }: { daily: Overview['daily'] }) {
  const t = useTranslations('adminUI'); const locale = useLocale(); const id = useId()
  const number = new Intl.NumberFormat(locale)
  const date = (value: string) => new Intl.DateTimeFormat(locale, { month: 'short', day: 'numeric', timeZone: 'UTC' }).format(new Date(`${value}T00:00:00Z`))
  const max = Math.max(1, ...daily.flatMap(day => [day.succeeded, day.failed]))
  const width = Math.max(1, daily.length) * 24
  return <figure aria-labelledby={`${id}-title`}><figcaption id={`${id}-title`} className="mb-4 font-semibold">{t('dailyChart')}</figcaption><div className="mb-3 flex gap-5 text-sm"><span className="flex items-center gap-2"><i className="h-3 w-3 rounded-sm bg-brand-primary" />{t('statuses.succeeded')}</span><span className="flex items-center gap-2"><i className="h-3 w-3 rounded-sm bg-brand-accent" />{t('statuses.failed')}</span></div><svg role="img" aria-labelledby={`${id}-title ${id}-description`} viewBox={`0 0 ${width} 200`} className="h-56 w-full" preserveAspectRatio="none"><desc id={`${id}-description`}>{t('chartDescription')}</desc><line x1="0" y1="170" x2={width} y2="170" className="stroke-brand-accent" />{daily.map((day, index) => <g key={day.date}><title>{date(day.date)}: {t('statuses.succeeded')} {number.format(day.succeeded)}, {t('statuses.failed')} {number.format(day.failed)}</title><rect x={index * 24 + 3} y={170 - day.succeeded / max * 150} width="8" height={day.succeeded / max * 150} className="fill-brand-primary" /><rect x={index * 24 + 12} y={170 - day.failed / max * 150} width="8" height={day.failed / max * 150} className="fill-brand-accent" />{(index === 0 || index === daily.length - 1 || index % 7 === 0) && <text x={index * 24 + 12} y="193" textAnchor="middle" fontSize="8" className="fill-brand-headline">{date(day.date)}</text>}</g>)}</svg><details className="mt-2 text-sm"><summary className="cursor-pointer text-brand-primary">{t('chartData')}</summary><table className="mt-3 w-full text-start"><thead><tr><th className="text-start">{t('date')}</th><th>{t('statuses.succeeded')}</th><th>{t('statuses.failed')}</th></tr></thead><tbody>{daily.map(day => <tr key={day.date}><td>{date(day.date)}</td><td className="text-center">{number.format(day.succeeded)}</td><td className="text-center">{number.format(day.failed)}</td></tr>)}</tbody></table></details></figure>
}
