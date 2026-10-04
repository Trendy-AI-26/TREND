import { BrandDashboard } from '@/components/brand/brand-dashboard'

export default function BrandDashboardPage({
  params,
}: {
  params: { brandId: string }
}) {
  return <BrandDashboard brandId={params.brandId} />
}
