type RuntimeWindow = Window & {
  runtimeConfig?: {
    BUD_APP_URL?: string
  }
}

function rawBudUrl(): string | null {
  const runtimeUrl = (window as RuntimeWindow).runtimeConfig?.BUD_APP_URL
  const buildTimeUrl = import.meta.env.VITE_TESTSTATION_APP_URL
  return runtimeUrl || buildTimeUrl || null
}

export function normalizeBudAppBaseUrl(value: string): string {
  return value.replace(/\/api\/?$/, '').replace(/\/$/, '')
}

export function getBudAppBaseUrl(): string | null {
  const rawUrl = rawBudUrl()
  return rawUrl?.trim() ? normalizeBudAppBaseUrl(rawUrl) : null
}

export function buildBudRunUrl(
  runId: number | string,
  baseUrl: string | null = getBudAppBaseUrl(),
): string | null {
  if (!baseUrl?.trim()) return null
  return `${normalizeBudAppBaseUrl(baseUrl)}/runs/${runId}`
}
