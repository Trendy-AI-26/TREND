'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import { inputClass } from './shared'

export function TagInput({ label, value, onChange }: { label: string; value: string[]; onChange: (value: string[]) => void }) {
  const [draft, setDraft] = useState(''); const t = useTranslations('adminUI')
  function add() { const tags = draft.split(',').map(tag => tag.trim()).filter(Boolean); if (tags.length) onChange(Array.from(new Set([...value, ...tags]))); setDraft('') }
  return <div className="space-y-2"><label className="block text-sm">{label}<input className={inputClass} value={draft} placeholder={t('tagHint')} onChange={event => setDraft(event.target.value)} onBlur={add} onKeyDown={event => { if (event.key === 'Enter' || event.key === ',') { event.preventDefault(); add() } }} /></label><div className="flex flex-wrap gap-1">{value.map(tag => <button key={tag} type="button" aria-label={t('removeTag', { tag })} onClick={() => onChange(value.filter(item => item !== tag))} className="rounded-full bg-brand-cream px-3 py-1 text-xs">{tag} ×</button>)}</div></div>
}
