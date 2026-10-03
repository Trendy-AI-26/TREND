import type { ReactNode } from 'react'

interface WizardFieldProps {
  label: string
  htmlFor?: string
  required?: boolean
  optionalLabel?: string
  hint?: string
  error?: string
  counter?: string
  children: ReactNode
}

// غلاف موحّد لكل سؤال: العنوان، النجمة، الوصف، الخطأ، وعداد الأحرف
export function WizardField({
  label,
  htmlFor,
  required = false,
  optionalLabel,
  hint,
  error,
  counter,
  children,
}: WizardFieldProps) {
  return (
    <div>
      <div className="flex items-baseline gap-1.5">
        <label htmlFor={htmlFor} className="text-[14px] font-bold leading-[21px] text-brand-headline">
          {label}
          {required && (
            <span aria-hidden="true" className="ms-1 text-destructive">
              *
            </span>
          )}
        </label>
        {optionalLabel && <span className="text-[11.5px] text-brand-headline/40">{optionalLabel}</span>}
      </div>

      {hint && <p className="mt-1 text-[12.5px] leading-[19px] text-brand-headline/40">{hint}</p>}

      <div className="mt-3">{children}</div>

      {(error || counter) && (
        <div className="mt-1.5 flex items-start justify-between gap-3 text-[11.5px] leading-[17px]">
          {error ? (
            <p role="alert" className="text-destructive">
              {error}
            </p>
          ) : (
            <span />
          )}
          {counter && <span className="shrink-0 tabular-nums text-brand-headline/40">{counter}</span>}
        </div>
      )}
    </div>
  )
}