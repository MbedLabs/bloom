// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { formatDateTime } from './date-utils'

describe('Bloom shows times to the minute', () => {
  beforeEach(() => {
    localStorage.setItem('bloom-timezone', 'UTC')
  })

  afterEach(() => {
    localStorage.removeItem('bloom-timezone')
  })

  it('stops at the minute', () => {
    const shown = formatDateTime('2026-09-27T12:34:56Z')
    expect(shown).toContain('12:34')
    expect(shown).not.toContain('56')
  })
})
