import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import {
  DEFAULT_SORT_DIR,
  DEFAULT_SORT_FIELD,
  docRegistryListUrl,
  isRegistrySortDir,
  isRegistrySortField,
  readStoredSort,
  sortSearchString,
  writeStoredSort,
} from '../lib/docRegistryParams'

const store = new Map<string, string>()
const fakeStorage = {
  getItem: (key: string) => store.get(key) ?? null,
  setItem: (key: string, val: string) => { store.set(key, val) },
  removeItem: (key: string) => { store.delete(key) },
  clear: () => { store.clear() },
  get length() { return store.size },
  key: () => null as string | null,
}

beforeEach(() => {
  store.clear()
  Object.defineProperty(globalThis, 'localStorage', { value: fakeStorage, writable: true, configurable: true })
})

afterEach(() => {
  store.clear()
})

describe('defaults', () => {
  it('default sort field is updated_at', () => {
    expect(DEFAULT_SORT_FIELD).toBe('updated_at')
  })

  it('default sort direction is desc (most recent first)', () => {
    expect(DEFAULT_SORT_DIR).toBe('desc')
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

describe('readStoredSort / writeStoredSort', () => {
  it('returns null when nothing stored', () => {
    expect(readStoredSort('VCU')).toBeNull()
  })

  it('round-trips a stored sort', () => {
    writeStoredSort('VCU', { field: 'doc_id', dir: 'asc' })
    expect(readStoredSort('VCU')).toEqual({ field: 'doc_id', dir: 'asc' })
  })

  it('project-scoped: different projects are independent', () => {
    writeStoredSort('VCU', { field: 'doc_id', dir: 'asc' })
    writeStoredSort('ECU', { field: 'title', dir: 'desc' })
    expect(readStoredSort('VCU')).toEqual({ field: 'doc_id', dir: 'asc' })
    expect(readStoredSort('ECU')).toEqual({ field: 'title', dir: 'desc' })
  })

  it('project switch: new project has no memory (returns null)', () => {
    writeStoredSort('VCU', { field: 'doc_id', dir: 'asc' })
    expect(readStoredSort('NEW')).toBeNull()
  })

  it('ignores corrupt localStorage data', () => {
    store.set('bloom:docs-registry-sort:BAD', '{invalid json')
    expect(readStoredSort('BAD')).toBeNull()
  })

  it('ignores stored data with invalid field/dir', () => {
    store.set('bloom:docs-registry-sort:BAD2', '{"field":"bogus","dir":"up"}')
    expect(readStoredSort('BAD2')).toBeNull()
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
    expect(docRegistryListUrl('VCU')).toBe('/projects/VCU/docs')
  })

  it('returns typed URL with no stored sort', () => {
    expect(docRegistryListUrl('VCU', 'REQ')).toBe('/projects/VCU/docs?type=requirements')
  })

  it('includes remembered sort in the URL', () => {
    writeStoredSort('VCU', { field: 'doc_id', dir: 'asc' })
    const url = docRegistryListUrl('VCU', 'REQ')
    expect(url).toContain('type=requirements')
    expect(url).toContain('sort=doc_id')
    expect(url).toContain('dir=asc')
  })

  it('omits default sort params from URL', () => {
    writeStoredSort('VCU', { field: 'updated_at', dir: 'desc' })
    expect(docRegistryListUrl('VCU', 'REQ')).toBe('/projects/VCU/docs?type=requirements')
  })

  it('uses project-scoped sort, not another project', () => {
    writeStoredSort('VCU', { field: 'doc_id', dir: 'asc' })
    expect(docRegistryListUrl('ECU', 'REQ')).toBe('/projects/ECU/docs?type=requirements')
  })
})
