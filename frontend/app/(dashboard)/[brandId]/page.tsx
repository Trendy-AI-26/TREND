import { redirect } from 'next/navigation'

export default function BrandPage({ params }: { params: { brandId: string } }) {
  redirect(`/dashboard?brandId=${params.brandId}`)
}
