const DEFAULT_BUD_URL = 'http://localhost:3000'

type RuntimeWindow = Window & {
  runtimeConfig?: {
    BUD_APP_URL?: string
  }
}

function rawBudUrl(): string {
  const runtimeUrl = (window as RuntimeWindow).runtimeConfig?.BUD_APP_URL
  const buildTimeUrl = import.meta.env.VITE_TESTSTATION_APP_URL
  return runtimeUrl || buildTimeUrl || DEFAULT_BUD_URL
}

export function normalizeBudAppBaseUrl(value: string): string {
  return value.replace(/\/api\/?$/, '').replace(/\/$/, '')
}

export function getBudAppBaseUrl(): string {
  return normalizeBudAppBaseUrl(rawBudUrl())
}

export function buildBudRunUrl(runId: number | string, baseUrl = getBudAppBaseUrl()): string {
  return `${normalizeBudAppBaseUrl(baseUrl)}/runs/${runId}`
}
