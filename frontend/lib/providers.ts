import type { Provider } from '@/types'

export const PROVIDER_LABELS: Record<Provider, string> = {
  openai: 'OpenAI',
  gemini: 'Gemini',
}

export function providerLabel(provider: Provider): string {
  return PROVIDER_LABELS[provider] ?? provider
}
