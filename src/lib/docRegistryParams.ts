import { DOC_TYPE_SLUGS, type DocType } from '../types/doc'

export type RegistrySortField =
  | 'updated_at'
  | 'created_at'
  | 'doc_id'
  | 'doc_type'
  | 'status'
  | 'title'
  | 'priority'
  | 'reviewer'

export type RegistrySortDir = 'asc' | 'desc'

export const DEFAULT_SORT_FIELD: RegistrySortField = 'updated_at'
export const DEFAULT_SORT_DIR: RegistrySortDir = 'desc'

const SORT_FIELDS = new Set<string>([
  'updated_at', 'created_at', 'doc_id', 'doc_type',
  'status', 'title', 'priority', 'reviewer',
])

const STORAGE_PREFIX = 'bloom:docs-registry-sort:'

function storageKey(prefix: string): string {
  return `${STORAGE_PREFIX}${prefix}`
}

export function isRegistrySortField(v: string | null | undefined): v is RegistrySortField {
  return typeof v === 'string' && SORT_FIELDS.has(v)
}

export function isRegistrySortDir(v: string | null | undefined): v is RegistrySortDir {
  return v === 'asc' || v === 'desc'
}

export interface StoredSort {
  field: RegistrySortField
  dir: RegistrySortDir
}

export function readStoredSort(prefix: string): StoredSort | null {
  try {
    const raw = localStorage.getItem(storageKey(prefix))
    if (!raw) return null
    const parsed = JSON.parse(raw) as { field?: string; dir?: string }
    if (isRegistrySortField(parsed.field) && isRegistrySortDir(parsed.dir)) {
      return { field: parsed.field, dir: parsed.dir }
    }
    return null
  } catch {
    return null
  }
}

export function writeStoredSort(prefix: string, sort: StoredSort): void {
  try {
    localStorage.setItem(storageKey(prefix), JSON.stringify(sort))
  } catch { /* quota exceeded — silently ignore */ }
}

export function sortSearchString(sort: StoredSort): string {
  const params = new URLSearchParams()
  if (sort.field !== DEFAULT_SORT_FIELD) params.set('sort', sort.field)
  if (sort.dir !== DEFAULT_SORT_DIR) params.set('dir', sort.dir)
  return params.toString()
}

export function docRegistryListUrl(
  prefix: string,
  docType?: DocType,
): string {
  const stored = readStoredSort(prefix)
  const slug = docType ? DOC_TYPE_SLUGS[docType] : undefined
  const params = new URLSearchParams()
  if (slug) params.set('type', slug)
  if (stored) {
    if (stored.field !== DEFAULT_SORT_FIELD) params.set('sort', stored.field)
    if (stored.dir !== DEFAULT_SORT_DIR) params.set('dir', stored.dir)
  }
  const qs = params.toString()
  return `/projects/${prefix}/docs${qs ? `?${qs}` : ''}`
}
