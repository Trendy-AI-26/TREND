'use client'

import { useCallback, useEffect, useState } from 'react'
import { apiRequest } from '@/lib/api'
import type { Page } from './types'

export function useAdminResource<T>(endpoint: string | null) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(!!endpoint)
  const [error, setError] = useState<unknown>(null)
  const [revision, setRevision] = useState(0)
  const refresh = useCallback(() => setRevision(value => value + 1), [])
  useEffect(() => {
    if (!endpoint) { setData(null); setLoading(false); return }
    const controller = new AbortController()
    setLoading(true)
    setError(null)
    setData(null)
    apiRequest<T>(endpoint, { signal: controller.signal }).then(value => {
      if (!controller.signal.aborted) setData(value)
    }).catch(err => {
      if (!controller.signal.aborted) setError(err)
    }).finally(() => {
      if (!controller.signal.aborted) setLoading(false)
    })
    return () => controller.abort()
  }, [endpoint, revision])
  return { data, loading, error, refresh }
}

export function useDebounced<T>(value: T, delay = 300) {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => { const timer = setTimeout(() => setDebounced(value), delay); return () => clearTimeout(timer) }, [value, delay])
  return debounced
}

export function useAdminList<T>(resource: string, filters: Record<string, string> = {}) {
  const [cursor, setCursor] = useState({ page: 1, key: '' })
  const key = new URLSearchParams(Object.entries(filters).filter(([, value]) => value !== '')).toString()
  const page = cursor.key === key ? cursor.page : 1
  const result = useAdminResource<Page<T>>(`/admin/${resource}?${key}${key ? '&' : ''}page=${page}&per_page=24`)
  const setPage = (next: number) => setCursor({ page: Math.max(1, next), key })
  return { ...result, page, setPage }
}
