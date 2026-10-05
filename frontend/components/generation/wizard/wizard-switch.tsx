'use client'

import { cn } from '@/lib/utils'

interface WizardSwitchProps {
  id: string
  label: string
  description?: string
  checked: boolean
  onChange: (checked: boolean) => void
}

// صف فيه عنوان ووصف، وزر تشغيل/إيقاف على الطرف الثاني
export function WizardSwitch({ id, label, description, checked, onChange }: WizardSwitchProps) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-[12px] border border-brand-accent/25 bg-white px-4 py-3.5">
      <div>
        <label htmlFor={id} className="cursor-pointer text-[13.5px] font-bold text-brand-headline">
          {label}
        </label>
        {description && (
          <p className="mt-0.5 text-[11.5px] leading-[17px] text-brand-headline/50">{description}</p>
        )}
      </div>

      <button
        id={id}
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={cn(
          'relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors',
          checked ? 'bg-brand-primary' : 'bg-brand-headline/20',
        )}
      >
        <span
          className={cn(
            'inline-block h-5 w-5 rounded-full bg-white shadow-sm transition-transform',
            // بالعربي الزر بيتحرك لليسار لما يشتغل، وبالإنجليزي لليمين
            checked ? 'translate-x-[22px] rtl:-translate-x-[22px]' : 'translate-x-0.5 rtl:-translate-x-0.5',
          )}
        />
      </button>
    </div>
  )
}