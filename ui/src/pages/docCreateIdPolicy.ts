import type { DocType } from '../types/doc'

const SERVER_ASSIGNED_CREATE_TYPES = new Set<DocType>([
  'REQ',
  'SPEC',
  'TC',
  'DES',
  'RSK',
  'CHG',
  'CPT',
  'DEF',
  'PRT',
  'RPT',
  'STD',
])

export function isServerAssignedDocIdOnCreate(docType: DocType): boolean {
  return SERVER_ASSIGNED_CREATE_TYPES.has(docType)
}

/**
 * Document types that own a dedicated page and must never be created or edited
 * through the generic rich-text document editor.
 *
 * A defect carries a severity, a resolution summary, an external tracker link
 * and a sync log; a campaign and a suite carry their own item lists. None of
 * that survives a round trip through the document editor, which knows only how
 * to save a title and a rich body.
 */
const DEDICATED_PAGE_TYPES = new Set<DocType>(['CMP', 'TS', 'DEF'])

export function usesDocumentEditor(docType: DocType): boolean {
  return !DEDICATED_PAGE_TYPES.has(docType)
}

/**
 * The route that owns a dedicated type, or null when the registry is its home.
 * Test suites are listed by the registry and only their detail page is bespoke,
 * so they have no dedicated list route here.
 */
const DEDICATED_LIST_ROUTES: Partial<Record<DocType, string>> = {
  CMP: 'campaigns',
  DEF: 'defects',
}

export function dedicatedListUrl(prefix: string, docType: DocType): string | null {
  const segment = DEDICATED_LIST_ROUTES[docType]
  return segment ? `/projects/${prefix}/${segment}` : null
}
