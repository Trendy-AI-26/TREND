// 'use client'

// import { useTranslations } from 'next-intl';
// import { useState, type ReactNode } from 'react'
// import { ProviderKey } from '@/types'
// import { SegmentedControl } from '@/components/ui/segmented-control'

// type Provider = 'openai' | 'gemini'

// interface ProviderTabsProps {
//   keys: ProviderKey[]
//   children: (filteredKeys: ProviderKey[], activeProvider: Provider) => ReactNode
// }

// export function ProviderTabs({ keys, children }: ProviderTabsProps) {
//   const t = useTranslations('components.keys.provider-tabs');
//   const [activeProvider, setActiveProvider] = useState<Provider>('openai')
//   const filteredKeys = keys.filter((k) => k.provider === activeProvider)
//   const openaiCount = keys.filter((k) => k.provider === 'openai').length
//   const geminiCount = keys.filter((k) => k.provider === 'gemini').length

//   return (
//     <div className="space-y-4">
//       <SegmentedControl
//         aria-label={t('provider')}
//         value={activeProvider}
//         onChange={setActiveProvider}
//         options={[
//           { value: 'openai', label: t('openai_count', { count: openaiCount }) },
//           { value: 'gemini', label: t('gemini_count', { count: geminiCount }) },
//         ]}
//       />
//       {children(filteredKeys, activeProvider)}
//     </div>
//   )
// }
