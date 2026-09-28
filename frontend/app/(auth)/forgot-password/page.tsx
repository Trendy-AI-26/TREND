'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Mail } from 'lucide-react'
import { useTranslations } from 'next-intl'
import { createClient } from '@/lib/supabase/client'
import { AuthShell } from '@/components/auth/auth-shell'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export default function ForgotPasswordPage() {
  const t = useTranslations('auth')
  const [email, setEmail] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [sent, setSent] = useState(false)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setLoading(true)

    const redirectTo = `${window.location.origin}/auth/confirm?next=/reset-password`
    const { error: resetError } = await createClient().auth.resetPasswordForEmail(email, { redirectTo })

    setLoading(false)
    if (resetError) {
      setError(resetError.message)
      return
    }

    setSent(true)
  }

  return (
    <AuthShell
      hero={t('resetHero')}
      subcopy={t('resetDescription')}
      features={[]}
    >
      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle className="text-[22px] font-semibold tracking-tight">
            {sent ? t('resetEmailSentTitle') : t('forgotPassword')}
          </CardTitle>
          <CardDescription>
            {sent ? `${t('resetEmailSentDescription')} ${email}` : t('resetDescription')}
          </CardDescription>
        </CardHeader>
        {sent ? (
          <CardContent>
            <Link href="/login" className="text-sm font-medium text-brand underline underline-offset-2">
              {t('backToLogin')}
            </Link>
          </CardContent>
        ) : (
          <form onSubmit={handleSubmit}>
            <CardContent className="space-y-4">
              {error && <div role="alert" className="rounded-md bg-destructive/10 p-3 text-[13px] text-destructive">{error}</div>}
              <div className="space-y-2">
                <Label htmlFor="reset-email">{t('email')}</Label>
                <div className="relative">
                  <Input
                    id="reset-email"
                    type="email"
                    placeholder={t('emailPlaceholder')}
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    required
                    autoComplete="email"
                    className="pr-10"
                  />
                  <Mail className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                </div>
              </div>
              <Button type="submit" size="lg" className="w-full" disabled={loading}>
                {loading ? t('sendingReset') : t('sendReset')}
              </Button>
              <p className="text-center text-[12px] text-muted-foreground">
                <Link href="/login" className="font-medium text-brand underline underline-offset-2">{t('backToLogin')}</Link>
              </p>
            </CardContent>
          </form>
        )}
      </Card>
    </AuthShell>
  )
}
