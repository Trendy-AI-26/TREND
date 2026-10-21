'use client'

import { useState } from 'react'
import { useTranslations } from 'next-intl'
import { Download } from 'lucide-react'
import { toast } from 'sonner'
import { errorMessage } from '@/lib/errors'
import { downloadImageFile } from '@/lib/download'
import { Button } from '@/components/ui/button'

interface HistoryDownloadButtonProps {
  imageUrl: string | null
  downloadFilename: string | null
  disabled?: boolean
}

export function HistoryDownloadButton({
  imageUrl,
  downloadFilename,
  disabled: forceDisabled = false,
}: HistoryDownloadButtonProps) {
  const te = useTranslations('errors')
  const [downloading, setDownloading] = useState(false)
  const disabled = forceDisabled || !imageUrl || !downloadFilename

  async function handleDownload() {
    if (disabled || !imageUrl || !downloadFilename) return
    setDownloading(true)
    try {
      await downloadImageFile(imageUrl, downloadFilename)
    } catch (err) {
      toast.error(errorMessage(err, te))
    } finally {
      setDownloading(false)
    }
  }

  return (
    <Button
      type="button"
      onClick={handleDownload}
      disabled={disabled || downloading}
    >
      <Download className="h-4 w-4" />
      {downloading ? 'Downloading…' : 'Download'}
    </Button>
  )
}
