import { useTranslations } from 'next-intl';
import { AdminStats } from '@/types'

interface AdminStatsCardsProps {
  stats: AdminStats
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-border px-4 py-[15px]">
      <p className="text-[12px] text-[#475569]">{label}</p>
      <p className="mt-1 text-[25px] font-semibold tabular-nums">{value}</p>
    </div>
  )
}

export function AdminStatsCards({ stats }: AdminStatsCardsProps) {
  const t = useTranslations('components.admin.admin-stats-cards');
  return (
    <div className="grid gap-3">
      <div className="grid gap-3 sm:grid-cols-3">
        <StatCard label={t('accounts')} value={stats.total_accounts} />
        <StatCard label={t('brands')} value={stats.total_brands} />
        <StatCard label={t('generations')} value={stats.total_generations} />
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label={t('pending')} value={stats.generations_by_status.pending} />
        <StatCard label={t('processing')} value={stats.generations_by_status.processing} />
        <StatCard label={t('succeeded')} value={stats.generations_by_status.succeeded} />
        <StatCard label={t('failed')} value={stats.generations_by_status.failed} />
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <StatCard label={t('openai_generations')} value={stats.generations_by_provider.openai} />
        <StatCard label={t('gemini_generations')} value={stats.generations_by_provider.gemini} />
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label={t('last_7_days')} value={stats.generations_last_7d} />
        <StatCard label={t('last_30_days')} value={stats.generations_last_30d} />
        <StatCard label={t('completed_brand_kits')} value={stats.brand_kits_complete} />
        <StatCard label={t('active_provider_keys')} value={stats.active_provider_keys} />
      </div>
    </div>
  )
}
