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
