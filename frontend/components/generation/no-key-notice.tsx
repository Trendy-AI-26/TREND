'use client'

import { useLocale } from 'next-intl'
import { Notice } from '@/components/ui/notice'

export function NoKeyNotice() {
  const locale = useLocale()
  const message = locale === 'ar'
    ? 'يتم تشغيل التوليد باستخدام إعدادات الخادم الآمنة.'
    : 'Generation uses the secure server configuration.'

  return <Notice variant="info">{message}</Notice>
}
