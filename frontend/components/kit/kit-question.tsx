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
          'font-el-messiri text-[29px] font-bold leading-[1.2] text-foreground sm:text-[31px]',
          centered ? 'mx-auto max-w-none' : 'max-w-[20ch]',
        )}
      >
        {before}
        <em className="not-italic text-brand">{emphasis}</em>
        {after}
      </h2>
      {helper && (
        <p
          className={cn(
            'font-tajawal max-w-[56ch] text-[14px] text-muted-foreground',
            centered && 'mx-auto',
          )}
        >
          {helper}
        </p>
      )}
    </div>
  )
}