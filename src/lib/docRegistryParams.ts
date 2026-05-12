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

/** Single-doc-type filter, or unfiltered "all documents" list. Multi-type selection = no session persistence. */
export type RegistrySortScope = DocType | 'all'

const SORT_FIELDS = new Set<string>([
  'updated_at', 'created_at', 'doc_id', 'doc_type',
  'status', 'title', 'priority', 'reviewer',
])

const LEGACY_STORAGE_PREFIX = 'bloom:docs-registry-sort:'

const sessionSort = new Map<string, StoredSort>()

/** Project prefix for routes under `/projects/:prefix/*`; null on dashboard and global routes. */
let activeRegistryPrefix: string | null = null

function sessionKey(prefix: string, scope: RegistrySortScope): string {
  return `${prefix}:${scope}`
}

function removeLegacyLocalStorage(prefix: string): void {
  try {
    localStorage.removeItem(`${LEGACY_STORAGE_PREFIX}${prefix}`)
  } catch { /* ignore */ }
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

export function registrySortScope(typeFilters: DocType[]): RegistrySortScope | null {
  if (typeFilters.length === 0) return 'all'
  if (typeFilters.length === 1) return typeFilters[0]
  return null
}

/** Call from Layout on route change. Clears session for the previous project when leaving or switching projects. */
export function syncRegistryProjectContext(projectPrefix: string | null): void {
  if (projectPrefix === activeRegistryPrefix) return
  if (activeRegistryPrefix) {
    clearRegistrySortSession(activeRegistryPrefix)
  }
  activeRegistryPrefix = projectPrefix
}

export function getActiveRegistryPrefix(): string | null {
  return activeRegistryPrefix
}

export function clearRegistrySortSession(prefix: string): void {
  removeLegacyLocalStorage(prefix)
  const prefixWithColon = `${prefix}:`
  for (const key of sessionSort.keys()) {
    if (key.startsWith(prefixWithColon)) {
      sessionSort.delete(key)
    }
  }
}

export function readStoredSort(prefix: string, scope: RegistrySortScope): StoredSort | null {
  return sessionSort.get(sessionKey(prefix, scope)) ?? null
}

export function writeStoredSort(prefix: string, scope: RegistrySortScope, sort: StoredSort): void {
  sessionSort.set(sessionKey(prefix, scope), sort)
}

export function sortSearchString(sort: StoredSort): string {
  const params = new URLSearchParams()
  if (sort.field !== DEFAULT_SORT_FIELD) params.set('sort', sort.field)
  if (sort.dir !== DEFAULT_SORT_DIR) params.set('dir', sort.dir)
  return params.toString()
}

/** Plural labels for registry list / shell back labeling (aligned with Layout breadcrumbs + Documents titles). */
const TYPE_LIST_LABELS: Record<DocType, string> = {
  REQ: 'Requirements',
  SPEC: 'Specifications',
  TC: 'Test Cases',
  DES: 'Design Items',
  RSK: 'Risks',
  CHG: 'Changes',
  TCO: 'Test Concepts',
  DEF: 'Defects',
  CMP: 'Campaigns',
  TS: 'Test Suites',
  PROT: 'Protocols',
  RPT: 'Reports',
  STD: 'Standards',
}

export function docRegistryListLabel(docType?: DocType): string {
  return docType ? TYPE_LIST_LABELS[docType] : 'Documents'
}

export function docRegistryBackUrl(
  prefix: string,
  docType?: DocType,
  returnTo?: string | null,
): string {
  if (returnTo != null && returnTo.trim() !== '') return returnTo
  return docRegistryListUrl(prefix, docType)
}

export function docRegistryListUrl(
  prefix: string,
  docType?: DocType,
): string {
  const scope: RegistrySortScope = docType ?? 'all'
  const slug = docType ? DOC_TYPE_SLUGS[docType] : undefined
  const params = new URLSearchParams()
  if (slug) params.set('type', slug)
  if (prefix === activeRegistryPrefix) {
    const stored = readStoredSort(prefix, scope)
    if (stored) {
      if (stored.field !== DEFAULT_SORT_FIELD) params.set('sort', stored.field)
      if (stored.dir !== DEFAULT_SORT_DIR) params.set('dir', stored.dir)
    }
  }
  const qs = params.toString()
  return `/projects/${prefix}/docs${qs ? `?${qs}` : ''}`
}
