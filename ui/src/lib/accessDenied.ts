import axios from 'axios'
import type { AccessResourceType } from '../api/client'

/** Whether a failed request means this user may not see the resource (403 or 404). */
export function isAccessDenied(error: unknown): boolean {
  const status = errorStatus(error)
  return status === 403 || status === 404
}

/** The HTTP status of a failed request, if it has one. */
export function errorStatus(error: unknown): number | undefined {
  return axios.isAxiosError(error) ? error.response?.status : undefined
}

const DOC_RESOURCE_TYPES: Record<string, AccessResourceType> = {
  REQ: 'requirement',
  TC: 'test-case',
  DES: 'design',
  RSK: 'risk',
  CHG: 'change',
  CPT: 'test-concept',
  DEF: 'defect',
  TS: 'test-suite',
  CMP: 'campaign',
  REQUIREMENTS: 'requirement',
  'TEST-CASES': 'test-case',
  DESIGNS: 'design',
  RISKS: 'risk',
  CHANGES: 'change',
  'TEST-CONCEPTS': 'test-concept',
  DEFECTS: 'defect',
  'TEST-SUITES': 'test-suite',
  CAMPAIGNS: 'campaign',
}

/** The access-request resource type for a document kind or kind slug in the address. */
export function docResourceType(kind: string | undefined): AccessResourceType {
  return DOC_RESOURCE_TYPES[(kind ?? '').toUpperCase()] ?? 'document'
}
