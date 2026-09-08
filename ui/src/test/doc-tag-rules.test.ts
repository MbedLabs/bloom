import { describe, expect, it } from 'vitest'

import { isDocLinkRoleAllowed, isDocTagHostType, isDocTagTargetAllowed } from '../types/doc'

describe('isDocTagHostType', () => {
  it('accepts the kinds whose body is prose', () => {
    for (const kind of ['REQ', 'DES', 'RSK', 'CHG', 'CPT', 'SPEC', 'PRT', 'RPT', 'STD']) {
      expect(isDocTagHostType(kind), kind).toBe(true)
    }
  })

  it('refuses containers and kinds with no body', () => {
    for (const kind of ['TC', 'TS', 'CMP', 'DEF']) {
      expect(isDocTagHostType(kind), kind).toBe(false)
    }
  })
})

describe('isDocTagTargetAllowed', () => {
  it('permits pairs the typed link matrix has no row for', () => {
    expect(isDocLinkRoleAllowed('SPEC', 'REQ', 'references')).toBe(false)
    expect(isDocTagTargetAllowed('SPEC', 'REQ')).toBe(true)

    expect(isDocLinkRoleAllowed('REQ', 'REQ', 'references')).toBe(false)
    expect(isDocTagTargetAllowed('REQ', 'REQ')).toBe(true)

    expect(isDocLinkRoleAllowed('REQ', 'DES', 'references')).toBe(false)
    expect(isDocTagTargetAllowed('REQ', 'DES')).toBe(true)
  })

  it('permits containers as targets but never as hosts', () => {
    expect(isDocTagTargetAllowed('REQ', 'CMP')).toBe(true)
    expect(isDocTagTargetAllowed('CMP', 'REQ')).toBe(false)
    expect(isDocTagTargetAllowed('TS', 'REQ')).toBe(false)
    expect(isDocTagTargetAllowed('TC', 'REQ')).toBe(false)
  })

  it('refuses unknown kinds on either side', () => {
    expect(isDocTagTargetAllowed('REQ', 'NOPE')).toBe(false)
    expect(isDocTagTargetAllowed('NOPE', 'REQ')).toBe(false)
  })
})
