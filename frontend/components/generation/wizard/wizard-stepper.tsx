'use client'

import { Check } from 'lucide-react'
import { cn } from '@/lib/utils'

interface WizardStepperProps {
  /** أسماء الخطوات بالترتيب */
  steps: string[]
  /** رقم الخطوة الحالية (يبدأ من 0) */
  currentStep: number
  /** أبعد خطوة وصلها المستخدم، حتى يقدر يرجع لها بالضغط */
  furthestStep: number
  onStepClick: (index: number) => void
  ariaLabel: string
}

export function WizardStepper({
  steps,
  currentStep,
  furthestStep,
  onStepClick,
  ariaLabel,
}: WizardStepperProps) {
  return (
    <nav aria-label={ariaLabel} className="border-b border-brand-accent/15 px-4 py-[18px] sm:px-7">
      <ol className="flex items-center">
        {steps.map((label, index) => {
          const isCurrent = index === currentStep
          const isDone = index < currentStep
          const isReachable = index <= furthestStep
          const isLast = index === steps.length - 1

          return (
            <li key={label} className={cn('flex items-center', !isLast && 'flex-1')}>
              <button
                type="button"
                onClick={() => onStepClick(index)}
                disabled={!isReachable}
                aria-current={isCurrent ? 'step' : undefined}
                className="flex shrink-0 items-center gap-2 py-0.5 disabled:cursor-default"
              >
                <span
                  className={cn(
                    'flex h-[26px] w-[26px] items-center justify-center rounded-full text-[11px] font-extrabold',
                    isCurrent || isDone
                      ? 'bg-brand-primary text-white'
                      : 'bg-brand-bg text-brand-headline/40',
                  )}
                >
                  {isDone ? <Check className="h-3 w-3" strokeWidth={3} /> : index + 1}
                </span>
                <span
                  className={cn(
                    'whitespace-nowrap text-[12.5px]',
                    isCurrent ? 'font-bold text-brand-headline' : 'hidden font-medium sm:inline',
                    isDone && 'text-brand-headline',
                    !isCurrent && !isDone && 'text-brand-headline/40',
                  )}
                >
                  {label}
                </span>
              </button>

              {!isLast && (
                <span
                  aria-hidden="true"
                  className={cn(
                    'mx-2.5 h-[1.5px] min-w-[12px] flex-1',
                    isDone ? 'bg-brand-primary' : 'bg-brand-accent/20',
                  )}
                />
              )}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}