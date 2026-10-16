import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  buildBudRunUrl,
  getBudAppBaseUrl,
  normalizeBudAppBaseUrl,
} from '../lib/budLinks'

describe('Bud link helpers', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('normalizes app URLs for browser navigation', () => {
    expect(normalizeBudAppBaseUrl('https://bud.example.com/api')).toBe('https://bud.example.com')
    expect(normalizeBudAppBaseUrl('https://bud.example.com/api/')).toBe('https://bud.example.com')
    expect(normalizeBudAppBaseUrl('https://bud.example.com/')).toBe('https://bud.example.com')
  })

  it('builds a direct Bud run detail URL', () => {
    expect(buildBudRunUrl(42, 'https://bud.example.com/api')).toBe('https://bud.example.com/runs/42')
  })

  it('uses runtime config before build-time fallback', () => {
    vi.stubGlobal('window', { runtimeConfig: { BUD_APP_URL: 'https://runtime-bud.example/api' } })

    expect(getBudAppBaseUrl()).toBe('https://runtime-bud.example')
  })

  it('does not invent a Bud URL when Bloom is standalone', () => {
    vi.stubGlobal('window', { runtimeConfig: {} })

    expect(getBudAppBaseUrl()).toBeNull()
    expect(buildBudRunUrl(42)).toBeNull()
  })
})
