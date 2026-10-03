'use client'

import { LibraryView } from '@/components/history/library-view'

export default function HistoryPage({ params }: { params: { brandId: string } }) {
  return <LibraryView brandId={params.brandId} />
}
