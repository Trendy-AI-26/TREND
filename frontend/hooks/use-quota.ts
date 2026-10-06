'use client'

import { useCallback, useEffect, useState } from 'react'
import { apiRequest } from '@/lib/api'
import type { QuotaSummary } from '@/types'

interface UseQuotaResult {
    quota: QuotaSummary | null
    loading: boolean
    error: string | null
    refetch: () => void
}

export function useQuota(): UseQuotaResult {
    const [quota, setQuota] = useState<QuotaSummary | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [requestId, setRequestId] = useState(0)

    const refetch = useCallback(() => setRequestId((current) => current + 1), [])

    useEffect(() => {
        let cancelled = false

        async function loadQuota() {
            setLoading(true)
            setError(null)
            try {
                const data = await apiRequest<QuotaSummary>('/me/quota')
                if (!cancelled) setQuota(data)
            } catch (err) {
                if (!cancelled) {
                    setError(err instanceof Error ? err.message : 'Failed to load quota')
                }
            } finally {
                if (!cancelled) setLoading(false)
            }
        }

        loadQuota()
        return () => {
            cancelled = true
        }
    }, [requestId])

    return { quota, loading, error, refetch }
}
