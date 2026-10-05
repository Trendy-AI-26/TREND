import { headers } from 'next/headers'
import { notFound, redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import { GenerationWizard } from '@/components/generation/wizard/generation-wizard'
import type { Brand } from '@/types'

async function getServerApiUrl(path: string) {
  const serverBase = process.env.NEXT_SERVER_API_URL || process.env.NEXT_PUBLIC_API_URL
  if (!serverBase) throw new Error('API base URL is not configured')
  if (serverBase.startsWith('http://') || serverBase.startsWith('https://')) {
    const base = new URL(serverBase)
    const basePathname = base.pathname.replace(/\/+$/, '')
    const nextPathname = path.replace(/^\/+/, '')
    base.pathname = [basePathname, nextPathname].filter(Boolean).join('/') || '/'
    return base.toString()
  }
  const requestHeaders = await headers()
  const host = requestHeaders.get('x-forwarded-host') || requestHeaders.get('host')
  const protocol = requestHeaders.get('x-forwarded-proto') || 'http'
  if (!host) throw new Error('Request host is unavailable for server-side API call')
  const normalizedBase = serverBase.replace(/\/+$/, '')
  const normalizedPath = path.replace(/^\/+/, '')
  return new URL(`${normalizedBase}/${normalizedPath}`, `${protocol}://${host}`).toString()
}

async function loadBrand(brandId: string): Promise<Brand> {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  const { data: { session } } = await supabase.auth.getSession()
  if (!user || !session?.access_token) redirect('/login')

  const apiUrl = await getServerApiUrl(`/brands/${brandId}`)
  const response = await fetch(apiUrl, {
    headers: { Authorization: `Bearer ${session.access_token}` },
    cache: 'no-store',
  })
  if (response.status === 404) notFound()
  if (response.status === 401) redirect('/login')
  if (!response.ok) throw new Error('Failed to load brand')

  const payload: unknown = await response.json()
  if (
    !payload ||
    typeof payload !== 'object' ||
    typeof (payload as Record<string, unknown>).name !== 'string' ||
    !('logo_url' in (payload as Record<string, unknown>))
  ) {
    throw new Error('Invalid brand payload')
  }
  return payload as Brand
}

export default async function BrandGeneratorPage({
  params,
}: {
  params: { brandId: string }
}) {
  const { brandId } = params
  const brand = await loadBrand(brandId)
  return (
      <GenerationWizard
      brandId={brandId}
      brandName={brand.name}
      brandHasLogo={Boolean(brand.logo_url)}
    />
  )
}
