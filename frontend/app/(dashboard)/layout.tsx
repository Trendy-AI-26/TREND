'use client'

import { Suspense } from 'react'
import { AppShell } from '@/components/layout/app-shell'
import { BrandsProvider } from '@/components/providers/brands-provider'

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <BrandsProvider>
      <Suspense fallback={null}>
        <AppShell>{children}</AppShell>
      </Suspense>
    </BrandsProvider>
  )
}
