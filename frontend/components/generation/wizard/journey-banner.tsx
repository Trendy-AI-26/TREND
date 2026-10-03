'use client'

import { Fragment } from 'react'
import { useTranslations } from 'next-intl'
import { ChevronLeft, MessageSquareText, Sparkles, Upload } from 'lucide-react'

export function JourneyBanner() {
  const t = useTranslations('components.generation.wizard')

  const items = [
    { icon: MessageSquareText, title: t('journey_answer_title'), text: t('journey_answer_text') },
    { icon: Sparkles, title: t('journey_design_title'), text: t('journey_design_text') },
    { icon: Upload, title: t('journey_publish_title'), text: t('journey_publish_text') },
  ]

  return (
    <div className="rounded-[12px] border border-brand-accent/30 bg-brand-cream px-3 py-4 sm:px-5">
      <div className="flex items-start">
        {items.map((item, index) => {
          const Icon = item.icon
          return (
            <Fragment key={item.title}>
              <div className="flex flex-1 flex-col items-center text-center">
                <span className="flex h-9 w-9 items-center justify-center rounded-[10px] bg-brand-primary/10 text-brand-primary">
                  <Icon className="h-[18px] w-[18px]" />
                </span>
                <p className="mt-1.5 text-[14px] font-extrabold leading-[21px] text-brand-primary">
                  {item.title}
                </p>
                <p className="mt-1 max-w-[193px] text-[11.5px] leading-[17px] text-brand-headline/60">
                  {item.text}
                </p>
              </div>

              {index < items.length - 1 && (
                <div
                  aria-hidden="true"
                  className="mt-[18px] hidden w-10 shrink-0 items-center text-brand-accent/60 sm:flex"
                >
                  <span className="h-0 flex-1 border-t border-dashed border-current" />
                  <ChevronLeft className="-ms-1 h-3 w-3 ltr:rotate-180" />
                </div>
              )}
            </Fragment>
          )
        })}
      </div>
    </div>
  )
}