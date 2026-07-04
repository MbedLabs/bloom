import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  buildBudRunUrl,
  getBudApiBaseUrl,
  getBudAppBaseUrl,
  normalizeBudAppBaseUrl,
} from '../lib/budLinks'

describe('Bud link helpers', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('normalizes app URLs for browser navigation', () => {
    expect(normalizeBudAppBaseUrl('https://bud.embedlabs.net/api')).toBe('https://bud.embedlabs.net')
    expect(normalizeBudAppBaseUrl('https://bud.embedlabs.net/api/')).toBe('https://bud.embedlabs.net')
    expect(normalizeBudAppBaseUrl('https://bud.embedlabs.net/')).toBe('https://bud.embedlabs.net')
  })

  it('builds a direct Bud run detail URL', () => {
    expect(buildBudRunUrl(42, 'https://bud.embedlabs.net/api')).toBe('https://bud.embedlabs.net/runs/42')
  })

  it('uses runtime config before build-time fallback', () => {
    vi.stubGlobal('window', { runtimeConfig: { BUD_APP_URL: 'https://runtime-bud.example/api' } })

    expect(getBudAppBaseUrl()).toBe('https://runtime-bud.example')
    expect(getBudApiBaseUrl()).toBe('https://runtime-bud.example')
  })
})
