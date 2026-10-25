// BYOK UI is temporarily disabled while provider-key management is being redesigned.
export default function KeysPage() {
  return (
    <div className="space-y-2">
      <h1 className="text-[30px] font-semibold leading-[1.16] tracking-tight">Provider keys</h1>
      <p className="text-muted-foreground">Provider key management is temporarily unavailable.</p>
    </div>
  )
}

// import { useTranslations } from 'next-intl';
// import { useState } from 'react'
// import { useParams } from 'next/navigation'
// import { Plus } from 'lucide-react'
// import { useKeys } from '@/hooks/use-keys'
// import { ProviderTabs } from '@/components/keys/provider-tabs'
// import { KeyCard } from '@/components/keys/key-card'
// import { AddKeyModal } from '@/components/keys/add-key-modal'
// import { Button } from '@/components/ui/button'
// import { Notice } from '@/components/ui/notice'
// import { apiRequest } from '@/lib/api'
// import { providerLabel } from '@/lib/providers'
// import { ProviderKey, ValidateKeyResponse } from '@/types'

// export default function KeysPage() {
//   const t = useTranslations('app.(dashboard).[brandId].keys.page');
//   const tNoKey = useTranslations('components.generation.no-key-notice');
//   const params = useParams()
//   const brandId = Array.isArray(params.brandId) ? params.brandId[0] : params.brandId ?? ''
//   const { keys, loading, error, refetch } = useKeys(brandId)

//   const [showAddModal, setShowAddModal] = useState(false)
//   const [addModalProvider, setAddModalProvider] = useState<'openai' | 'gemini'>('openai')
//   const [validatingKeyId, setValidatingKeyId] = useState<string | null>(null)
//   const [actionError, setActionError] = useState<string | null>(null)

//   const handleValidate = async (keyId: string) => {
//     setValidatingKeyId(keyId)
//     setActionError(null)
//     try {
//       await apiRequest<ValidateKeyResponse>(`/brands/${brandId}/keys/${keyId}/validate`, {
//         method: 'POST',
//       })
//       refetch()
//     } catch (err) {
//       setActionError(err instanceof Error ? err.message : t('validation_failed'))
//     } finally {
//       setValidatingKeyId(null)
//     }
//   }

//   const handleActivate = async (keyId: string) => {
//     setActionError(null)
//     try {
//       await apiRequest<ProviderKey>(`/brands/${brandId}/keys/${keyId}/activate`, {
//         method: 'PATCH',
//       })
//       refetch()
//     } catch (err) {
//       setActionError(err instanceof Error ? err.message : t('activation_failed'))
//     }
//   }

//   const handleDelete = async (keyId: string) => {
//     setActionError(null)
//     try {
//       await apiRequest(`/brands/${brandId}/keys/${keyId}`, { method: 'DELETE' })
//       refetch()
//     } catch (err) {
//       setActionError(err instanceof Error ? err.message : t('deletion_failed'))
//     }
//   }

//   const handleAddClick = (provider: 'openai' | 'gemini') => {
//     setAddModalProvider(provider)
//     setShowAddModal(true)
//   }

//   if (loading) {
//     return <p className="text-muted-foreground">{t('loading')}</p>
//   }

//   if (error) {
//     return <p className="text-destructive">{t('failed_to_load_keys')}</p>
//   }

//   return (
//     <div className="space-y-6">
//       <div className="flex items-center justify-between gap-4">
//         <h1 className="text-[30px] font-semibold leading-[1.16] tracking-tight">{t('keys')}</h1>
//         <Button type="button" onClick={() => handleAddClick('openai')}>
//           <Plus className="h-4 w-4" />{t('add_key')}</Button>
//       </div>

//       {actionError && <Notice variant="danger">{actionError}</Notice>}

//       <ProviderTabs keys={keys}>
//         {(filteredKeys, activeProvider) => (
//           <div className="space-y-2.5">
//             {filteredKeys.length === 0 ? (
//               <Notice variant="warning">
//                 {tNoKey('no_provider_key_yet', { provider: providerLabel(activeProvider) })}{' '}
//                 <button
//                   type="button"
//                   onClick={() => handleAddClick(activeProvider)}
//                   className="font-medium underline underline-offset-2"
//                 >
//                   {tNoKey('add_one')}
//                 </button>{' '}
//                 {tNoKey('to_generate_with_provider')}
//               </Notice>
//             ) : (
//               filteredKeys.map((k) => (
//                 <KeyCard
//                   key={k.id}
//                   keyData={k}
//                   onValidate={handleValidate}
//                   onActivate={handleActivate}
//                   onDelete={handleDelete}
//                   isValidating={validatingKeyId === k.id}
//                 />
//               ))
//             )}
//           </div>
//         )}
//       </ProviderTabs>

//       <AddKeyModal
//         brandId={brandId}
//         open={showAddModal}
//         onOpenChange={setShowAddModal}
//         onKeyAdded={refetch}
//         defaultProvider={addModalProvider}
//       />
//     </div>
//   )
// }
