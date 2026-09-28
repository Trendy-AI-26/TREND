'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useTranslations } from 'next-intl'
import { createClient } from '@/lib/supabase/client'
import { AuthShell } from '@/components/auth/auth-shell'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export default function ResetPasswordPage() {
  const router = useRouter()
  const t = useTranslations('auth')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const validPassword = password.length >= 8 && /\d/.test(password) && /[A-Z]/.test(password)
  const passwordsMatch = password === confirmation && confirmation.length > 0

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)

    if (!validPassword) {
      setError(t('passwordRequirementsError'))
      return
    }
    if (!passwordsMatch) {
      setError(t('passwordMatchError'))
      return
    }

    setLoading(true)
    const { error: updateError } = await createClient().auth.updateUser({ password })
    setLoading(false)

    if (updateError) {
      setError(updateError.message)
      return
    }

    router.push('/login?password-reset=success')
    router.refresh()
  }

  return (
    <AuthShell
      hero={t('resetHero')}
      subcopy={t('newPasswordDescription')}
      features={[]}
    >
      <Card className="shadow-sm">
        <CardHeader>
          <CardTitle className="text-[22px] font-semibold tracking-tight">{t('newPasswordTitle')}</CardTitle>
          <CardDescription>{t('newPasswordDescription')}</CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            {error && <div role="alert" className="rounded-md bg-destructive/10 p-3 text-[13px] text-destructive">{error}</div>}
            <div className="space-y-2">
              <Label htmlFor="new-password">{t('newPasswordLabel')}</Label>
              <Input id="new-password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required autoComplete="new-password" />
              <p className="text-[12px] text-muted-foreground">{t('passwordRequirements')}</p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirm-password">{t('confirmPasswordLabel')}</Label>
              <Input id="confirm-password" type="password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} required autoComplete="new-password" />
            </div>
            <Button type="submit" size="lg" className="w-full" disabled={loading || !validPassword || !passwordsMatch}>
              {loading ? t('updatingPassword') : t('resetPassword')}
            </Button>
            <p className="text-center text-[12px] text-muted-foreground">
              <Link href="/login" className="font-medium text-brand underline underline-offset-2">{t('backToLogin')}</Link>
            </p>
          </CardContent>
        </form>
      </Card>
    </AuthShell>
  )
}
