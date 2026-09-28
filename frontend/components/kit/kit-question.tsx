import { cn } from '@/lib/utils'

export function KitQuestion({
  before,
  emphasis,
  after,
  helper,
  align = 'start',
}: {
  before?: string
  emphasis: string
  after?: string
  helper?: string
  
  align?: 'start' | 'center'
}) {
  const centered = align === 'center'
  return (
    <div className={cn('space-y-2', centered && 'text-center')}>
      <h2
        className={cn(
          'font-display text-[31px] leading-[1.12] text-foreground',
          centered ? 'mx-auto max-w-none' : 'max-w-[20ch]',
        )}
      >
        {before}
        <em className="text-brand">{emphasis}</em>
        {after}
      </h2>
      {helper && (
        <p
          className={cn(
            'max-w-[56ch] text-[14px] text-muted-foreground',
            centered && 'mx-auto',
          )}
        >
          {helper}
        </p>
      )}
    </div>
  )
}