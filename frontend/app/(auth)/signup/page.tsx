'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useTranslations } from 'next-intl'
import { ImagePlus, KeyRound, Palette } from 'lucide-react'
import { createClient } from '@/lib/supabase/client'
import { AuthShell } from '@/components/auth/auth-shell'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'

export default function SignUpPage() {
  const router = useRouter()
  const t = useTranslations('auth')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [confirmationSent, setConfirmationSent] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)

    const supabase = createClient()
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
    })

    setLoading(false)

    if (error) {
      if (error.message.includes('User already registered')) {
        setError('An account with this email already exists. Please log in instead.')
      } else {
        setError(error.message)
      }
      return
    }

    if (!data.session) {
      setConfirmationSent(true)
      return
    }

    router.push('/brands')
    router.refresh()
  }

  const hero = (
    <>
      {t('signupHeroBefore')} <em className="text-brand-accent">{t('signupHeroAccent')}</em>
    </>
  )

  return (
    <AuthShell
      hero={hero}
      subcopy={t('signupSubcopy')}
      features={[
        { icon: Palette, label: t('signupFeatureInterview') },
        { icon: KeyRound, label: t('featureKeys') },
        { icon: ImagePlus, label: t('signupFeaturePreset') },
      ]}
    >
      <Card className="shadow-sm">
        {confirmationSent ? (
          <>
            <CardHeader>
              <CardTitle className="text-[22px] font-semibold tracking-tight">{t('checkEmail')}</CardTitle>
              <CardDescription>
                {t('confirmationSent')} <strong>{email}</strong>. {t('activateAccount')}
              </CardDescription>
            </CardHeader>
            <CardFooter>
              <Link href="/login" className="w-full text-center text-sm font-medium text-brand underline underline-offset-2">
                {t('backToLogin')}
              </Link>
            </CardFooter>
          </>
        ) : (
          <>
        <CardHeader>
          <CardTitle className="text-[22px] font-semibold tracking-tight">{t('createAccount')}</CardTitle>
          <CardDescription>{t('signupDescription')}</CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            {error && (
              <div className="rounded-md bg-[color-mix(in_srgb,hsl(var(--destructive))_8%,white)] p-3 text-[13px] text-destructive">
                {error}
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="email">{t('email')}</Label>
              <Input
                id="email"
                type="email"
                placeholder={t('emailPlaceholder')}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">{t('password')}</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
                autoComplete="new-password"
              />
              <p className="text-[12px] text-muted-foreground">{t('passwordHint')}</p>
            </div>
          </CardContent>
          <CardFooter className="flex flex-col gap-4">
            <Button type="submit" size="lg" className="w-full" disabled={loading}>
              {loading ? t('creatingAccount') : t('signUp')}
            </Button>
            <p className="text-center text-[12px] text-muted-foreground">
              {t('hasAccount')}{' '}
              <Link href="/login" className="font-medium text-brand underline underline-offset-[2px]">
                {t('loginTitle')}
              </Link>
            </p>
          </CardFooter>
        </form>
          </>
        )}
      </Card>
    </AuthShell>
  )
}
