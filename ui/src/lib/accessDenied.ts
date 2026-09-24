import axios from 'axios'
import type { AccessResourceType } from '../api/client'

/** Whether a failed request means this user may not see the resource (403 or 404). */
export function isAccessDenied(error: unknown): boolean {
  if (!axios.isAxiosError(error)) return false
  const status = error.response?.status
  return status === 403 || status === 404
}

const DOC_RESOURCE_TYPES: Record<string, AccessResourceType> = {
  REQ: 'requirement',
  TC: 'test-case',
  DES: 'design',
  RSK: 'risk',
  CHG: 'change',
  TCO: 'test-concept',
  DEF: 'defect',
}

/** The access-request resource type for a document kind in the address. */
export function docResourceType(kind: string | undefined): AccessResourceType {
  return DOC_RESOURCE_TYPES[(kind ?? '').toUpperCase()] ?? 'document'
}
