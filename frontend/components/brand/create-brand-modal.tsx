'use client'

import { useTranslations } from 'next-intl';
import { useState } from 'react'
import { ArrowLeft, ArrowRight, Check } from 'lucide-react'
import { apiRequest } from '@/lib/api'
import { saveKit } from '@/hooks/use-kit'
import { useBrands } from '@/hooks/use-brands'
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

const CURATED_COLORS: { hex: string; nameKey: string }[] = [
  { hex: '#7A1521', nameKey: 'color_maroon' },
  { hex: '#1D1A19', nameKey: 'color_black' },
  { hex: '#D63384', nameKey: 'color_pink' },
  { hex: '#9333EA', nameKey: 'color_purple' },
  { hex: '#3B82F6', nameKey: 'color_blue' },
  { hex: '#64748B', nameKey: 'color_gray' },
  { hex: '#10B981', nameKey: 'color_green' },
  { hex: '#F97316', nameKey: 'color_orange' },
]
const TOTAL_STEPS = 2

function spectrumColor(x: number, y: number, width: number, height: number) {
  const hue = Math.max(0, Math.min(360, (x / width) * 360))
  const lightness = Math.max(8, 96 - (y / height) * 68)
  const saturation = 96
  const chroma = (1 - Math.abs((2 * lightness) / 100 - 1)) * (saturation / 100)
  const match = hue / 60
  const second = chroma * (1 - Math.abs((match % 2) - 1))
  const [r, g, b] = match < 1
    ? [chroma, second, 0]
    : match < 2
      ? [second, chroma, 0]
      : match < 3
        ? [0, chroma, second]
        : match < 4
          ? [0, second, chroma]
          : match < 5
            ? [second, 0, chroma]
            : [chroma, 0, second]
  const offset = lightness / 100 - chroma / 2
  return `#${[r, g, b].map((value) => Math.round((value + offset) * 255).toString(16).padStart(2, '0')).join('').toUpperCase()}`
}

export function CreateBrandModal({ open, onOpenChange, onBrandCreated }: CreateBrandModalProps) {
  const t = useTranslations('components.brand.create-brand-modal');
  const tColors = useTranslations('components.kit.steps.step-colors');
  const { setAccent } = useBrands()
  const [step, setStep] = useState<1 | 2>(1)
  const [name, setName] = useState('')
  const [color, setColor] = useState(CURATED_COLORS[0].hex)
  const [pickerPosition, setPickerPosition] = useState({ x: 0.78, y: 0.12 })
  const [pickerOpen, setPickerOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const reset = () => {
    setStep(1)
    setName('')
    setColor(CURATED_COLORS[0].hex)
    setPickerPosition({ x: 0.78, y: 0.12 })
    setPickerOpen(false)
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
          product_asset_id: null,
          tagline: null,
          audience: null,
          colors: [color],
          avoid_words: null,
          industry: null,
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
              <div className="space-y-3">
                <div className="grid grid-cols-4 gap-2">
                  {CURATED_COLORS.map(({ hex, nameKey }) => {
                    const selected = hex === color
                    return (
                      <button
                        key={hex}
                        type="button"
                        onClick={() => {
                          setColor(hex)
                          setPickerOpen(false)
                        }}
                        aria-label={tColors(nameKey)}
                        aria-pressed={selected}
                        title={tColors(nameKey)}
                        className={cn(
                          'relative flex h-10 w-full items-center justify-center overflow-hidden rounded-lg border border-black/10 transition-transform hover:scale-[1.03] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary/50 focus-visible:ring-offset-2',
                          selected && 'ring-2 ring-brand-headline ring-offset-2',
                        )}
                        style={{ background: hex }}
                      >
                        {selected && (
                          <span className="absolute end-1 top-1 inline-flex h-4 w-4 items-center justify-center rounded-full bg-white/90 shadow-sm">
                            <Check className="h-[10px] w-[10px]" style={{ color: hex }} />
                          </span>
                        )}
                      </button>
                    )
                  })}
                </div>
                <button
                  type="button"
                  aria-label={tColors('curated_palette')}
                  aria-expanded={pickerOpen}
                  onClick={() => setPickerOpen((open) => !open)}
                  className="relative h-8 w-full overflow-hidden rounded-lg border border-black/10 shadow-inner focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary/50 focus-visible:ring-offset-2"
                  style={{
                    backgroundImage: 'linear-gradient(to right, #f00 0%, #ff0 16%, #0f0 33%, #0ff 50%, #00f 66%, #f0f 83%, #f00 100%)',
                  }}
                >
                  <span className="absolute inset-y-1 end-1 w-7 rounded-md border-2 border-white shadow-[0_1px_4px_rgba(0,0,0,.45)]" style={{ backgroundColor: color }} />
                </button>
                {pickerOpen && (
                  <div
                    role="application"
                    aria-label={tColors('curated_palette')}
                    className="relative h-28 w-full cursor-crosshair overflow-hidden rounded-xl border border-black/10 shadow-inner"
                    style={{
                      backgroundImage: 'linear-gradient(to bottom, transparent 0%, rgba(0,0,0,.72) 100%), linear-gradient(to right, #f00 0%, #ff0 16%, #0f0 33%, #0ff 50%, #00f 66%, #f0f 83%, #f00 100%)',
                    }}
                    onClick={(event) => {
                      const rect = event.currentTarget.getBoundingClientRect()
                      const x = (event.clientX - rect.left) / rect.width
                      const y = (event.clientY - rect.top) / rect.height
                      setPickerPosition({ x, y })
                      setColor(spectrumColor(event.clientX - rect.left, event.clientY - rect.top, rect.width, rect.height))
                      setPickerOpen(false)
                    }}
                  >
                    <span
                      aria-hidden="true"
                      className="pointer-events-none absolute h-5 w-5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white shadow-[0_1px_4px_rgba(0,0,0,.55)]"
                      style={{ left: `${pickerPosition.x * 100}%`, top: `${pickerPosition.y * 100}%`, backgroundColor: color }}
                    />
                  </div>
                )}
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
