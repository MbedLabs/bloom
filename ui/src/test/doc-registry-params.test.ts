import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import {
  DEFAULT_SORT_DIR,
  DEFAULT_SORT_FIELD,
  clearRegistrySortSession,
  docRegistryBackUrl,
  docRegistryListLabel,
  docRegistryListUrl,
  isRegistrySortDir,
  isRegistrySortField,
  readStoredSort,
  registrySortScope,
  sortSearchString,
  syncRegistryProjectContext,
  writeStoredSort,
} from '../lib/docRegistryParams'

beforeEach(() => {
  syncRegistryProjectContext(null)
})

afterEach(() => {
  syncRegistryProjectContext(null)
})

describe('defaults', () => {
  it('default sort field is updated_at', () => {
    expect(DEFAULT_SORT_FIELD).toBe('updated_at')
  })

  it('default sort direction is desc (most recent first)', () => {
    expect(DEFAULT_SORT_DIR).toBe('desc')
  })
})

describe('registrySortScope', () => {
  it('returns all for no type filters', () => {
    expect(registrySortScope([])).toBe('all')
  })

  it('returns the type for a single filter', () => {
    expect(registrySortScope(['REQ'])).toBe('REQ')
    expect(registrySortScope(['DEF'])).toBe('DEF')
  })

  it('returns null for multi-type filter (no session)', () => {
    expect(registrySortScope(['REQ', 'DEF'])).toBeNull()
  })
})

describe('isRegistrySortField', () => {
  it('accepts known fields', () => {
    expect(isRegistrySortField('doc_id')).toBe(true)
    expect(isRegistrySortField('updated_at')).toBe(true)
    expect(isRegistrySortField('title')).toBe(true)
  })

  it('rejects unknown fields', () => {
    expect(isRegistrySortField('foo')).toBe(false)
    expect(isRegistrySortField(null)).toBe(false)
    expect(isRegistrySortField(undefined)).toBe(false)
  })
})

describe('isRegistrySortDir', () => {
  it('accepts asc and desc', () => {
    expect(isRegistrySortDir('asc')).toBe(true)
    expect(isRegistrySortDir('desc')).toBe(true)
  })

  it('rejects other strings', () => {
    expect(isRegistrySortDir('DESC')).toBe(false)
    expect(isRegistrySortDir(null)).toBe(false)
  })
})

describe('session read/write (per type)', () => {
  it('returns null when nothing stored', () => {
    syncRegistryProjectContext('PRJ')
    expect(readStoredSort('PRJ', 'REQ')).toBeNull()
  })

  it('round-trips per scope', () => {
    syncRegistryProjectContext('PRJ')
    writeStoredSort('PRJ', 'REQ', { field: 'doc_id', dir: 'asc' })
    expect(readStoredSort('PRJ', 'REQ')).toEqual({ field: 'doc_id', dir: 'asc' })
  })

  it('REQ and DEF are independent in one project', () => {
    syncRegistryProjectContext('PRJ')
    writeStoredSort('PRJ', 'REQ', { field: 'doc_id', dir: 'asc' })
    writeStoredSort('PRJ', 'DEF', { field: 'title', dir: 'desc' })
    expect(readStoredSort('PRJ', 'REQ')).toEqual({ field: 'doc_id', dir: 'asc' })
    expect(readStoredSort('PRJ', 'DEF')).toEqual({ field: 'title', dir: 'desc' })
  })

  it('all bucket is independent from REQ', () => {
    syncRegistryProjectContext('PRJ')
    writeStoredSort('PRJ', 'all', { field: 'created_at', dir: 'asc' })
    writeStoredSort('PRJ', 'REQ', { field: 'doc_id', dir: 'desc' })
    expect(readStoredSort('PRJ', 'all')).toEqual({ field: 'created_at', dir: 'asc' })
    expect(readStoredSort('PRJ', 'REQ')).toEqual({ field: 'doc_id', dir: 'desc' })
  })

  it('different projects are independent', () => {
    syncRegistryProjectContext('PRJ')
    writeStoredSort('PRJ', 'REQ', { field: 'doc_id', dir: 'asc' })
    syncRegistryProjectContext('ECU')
    writeStoredSort('ECU', 'REQ', { field: 'title', dir: 'desc' })
    expect(readStoredSort('ECU', 'REQ')).toEqual({ field: 'title', dir: 'desc' })
    syncRegistryProjectContext('PRJ')
    expect(readStoredSort('PRJ', 'REQ')).toBeNull()
  })
})

describe('reset on project switch / leave', () => {
  it('switching project clears previous project session', () => {
    syncRegistryProjectContext('PRJ')
    writeStoredSort('PRJ', 'REQ', { field: 'doc_id', dir: 'asc' })
    syncRegistryProjectContext('ECU')
    expect(readStoredSort('PRJ', 'REQ')).toBeNull()
    syncRegistryProjectContext('PRJ')
    expect(readStoredSort('PRJ', 'REQ')).toBeNull()
  })

  it('leaving project (null context) clears that project session', () => {
    syncRegistryProjectContext('PRJ')
    writeStoredSort('PRJ', 'REQ', { field: 'doc_id', dir: 'asc' })
    syncRegistryProjectContext(null)
    syncRegistryProjectContext('PRJ')
    expect(readStoredSort('PRJ', 'REQ')).toBeNull()
  })

  it('clearRegistrySortSession removes all scopes for a prefix', () => {
    syncRegistryProjectContext('PRJ')
    writeStoredSort('PRJ', 'REQ', { field: 'doc_id', dir: 'asc' })
    writeStoredSort('PRJ', 'DEF', { field: 'title', dir: 'asc' })
    clearRegistrySortSession('PRJ')
    expect(readStoredSort('PRJ', 'REQ')).toBeNull()
    expect(readStoredSort('PRJ', 'DEF')).toBeNull()
  })
})

describe('sortSearchString', () => {
  it('returns empty for defaults', () => {
    expect(sortSearchString({ field: 'updated_at', dir: 'desc' })).toBe('')
  })

  it('includes sort when field differs from default', () => {
    expect(sortSearchString({ field: 'doc_id', dir: 'desc' })).toBe('sort=doc_id')
  })

  it('includes dir when it differs from default', () => {
    expect(sortSearchString({ field: 'updated_at', dir: 'asc' })).toBe('dir=asc')
  })

  it('includes both when both differ', () => {
    const qs = sortSearchString({ field: 'title', dir: 'asc' })
    expect(qs).toContain('sort=title')
    expect(qs).toContain('dir=asc')
  })
})

describe('docRegistryListUrl', () => {
  it('returns base docs URL with no stored sort', () => {
    syncRegistryProjectContext('PRJ')
    expect(docRegistryListUrl('PRJ')).toBe('/projects/PRJ/docs')
  })

  it('returns typed URL with no stored sort', () => {
    syncRegistryProjectContext('PRJ')
    expect(docRegistryListUrl('PRJ', 'REQ')).toBe('/projects/PRJ/docs?type=requirements')
  })

  it('includes remembered sort only for active project', () => {
    syncRegistryProjectContext('PRJ')
    writeStoredSort('PRJ', 'REQ', { field: 'doc_id', dir: 'asc' })
    const url = docRegistryListUrl('PRJ', 'REQ')
    expect(url).toContain('type=requirements')
    expect(url).toContain('sort=doc_id')
    expect(url).toContain('dir=asc')
  })

  it('does not apply another project sort when viewing a different active project', () => {
    syncRegistryProjectContext('PRJ')
    writeStoredSort('PRJ', 'REQ', { field: 'doc_id', dir: 'asc' })
    syncRegistryProjectContext('ECU')
    expect(docRegistryListUrl('PRJ', 'REQ')).toBe('/projects/PRJ/docs?type=requirements')
  })

  it('omits default sort params from URL', () => {
    syncRegistryProjectContext('PRJ')
    writeStoredSort('PRJ', 'REQ', { field: 'updated_at', dir: 'desc' })
    expect(docRegistryListUrl('PRJ', 'REQ')).toBe('/projects/PRJ/docs?type=requirements')
  })
})

describe('docRegistryListLabel', () => {
  it('returns Documents when no doc type', () => {
    expect(docRegistryListLabel()).toBe('Documents')
    expect(docRegistryListLabel(undefined)).toBe('Documents')
  })

  it('returns plural list title per DocType', () => {
    expect(docRegistryListLabel('REQ')).toBe('Requirements')
    expect(docRegistryListLabel('TC')).toBe('Test Cases')
    expect(docRegistryListLabel('CMP')).toBe('Test Campaigns')
    expect(docRegistryListLabel('TS')).toBe('Test Suites')
  })
})

describe('docRegistryBackUrl', () => {
  it('uses returnTo when provided', () => {
    expect(docRegistryBackUrl('PRJ', 'REQ', '/projects/PRJ/docs?type=requirements&sort=doc_id')).toBe(
      '/projects/PRJ/docs?type=requirements&sort=doc_id',
    )
  })

  it('ignores whitespace-only returnTo', () => {
    syncRegistryProjectContext('PRJ')
    expect(docRegistryBackUrl('PRJ', 'REQ', '   ')).toBe('/projects/PRJ/docs?type=requirements')
  })

  it('falls back to sort-aware docRegistryListUrl', () => {
    syncRegistryProjectContext('PRJ')
    writeStoredSort('PRJ', 'REQ', { field: 'doc_id', dir: 'asc' })
    expect(docRegistryBackUrl('PRJ', 'REQ')).toContain('type=requirements')
    expect(docRegistryBackUrl('PRJ', 'REQ')).toContain('sort=doc_id')
  })
})
