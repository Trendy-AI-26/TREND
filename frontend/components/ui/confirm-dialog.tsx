'use client'

import * as React from 'react'
import { useTranslations } from 'next-intl'
import { Info, TriangleAlert } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { cn } from '@/lib/utils'

export type ConfirmTone = 'danger' | 'default'

/* -------------------------------------------------------------------------- */
/* ConfirmDialog: the one confirmation UI of the site (controlled)            */
/* -------------------------------------------------------------------------- */

export interface ConfirmDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  title: React.ReactNode
  description?: React.ReactNode
  confirmLabel: string
  cancelLabel: string
  tone?: ConfirmTone
  /** Disables both buttons and shows `loadingLabel` on the confirm button. */
  loading?: boolean
  loadingLabel?: string
  onConfirm: () => void
}

/**
 * Controlled confirmation dialog. Use it directly when the confirm action is
 * async and the dialog must stay open meanwhile (delete dialogs), or use
 * `useConfirm()` for a simple "are you sure?" that returns a promise.
 */
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel,
  cancelLabel,
  tone = 'default',
  loading = false,
  loadingLabel,
  onConfirm,
}: ConfirmDialogProps) {
  const danger = tone === 'danger'
  const Icon = danger ? TriangleAlert : Info

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        // Without a description, tell Radix not to expect one.
        {...(description ? {} : { 'aria-describedby': undefined })}
        className="max-w-[360px] gap-0 rounded-2xl border-brand-accent/30 bg-white p-6 font-readex text-brand-headline sm:rounded-2xl"
      >
        <DialogHeader className="gap-0 text-start sm:text-start">
          <div className="flex items-start gap-3 rtl:flex-row-reverse">
            <span
              className={cn(
                'inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl',
                danger ? 'bg-destructive/10 text-destructive' : 'bg-brand-primary/10 text-brand-primary',
              )}
            >
              <Icon className="h-5 w-5" aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <DialogTitle className="text-[16px] font-bold leading-normal tracking-normal">
                {title}
              </DialogTitle>
              {description ? (
                <DialogDescription className="mt-2 text-[13px] leading-relaxed text-brand-headline/60">
                  {description}
                </DialogDescription>
              ) : null}
            </div>
          </div>
        </DialogHeader>

        <div className="mt-8 flex items-center gap-2 ltr:flex-row-reverse">
          <Button
            type="button"
            variant={danger ? 'destructive' : 'default'}
            onClick={onConfirm}
            disabled={loading}
            className="h-10 px-5"
          >
            {loading && loadingLabel ? loadingLabel : confirmLabel}
          </Button>
          <Button
            type="button"
            variant="outline"
            className="h-10 px-4"
            onClick={() => onOpenChange(false)}
            disabled={loading}
          >
            {cancelLabel}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

/* -------------------------------------------------------------------------- */
/* ConfirmProvider + useConfirm: promise API                                  */
/* -------------------------------------------------------------------------- */

export interface ConfirmOptions {
  title: React.ReactNode
  description?: React.ReactNode
  /** Defaults to the translated "Confirm". */
  confirmLabel?: string
  /** Defaults to the translated "Cancel". */
  cancelLabel?: string
  /** `danger` styles the dialog and the confirm button as destructive. Defaults to `default`. */
  tone?: ConfirmTone
}

type ConfirmFn = (options: ConfirmOptions) => Promise<boolean>

const ConfirmContext = React.createContext<ConfirmFn | null>(null)

interface PendingConfirm {
  options: ConfirmOptions
  open: boolean
}

export function ConfirmProvider({ children }: { children: React.ReactNode }) {
  const t = useTranslations('confirm')
  const [pending, setPending] = React.useState<PendingConfirm | null>(null)
  const resolver = React.useRef<((value: boolean) => void) | null>(null)

  const settle = React.useCallback((value: boolean) => {
    resolver.current?.(value)
    resolver.current = null
    // Keep the options so the content stays visible during the close animation.
    setPending((current) => (current ? { ...current, open: false } : current))
  }, [])

  const confirm = React.useCallback<ConfirmFn>((options) => {
    // A new request replaces an unanswered one, which counts as "no".
    resolver.current?.(false)
    return new Promise<boolean>((resolve) => {
      resolver.current = resolve
      setPending({ options, open: true })
    })
  }, [])

  // Never leave a caller hanging if the provider unmounts while a dialog is open.
  React.useEffect(() => () => resolver.current?.(false), [])

  const options = pending?.options

  return (
    <ConfirmContext.Provider value={confirm}>
      {children}
      {pending && options ? (
        <ConfirmDialog
          open={pending.open}
          onOpenChange={(open) => {
            if (!open) settle(false)
          }}
          title={options.title}
          description={options.description}
          confirmLabel={options.confirmLabel ?? t('confirm')}
          cancelLabel={options.cancelLabel ?? t('cancel')}
          tone={options.tone}
          onConfirm={() => settle(true)}
        />
      ) : null}
    </ConfirmContext.Provider>
  )
}

/** Returns `confirm(options) => Promise<boolean>`. Must be used under `<ConfirmProvider>`. */
export function useConfirm(): ConfirmFn {
  const confirm = React.useContext(ConfirmContext)
  if (!confirm) {
    throw new Error('useConfirm must be used within a <ConfirmProvider>')
  }
  return confirm
}
