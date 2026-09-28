'use client'

import { useTranslations } from 'next-intl';
import { useState } from 'react'
import { ArrowLeft, ArrowRight, Check } from 'lucide-react'
import { apiRequest } from '@/lib/api'
import { saveKit } from '@/hooks/use-kit'
import { useBrands } from '@/hooks/use-brands'
import { onBrandTextColor } from '@/components/brand/brand-workspace'
import { Brand } from '@/types'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { cn } from '@/lib/utils'

interface CreateBrandModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onBrandCreated: (brand: Brand) => void
}

const PRIMARY_COLORS = ['#7A1521', '#C49A55', '#1D1A19', '#3B82F6', '#10B981', '#8B5CF6', '#F97316']
const TOTAL_STEPS = 2

export function CreateBrandModal({ open, onOpenChange, onBrandCreated }: CreateBrandModalProps) {
  const t = useTranslations('components.brand.create-brand-modal');
  const { setAccent } = useBrands()
  const [step, setStep] = useState<1 | 2>(1)
  const [name, setName] = useState('')
  const [color, setColor] = useState(PRIMARY_COLORS[0])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const reset = () => {
    setStep(1)
    setName('')
    setColor(PRIMARY_COLORS[0])
    setError(null)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // الخطوة 1: بس ننتقل للخطوة 2
    if (step === 1) {
      if (name.trim()) setStep(2)
      return
    }


    setLoading(true)
    setError(null)
    try {
      const brand = await apiRequest<Brand>('/brands', {
        method: 'POST',
        body: JSON.stringify({ name: name.trim() }),
      })
      try {
        await saveKit(brand.id, {
          tagline: null,
          tone: null,
          audience: null,
          colors: [color],
          avoid_words: null,
        })
        setAccent(brand.id, color)
      } catch {
       
      }
      onBrandCreated(brand)
      reset()
      onOpenChange(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('create_failed'))
    } finally {
      setLoading(false)
    }
  }

  const handleOpenChange = (isOpen: boolean) => {
    if (!isOpen) reset()
    onOpenChange(isOpen)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-[440px] gap-0 rounded-2xl border-brand-accent/30 bg-white p-6 font-readex text-brand-headline sm:rounded-2xl">
        <DialogHeader className="gap-1 text-start sm:text-start">
          <p className="text-[12px] text-brand-headline/50">
            {t('step_of', { current: step, total: TOTAL_STEPS })}
          </p>
          <DialogTitle className="text-[18px] font-bold leading-normal tracking-normal">
            {step === 1 ? t('details_title') : t('primary_color_title')}
          </DialogTitle>
          <DialogDescription className="sr-only">{t('name_a_studio_you')}</DialogDescription>
        </DialogHeader>

        {/* شريط التقدم: قطعتين */}
        <div className="mt-4 flex gap-2" aria-hidden="true">
          {[1, 2].map((n) => (
            <span
              key={n}
              className={cn(
                'h-[3px] flex-1 rounded-full',
                n <= step ? 'bg-brand-primary' : 'bg-brand-accent/30',
              )}
            />
          ))}
        </div>

        <form onSubmit={handleSubmit} className="mt-6">
          {step === 1 ? (
            <div className="space-y-2">
              <Label htmlFor="brand-name" className="text-[12px] font-medium text-brand-headline/70">
                {t('name_label')}
              </Label>
              <Input
                id="brand-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={t('name_placeholder')}
                autoFocus
                className="h-12 rounded-xl border-brand-accent/40 bg-white"
              />
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-[12px] font-medium text-brand-headline/70">{t('pick_color')}</p>
              <div className="flex flex-wrap gap-3">
                {PRIMARY_COLORS.map((hex) => {
                  const selected = hex === color
                  return (
                    <button
                      key={hex}
                      type="button"
                      onClick={() => setColor(hex)}
                      aria-label={hex}
                      aria-pressed={selected}
                      title={hex}
                      className={cn(
                        'flex h-10 w-10 items-center justify-center rounded-lg transition-transform hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary/50 focus-visible:ring-offset-2',
                        selected && 'ring-2 ring-brand-headline ring-offset-2',
                      )}
                      style={{ background: hex }}
                    >
                      {selected && (
                        <Check className="h-4 w-4" style={{ color: onBrandTextColor(hex) }} />
                      )}
                    </button>
                  )
                })}
              </div>

              <div className="flex items-center gap-3 rounded-xl border border-brand-accent/30 bg-white p-3">
                <span
                  className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-[14px] font-bold"
                  style={{
                    backgroundColor: `color-mix(in srgb, ${color} 15%, white)`,
                    color,
                  }}
                >
                  {name.trim().charAt(0).toUpperCase()}
                </span>
                <span className="h-6 w-[3px] rounded-full" style={{ background: color }} />
                <span className="truncate text-[14px] font-bold">{name.trim()}</span>
              </div>
            </div>
          )}

          {error && <p className="mt-3 text-[13px] text-destructive">{error}</p>}

      
          <div className="mt-8 flex items-center gap-2 ltr:flex-row-reverse">
            {step === 1 ? (
              <Button key="next" type="submit" disabled={!name.trim()} className="h-11 px-5">
                {t('next')}
                <ArrowLeft className="h-4 w-4 ltr:rotate-180" />
              </Button>
            ) : (
              <Button key="create" type="submit" disabled={loading} className="h-11 px-6">
                {loading ? t('creating') : t('create')}
              </Button>
            )}
            <Button
              type="button"
              variant="outline"
              className="h-11 px-4"
              onClick={() => handleOpenChange(false)}
            >
              {t('cancel')}
            </Button>
            {step === 2 && (
              <Button
                type="button"
                variant="outline"
                className="h-11 px-4"
                onClick={() => setStep(1)}
                disabled={loading}
              >
                <ArrowRight className="h-4 w-4 ltr:rotate-180" />
                {t('back')}
              </Button>
            )}
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}