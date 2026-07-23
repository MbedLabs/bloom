import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'
import { type DocType, DOC_TYPE_SLUGS } from '../types/doc'
import type { TcsRow } from '../utils/tcs'
export type { TcsRow } from '../utils/tcs'
import { clearAuthToken, getAuthToken, setAuthToken } from '../lib/tokenStorage'
import packageJson from '../../package.json'

const API_URL = import.meta.env.VITE_API_URL || '/api'

const api = axios.create({
  baseURL: API_URL,
  // Send the httpOnly refresh cookie on same-origin auth calls.
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use((config) => {
  const token = getAuthToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

const PUBLIC_PATHS = ['/login', '/accept-invite', '/verify-email', '/forgot-password', '/reset-password']

function redirectToLogin() {
  clearAuthToken()
  if (!PUBLIC_PATHS.includes(window.location.pathname)) {
    window.location.href = '/login'
  }
}

// De-duplicate concurrent refreshes: when the short access token expires, many
// in-flight requests can 401 at once; they all await a single /auth/refresh.
let refreshPromise: Promise<string | null> | null = null

async function refreshAccessToken(): Promise<string | null> {
  try {
    // Bare axios (no interceptors) so a 401 here cannot recurse into itself.
    const resp = await axios.post<{ access_token: string }>(
      `${API_URL}/auth/refresh`,
      {},
      { withCredentials: true },
    )
    setAuthToken(resp.data.access_token)
    return resp.data.access_token
  } catch {
    return null
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined
    const url = original?.url ?? ''
    const isAuthCall =
      url.includes('/auth/refresh') || url.includes('/auth/login') || url.includes('/auth/logout')

    if (error.response?.status === 401 && original && !original._retried && !isAuthCall) {
      original._retried = true
      if (!refreshPromise) {
        refreshPromise = refreshAccessToken().finally(() => {
          refreshPromise = null
        })
      }
      const newToken = await refreshPromise
      if (newToken) {
        original.headers.Authorization = `Bearer ${newToken}`
        return api(original)
      }
      redirectToLogin()
    } else if (error.response?.status === 401 && !isAuthCall) {
      redirectToLogin()
    }
    return Promise.reject(error)
  },
)

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  skip: number
  limit: number
}

export type ArtefactVisibility = 'internal' | 'customer'

export interface User {
  id: number
  email: string
  full_name: string
  role: 'admin' | 'maintainer' | 'external'
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface InviteUserResponse {
  message: string
  user: User
  invite_link?: string | null
}

export const APP_VERSION = packageJson.version

export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

export interface InviteInfoResponse {
  email: string
  full_name: string
  valid: boolean
  expired: boolean
}

export interface AcceptInviteResponse {
  requires_email_verification: boolean
  email: string
  message: string
}

export interface GenericMessageResponse {
  message: string
}

export function extractApiErrorMessage(error: unknown, fallback = 'Request failed'): string {
  if (axios.isAxiosError<{ detail?: string }>(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string' && detail.trim().length > 0) {
      return detail
    }
  }
  if (error instanceof Error && error.message) {
    return error.message
  }
  return fallback
}

export const authApi = {
  login: async (email: string, password: string): Promise<LoginResponse> => {
    const response = await api.post<LoginResponse>('/auth/login', { email, password })
    return response.data
  },
  refresh: async (): Promise<LoginResponse> => {
    const response = await api.post<LoginResponse>('/auth/refresh')
    return response.data
  },
  logout: async (): Promise<void> => {
    try {
      await api.post('/auth/logout')
    } finally {
      clearAuthToken()
    }
  },
  getMe: async (): Promise<User> => {
    const response = await api.get<User>('/auth/me')
    return response.data
  },
  updateMe: async (data: { full_name?: string }): Promise<User> => {
    const response = await api.put<User>('/auth/me', data)
    return response.data
  },
  requestEmailChange: async (
    currentPassword: string,
    newEmail: string,
  ): Promise<GenericMessageResponse> => {
    const response = await api.post<GenericMessageResponse>('/auth/me/email', {
      current_password: currentPassword,
      new_email: newEmail,
    })
    return response.data
  },
  cancelEmailChange: async (): Promise<GenericMessageResponse> => {
    const response = await api.delete<GenericMessageResponse>('/auth/me/email')
    return response.data
  },
  confirmEmailChange: async (token: string): Promise<GenericMessageResponse> => {
    const response = await api.post<GenericMessageResponse>('/auth/confirm-email-change', { token })
    return response.data
  },
  changePassword: async (currentPassword: string, newPassword: string): Promise<User> => {
    const response = await api.put<User>('/auth/me/password', { current_password: currentPassword, new_password: newPassword })
    return response.data
  },
  getInviteInfo: async (token: string): Promise<InviteInfoResponse> => {
    const response = await api.post<InviteInfoResponse>('/auth/invite-info', { token })
    return response.data
  },
  acceptInvite: async (token: string, password: string): Promise<AcceptInviteResponse> => {
    const response = await api.post<AcceptInviteResponse>('/auth/accept-invite', { token, password })
    return response.data
  },
  verifyEmail: async (token: string): Promise<GenericMessageResponse> => {
    const response = await api.post<GenericMessageResponse>('/auth/verify-email', { token })
    return response.data
  },
  forgotPassword: async (email: string): Promise<GenericMessageResponse> => {
    const response = await api.post<GenericMessageResponse>('/auth/forgot-password', { email })
    return response.data
  },
  resetPassword: async (token: string, newPassword: string): Promise<GenericMessageResponse> => {
    const response = await api.post<GenericMessageResponse>('/auth/reset-password', { token, new_password: newPassword })
    return response.data
  },
}

export interface ServiceCredential {
  id: number
  name: string
  token_prefix: string
  scope: 'test-results:write'
  expires_at: string
  revoked_at: string | null
  last_used_at: string | null
  created_at: string
}

export interface CreatedServiceCredential extends ServiceCredential {
  token: string
}

export const serviceCredentialsApi = {
  list: async (): Promise<ServiceCredential[]> => {
    const response = await api.get<ServiceCredential[]>('/service-credentials')
    return response.data
  },
  create: async (): Promise<CreatedServiceCredential> => {
    const response = await api.post<CreatedServiceCredential>('/service-credentials', {
      name: 'Bud result sync',
      scope: 'test-results:write',
      expires_in_days: 90,
    })
    return response.data
  },
  rotate: async (id: number): Promise<CreatedServiceCredential> => {
    const response = await api.post<CreatedServiceCredential>(`/service-credentials/${id}/rotate`)
    return response.data
  },
  revoke: async (id: number): Promise<void> => {
    await api.delete(`/service-credentials/${id}`)
  },
}

export const usersApi = {
  list: async (): Promise<User[]> => {
    const response = await api.get<User[]>('/users')
    return response.data
  },
  get: async (id: number): Promise<User> => {
    const response = await api.get<User>(`/users/${id}`)
    return response.data
  },
  create: async (data: { email: string; full_name: string; password: string; role?: string }): Promise<User> => {
    const response = await api.post<User>('/users', data)
    return response.data
  },
  invite: async (data: { email: string; full_name: string; role?: string }): Promise<InviteUserResponse> => {
    const response = await api.post<InviteUserResponse>('/users/invite', data)
    return response.data
  },
  update: async (id: number, data: { full_name?: string; email?: string; role?: string; is_active?: boolean }): Promise<User> => {
    const response = await api.patch<User>(`/users/${id}`, data)
    return response.data
  },
  delete: async (id: number): Promise<void> => {
    await api.delete(`/users/${id}`)
  },
}

export interface DashboardStats {
  total_projects: number
  active_projects: number
  total_requirements: number
  total_test_cases: number
  total_campaigns: number
  active_campaigns: number
  coverage_percent: number
  uncovered_requirements: number
  requirement_status_distribution: Record<string, number>
  test_case_status_distribution: Record<string, number>
  campaign_result_distribution: Record<string, number>
  total_defects: number
  open_defects: number
  defect_severity_distribution: Record<string, number>
  defect_status_distribution: Record<string, number>
  projects: {
    id: number
    name: string
    prefix: string
    status: string
    requirement_count: number
    test_case_count: number
    uncovered_requirement_count: number
  }[]
}

export const dashboardApi = {
  getStats: async () => {
    const response = await api.get<DashboardStats>('/dashboard/stats')
    return response.data
  },
}

export interface Project {
  id: number
  name: string
  prefix: string
  description: string | null
  status: string
  requirement_count: number
  test_case_count: number
  campaign_count: number
  design_count: number
  risk_count: number
  change_count: number
  test_concept_count: number
  test_suite_count: number
  defect_count: number
  coverage_percent: number
  uncovered_requirement_count: number
  created_at: string
  updated_at: string
}

export type ProjectMemberRole = 'maintainer' | 'external'

export interface ProjectMember {
  id: number
  user_id: number
  email: string
  full_name: string
  role: ProjectMemberRole
  doc_types: string[]
  created_at: string
  updated_at: string
}

interface RequirementSummary {
  id: number
  req_id: string
  title: string
  status: string
}

interface TestCaseSummary {
  id: number
  tc_id: string
  title: string
  status: string
  last_execution_status?: string | null
  last_executed_at?: string | null
  last_bud_run_id: number | null
}

export interface TestSuiteSummary {
  id: number
  suite_id: string
  name: string
  status: string
  last_execution_status?: string | null
  last_executed_at?: string | null
  last_bud_run_id?: number | null
}

export interface TestCampaignSummary {
  id: number
  campaign_id?: string
  name: string
  status: string
  last_execution_status?: string | null
  last_executed_at?: string | null
}

interface TestConceptSummary {
  id: number
  concept_id: string
  name: string
  status: string
}

interface RequirementVerifiedByLink {
  id: number
  link_type: string
  created_at: string
  test_case: TestCaseSummary
}

interface TestCaseVerifiesLink {
  id: number
  link_type: string
  created_at: string
  requirement: RequirementSummary
}

export interface Requirement {
  id: number
  project_id: number
  parent_id: number | null
  req_id: string
  title: string
  description: string | null
  content_json?: Record<string, unknown> | null
  content_html?: string | null
  status: string
  visibility: ArtefactVisibility
  priority: string
  req_type: string
  req_origin: string
  reviewer_id: number | null
  approver_id: number | null
  reviewed_by_id: number | null
  approved_by_id: number | null
  reviewed_at: string | null
  approved_at: string | null
  source_ref?: string | null
  source_project_id?: number | null
  test_case_count: number
  children: Requirement[]
  linked_test_cases: TestCaseSummary[]
  verified_by: RequirementVerifiedByLink[]
  linked_test_runs: TestRunLink[]
  suite_backlinks: TestSuiteSummary[]
  campaign_backlinks: TestCampaignSummary[]
  created_at: string
  updated_at: string
}

export interface TestCase {
  id: number
  project_id: number
  tc_id: string
  title: string
  description: string | null
  content_json?: Record<string, unknown> | null
  content_html?: string | null
  preconditions: string | null
  steps: Step[] | TcsRow[] | null
  status: string
  visibility: ArtefactVisibility
  reviewer_id: number | null
  approver_id: number | null
  reviewed_by_id: number | null
  approved_by_id: number | null
  reviewed_at: string | null
  approved_at: string | null
  last_execution_status?: string | null
  last_executed_at?: string | null
  last_execution_comment: string | null
  last_bud_run_id: number | null
  source_ref?: string | null
  source_project_id?: number | null
  requirement_count: number
  linked_requirements: RequirementSummary[]
  verifies: TestCaseVerifiesLink[]
  suite_memberships: TestSuiteSummary[]
  campaign_memberships: TestCampaignSummary[]
  created_at: string
  updated_at: string
}

export interface Step {
  step_number: number
  action: string
  expected_result: string
}

export interface TestRunLink {
  id: number
  requirement_id: number
  test_run_id: number
  test_run_name: string | null
  teststation_url: string | null
  status: string | null
  created_at: string
}

export interface TraceabilityItem {
  requirement: Requirement
  linked_test_cases: TestCase[]
  linked_test_runs: TestRunLink[]
  coverage_status: string
}

export interface ImpactNode {
  requirement: Requirement
  link_type: string
  direction: string
  depth: number
  children: ImpactNode[]
}

export interface ImpactAnalysisResponse {
  root_requirement: Requirement
  upstream: ImpactNode[]
  downstream: ImpactNode[]
}

interface CoverageGap {
  requirement: Requirement
  gap_type: string
  linked_test_cases: TestCase[]
  all_test_cases_draft: boolean
  missing_link_types: string[]
}

export interface CoverageGapReport {
  project_id: number
  total_requirements: number
  covered: number
  partial: number
  uncovered: number
  coverage_percent: number
  gaps: CoverageGap[]
}

export interface DesignItem {
  id: number
  project_id: number
  design_id: string
  title: string
  description: string | null
  content_json?: Record<string, unknown> | null
  content_html?: string | null
  status: string
  visibility: ArtefactVisibility
  priority: string
  design_type: string
  linked_requirement_id: number | null
  source_ref?: string | null
  source_project_id?: number | null
  created_at: string
  updated_at: string
}

export interface RiskItem {
  id: number
  project_id: number
  risk_id: string
  title: string
  description: string | null
  content_json?: Record<string, unknown> | null
  content_html?: string | null
  status: string
  visibility: ArtefactVisibility
  severity: string
  probability: string
  mitigation: string | null
  risk_category: string
  linked_requirement_id: number | null
  source_ref?: string | null
  source_project_id?: number | null
  created_at: string
  updated_at: string
}

export interface ChangeRequest {
  id: number
  project_id: number
  change_id: string
  title: string
  description: string | null
  content_json?: Record<string, unknown> | null
  content_html?: string | null
  status: string
  visibility: ArtefactVisibility
  priority: string
  change_type: string
  impact_assessment: string | null
  justification: string | null
  source_ref?: string | null
  source_project_id?: number | null
  created_at: string
  updated_at: string
}

export interface Defect {
  id: number
  project_id: number
  defect_id: string
  title: string
  description: string | null
  status: string
  visibility: ArtefactVisibility
  severity: string
  priority: string
  source_type: string | null
  source_id: number | null
  owner_id: number | null
  reporter_id: number | null
  reviewer_id: number | null
  resolution_summary: string | null
  external_tracker: string | null
  external_repo_full_name: string | null
  external_issue_number: number | null
  external_issue_url: string | null
  external_issue_state: string | null
  closed_at: string | null
  created_at: string
  updated_at: string
}

export interface Baseline {
  id: number
  project_id: number
  name: string
  description: string | null
  status: string
  baseline_type: string
  snapshot: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface TestConcept {
  id: number
  project_id: number
  concept_id: string
  name: string
  description: string | null
  content_json?: Record<string, unknown> | null
  content_html?: string | null
  status: string
  visibility: ArtefactVisibility
  linked_requirement_ids: number[]
  coverage: number
  source_ref?: string | null
  source_project_id?: number | null
  created_at: string
  updated_at: string
}

export interface ArtefactComment {
  id: number
  artefact_type: string
  artefact_id: number
  author_name: string
  body: string
  created_at: string
}

export interface ArtefactActivity {
  id: number
  artefact_type: string
  artefact_id: number
  event_type: string
  summary: string
  created_at: string
}

interface RelatedRequirementSummary {
  id: number
  req_id: string
  title: string
  status: string
}

interface RelatedTestCaseSummary {
  id: number
  tc_id: string
  title: string
  status: string
}

interface RelatedDocumentSummary {
  id: number
  doc_id: string | null
  title: string
  doc_type: string
  status: string
  matched_sections: string[]
}

export interface ArtefactRelated {
  project: { id: number; name: string; prefix: string; status: string }
  linked_requirements: RelatedRequirementSummary[]
  related_test_cases: RelatedTestCaseSummary[]
  related_documents: RelatedDocumentSummary[]
}

export const projectsApi = {
  list: async () => {
    const response = await api.get<Project[]>('/projects')
    return response.data
  },

  get: async (id: number) => {
    const response = await api.get<Project>(`/projects/${id}`)
    return response.data
  },

  getByPrefix: async (prefix: string) => {
    const response = await api.get<Project>(`/projects/by-prefix/${prefix}`)
    return response.data
  },

  create: async (data: { name: string; prefix: string; description?: string }) => {
    const response = await api.post<Project>('/projects', data)
    return response.data
  },

  update: async (id: number, data: Partial<Project>) => {
    const response = await api.patch<Project>(`/projects/${id}`, data)
    return response.data
  },

  delete: async (id: number) => {
    await api.delete(`/projects/${id}`)
  },
}

export const projectMembersApi = {
  list: async (projectId: number): Promise<ProjectMember[]> => {
    const response = await api.get<ProjectMember[]>(`/projects/${projectId}/members`)
    return response.data
  },
  create: async (
    projectId: number,
    data: { user_id: number; role: ProjectMemberRole; doc_types?: string[] }
  ): Promise<ProjectMember> => {
    const response = await api.post<ProjectMember>(`/projects/${projectId}/members`, data)
    return response.data
  },
  update: async (
    projectId: number,
    membershipId: number,
    data: { role?: ProjectMemberRole; doc_types?: string[] }
  ): Promise<ProjectMember> => {
    const response = await api.patch<ProjectMember>(
      `/projects/${projectId}/members/${membershipId}`,
      data
    )
    return response.data
  },
  remove: async (projectId: number, membershipId: number): Promise<void> => {
    await api.delete(`/projects/${projectId}/members/${membershipId}`)
  },
}

export interface DocShell {
  id: number
  doc_id: string
  doc_type: string
  title: string
  status: string
  visibility: ArtefactVisibility
  priority: string | null
  req_type: string | null
  req_origin: string | null
  project_id: number
  reviewer_id: number | null
  incoming_links: number
  outgoing_links: number
  suspect_links: number
  last_execution_status: string | null
  last_executed_at: string | null
  last_bud_run_id: number | null
  created_at: string
  updated_at: string
}

export interface DocDetailFacade extends DocShell {
  description: string | null
  content_json: Record<string, unknown> | null
  content_html: string | null
}

export const docsApi = {
  list: async (projectRef: string, params?: { type?: string[]; status?: string; q?: string; includeLinkCounts?: boolean; skip?: number; limit?: number }) => {
    const query = new URLSearchParams()
    if (params?.type) params.type.forEach(t => query.append('type', t))
    if (params?.status) query.set('status', params.status)
    if (params?.q) query.set('q', params.q)
    if (params?.includeLinkCounts !== undefined) query.set('include_link_counts', String(params.includeLinkCounts))
    if (params?.skip !== undefined) query.set('skip', String(params.skip))
    if (params?.limit !== undefined) query.set('limit', String(params.limit))
    const qs = query.toString()
    const response = await api.get<PaginatedResponse<DocShell>>(`/projects/${projectRef}/docs${qs ? '?' + qs : ''}`)
    return response.data
  },
  get: async (projectRef: string, kind: string | DocType, docId: string) => {
    const kindSlug = Object.prototype.hasOwnProperty.call(DOC_TYPE_SLUGS, kind)
      ? DOC_TYPE_SLUGS[kind as DocType]
      : kind
    const response = await api.get<DocDetailFacade>(`/projects/${projectRef}/docs/${kindSlug}/${docId}`)
    return response.data
  },
}

export const requirementsApi = {
  list: async (projectId: number, params?: { skip?: number; limit?: number }) => {
    const response = await api.get<PaginatedResponse<Requirement>>(`/requirements`, { params: { project_id: projectId, ...params } })
    return response.data
  },

  get: async (id: number) => {
    const response = await api.get<Requirement>(`/requirements/${id}`)
    return response.data
  },

  create: async (data: {
    project_id: number
    title: string
    description?: string
    visibility?: ArtefactVisibility
    priority?: string
    req_type?: string
    req_origin?: string
    parent_id?: number | null
  }) => {
    const response = await api.post<Requirement>('/requirements', data)
    return response.data
  },

  update: async (id: number, data: Partial<Requirement>) => {
    const response = await api.patch<Requirement>(`/requirements/${id}`, data)
    return response.data
  },

  setReviewed: async (id: number, reviewedById: number) => {
    const response = await api.patch<Requirement>(`/requirements/${id}`, {
      reviewed_by_id: reviewedById,
      reviewed_at: new Date().toISOString(),
    })
    return response.data
  },

  setApproved: async (id: number, approvedById: number) => {
    const response = await api.patch<Requirement>(`/requirements/${id}`, {
      approved_by_id: approvedById,
      approved_at: new Date().toISOString(),
    })
    return response.data
  },

  delete: async (id: number) => {
    await api.delete(`/requirements/${id}`)
  },

  linkTestRun: async (requirementId: number, testRunId: number) => {
    const response = await api.post(`/requirements/${requirementId}/link-testrun`, { test_run_id: testRunId })
    return response.data
  },

  getTestRuns: async (requirementId: number) => {
    const response = await api.get<TestRunLink[]>(`/requirements/${requirementId}/test-runs`)
    return response.data
  },
}

export const testCasesApi = {
  list: async (projectId: number, params?: { skip?: number; limit?: number }) => {
    const response = await api.get<PaginatedResponse<TestCase>>(`/test-cases`, { params: { project_id: projectId, ...params } })
    return response.data
  },

  get: async (id: number) => {
    const response = await api.get<TestCase>(`/test-cases/${id}`)
    return response.data
  },

  create: async (data: {
    project_id: number
    title: string
    description?: string
    preconditions?: string
    steps?: Step[] | TcsRow[]
    status?: string
    visibility?: ArtefactVisibility
    reviewer_id?: number
    approver_id?: number
  }) => {
    const response = await api.post<TestCase>('/test-cases', data)
    return response.data
  },

  update: async (id: number, data: Partial<TestCase>) => {
    const response = await api.patch<TestCase>(`/test-cases/${id}`, data)
    return response.data
  },

  setReviewed: async (id: number, reviewedById: number) => {
    const response = await api.patch<TestCase>(`/test-cases/${id}`, {
      reviewed_by_id: reviewedById,
      reviewed_at: new Date().toISOString(),
    })
    return response.data
  },

  setApproved: async (id: number, approvedById: number) => {
    const response = await api.patch<TestCase>(`/test-cases/${id}`, {
      approved_by_id: approvedById,
      approved_at: new Date().toISOString(),
    })
    return response.data
  },

  delete: async (id: number) => {
    await api.delete(`/test-cases/${id}`)
  },
}

export const traceabilityApi = {
  getMatrix: async (projectId: number, params?: { coverage_filter?: string; priority_filter?: string; sort_by?: string }) => {
    const query = new URLSearchParams()
    query.set('project_id', String(projectId))
    if (params?.coverage_filter) query.set('coverage_filter', params.coverage_filter)
    if (params?.priority_filter) query.set('priority_filter', params.priority_filter)
    if (params?.sort_by) query.set('sort_by', params.sort_by)
    const response = await api.get<TraceabilityItem[]>(`/traceability?${query.toString()}`)
    return response.data
  },

  getImpactAnalysis: async (requirementId: number, depth?: number) => {
    const query = depth ? `?depth=${depth}` : ''
    const response = await api.get<ImpactAnalysisResponse>(`/traceability/impact/${requirementId}${query}`)
    return response.data
  },

  getCoverageGaps: async (projectId: number) => {
    const response = await api.get<CoverageGapReport>(`/traceability/coverage-gaps/${projectId}`)
    return response.data
  },
}

export interface Document {
  id: number
  project_id: number
  doc_id?: string | null
  title: string
  doc_type: string
  status: string
  visibility: ArtefactVisibility
  version: string
  description: string | null
  content_json?: Record<string, unknown> | null
  content_html?: string | null
  created_at: string
  updated_at: string
  section_count: number
}

export interface DocumentSection {
  id: number
  document_id: number
  parent_section_id: number | null
  order: number
  title: string
  content: string | null
  section_type: string
  created_at: string
  updated_at: string
  child_sections: DocumentSection[]
}

export interface DocumentDetail extends Omit<Document, 'section_count'> {
  content_json?: Record<string, unknown> | null
  content_html?: string | null
  sections: DocumentSection[]
}

export const documentsApi = {
  list: async (projectId: number) => {
    const response = await api.get<PaginatedResponse<Document>>(`/projects/${projectId}/documents`)
    return response.data
  },
  get: async (documentId: number) => {
    const response = await api.get<DocumentDetail>(`/documents/${documentId}`)
    return response.data
  },
  create: async (data: { project_id: number; title: string; doc_type?: string; description?: string; content_json?: Record<string, unknown> | null; content_html?: string | null; visibility?: ArtefactVisibility }) => {
    const response = await api.post<Document>('/projects/' + data.project_id + '/documents', data)
    return response.data
  },
  update: async (id: number, data: Partial<Document>) => {
    const response = await api.patch<Document>('/documents/' + id, data)
    return response.data
  },
  delete: async (id: number) => {
    await api.delete('/documents/' + id)
  },
  addSection: async (documentId: number, data: { title: string; content?: string; section_type?: string; order?: number }) => {
    const response = await api.post<DocumentSection>('/documents/' + documentId + '/sections', data)
    return response.data
  },
  updateSection: async (sectionId: number, data: Partial<DocumentSection>) => {
    const response = await api.patch<DocumentSection>('/document-sections/' + sectionId, data)
    return response.data
  },
  deleteSection: async (sectionId: number) => {
    await api.delete('/document-sections/' + sectionId)
  },
  reorderSections: async (documentId: number, sectionOrders: { id: number; order: number }[]) => {
    const response = await api.post('/documents/' + documentId + '/sections/reorder', { section_orders: sectionOrders })
    return response.data
  },
}

export interface ProjectVariable {
  id: number
  project_id: number
  kind: 'parameter' | 'variable'
  key: string
  value: string
  description: string | null
  created_at: string
  updated_at: string
}

export const projectVariablesApi = {
  list: async (projectId: number) => {
    const response = await api.get<ProjectVariable[]>('/project-variables', { params: { project_id: projectId } })
    return response.data
  },
  create: async (data: { project_id: number; kind: 'parameter' | 'variable'; key: string; value: string; description?: string | null }) => {
    const response = await api.post<ProjectVariable>('/project-variables', data)
    return response.data
  },
  update: async (id: number, data: Partial<Pick<ProjectVariable, 'kind' | 'key' | 'value' | 'description'>>) => {
    const response = await api.patch<ProjectVariable>(`/project-variables/${id}`, data)
    return response.data
  },
  delete: async (id: number) => {
    await api.delete(`/project-variables/${id}`)
  },
}

export interface TestConfiguration {
  id: number
  project_id: number
  name: string
  description: string | null
  environment: string | null
  parameters: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface TestSuiteItem {
  id: number
  suite_id: number
  test_case_id: number
  order: number
  created_at: string
  test_case: TestCaseSummary | null
}

export interface TestSuite extends TestSuiteSummary {
  project_id: number
  description: string | null
  visibility: ArtefactVisibility
  created_at: string
  updated_at: string
  total_items: number
  last_execution_status: string | null
  last_executed_at: string | null
  last_bud_run_id: number | null
}

export interface TestSuiteDetail extends TestSuite {
  items: TestSuiteItem[]
  related_requirements: RequirementSummary[]
  linked_campaigns: TestCampaignSummary[]
  related_concepts: TestConceptSummary[]
}

export interface TestCampaignItem {
  id: number
  campaign_id: number
  test_case_id: number
  status: string
  result: string | null
  comment: string | null
  executed_at: string | null
  created_at: string
  test_case: TestCase | null
}

export interface TestCampaign {
  id: number
  project_id: number
  campaign_id?: string
  configuration_id: number | null
  suite_id: number | null
  bud_run_id: number | null
  bud_run_url: string | null
  bud_run_status: string | null
  name: string
  description: string | null
  status: string
  visibility: ArtefactVisibility
  started_at: string | null
  completed_at: string | null
  created_at: string
  updated_at: string
  total_items: number
  passed: number
  failed: number
  blocked: number
  pending: number
  last_execution_status: string | null
  last_executed_at: string | null
  configuration: TestConfiguration | null
  suite: TestSuiteSummary | null
  suites: TestSuiteSummary[]
}

interface TestCampaignSuiteScope {
  suite: TestSuiteSummary
  items: TestCampaignItem[]
}

export interface TestCampaignDetail extends TestCampaign {
  items: TestCampaignItem[]
  suite_scopes: TestCampaignSuiteScope[]
  ad_hoc_items: TestCampaignItem[]
  related_requirements: RequirementSummary[]
  related_concepts: TestConceptSummary[]
}

export interface ArtefactLink {
  id: number
  project_id: number
  source_type: string
  source_id: number
  target_type: string
  target_id: number
  role: string
  suspect: boolean
  created_at: string
}

export const campaignsApi = {
  list: async (projectId: number, status?: string, params?: { skip?: number; limit?: number }) => {
    const query = new URLSearchParams({ project_id: String(projectId) })
    if (status) query.set('status', status)
    if (params?.skip !== undefined) query.set('skip', String(params.skip))
    if (params?.limit !== undefined) query.set('limit', String(params.limit))
    const response = await api.get<PaginatedResponse<TestCampaign>>(`/campaigns?${query}`)
    return response.data
  },

  get: async (campaignId: number) => {
    const response = await api.get<TestCampaignDetail>(`/campaigns/${campaignId}`)
    return response.data
  },

  create: async (data: { project_id: number; name: string; description?: string; configuration_id?: number; suite_id?: number; suite_ids?: number[]; status?: string; visibility?: ArtefactVisibility; bud_run_id?: number; bud_run_url?: string; bud_run_status?: string; test_case_ids?: number[] }) => {
    const response = await api.post<TestCampaignDetail>('/campaigns', data)
    return response.data
  },

  update: async (campaignId: number, data: Partial<Pick<TestCampaign, 'name' | 'description' | 'status' | 'visibility' | 'bud_run_id' | 'bud_run_url' | 'bud_run_status'>> & { configuration_id?: number; suite_id?: number | null; suite_ids?: number[] }) => {
    const response = await api.patch<TestCampaign>(`/campaigns/${campaignId}`, data)
    return response.data
  },

  delete: async (campaignId: number) => {
    await api.delete(`/campaigns/${campaignId}`)
  },

  addItem: async (campaignId: number, testCaseId: number) => {
    const response = await api.post<TestCampaignItem>(`/campaigns/${campaignId}/items?test_case_id=${testCaseId}`)
    return response.data
  },

  updateItem: async (campaignId: number, itemId: number, data: { comment?: string }) => {
    const response = await api.patch<TestCampaignItem>(`/campaigns/${campaignId}/items/${itemId}`, data)
    return response.data
  },

  removeItem: async (campaignId: number, itemId: number) => {
    await api.delete(`/campaigns/${campaignId}/items/${itemId}`)
  },

  scopeLinks: async (campaignId: number) => {
    const response = await api.get<ArtefactLink[]>(`/campaigns/${campaignId}/scope-links`)
    return response.data
  },

  listConfigurations: async (projectId: number) => {
    const response = await api.get<TestConfiguration[]>(`/campaigns/configurations?project_id=${projectId}`)
    return response.data
  },

  createConfiguration: async (data: { project_id: number; name: string; description?: string; environment?: string; parameters?: Record<string, unknown> }) => {
    const response = await api.post<TestConfiguration>('/campaigns/configurations', data)
    return response.data
  },
}

export const testSuitesApi = {
  list: async (projectId: number, params?: { skip?: number; limit?: number }) => {
    const response = await api.get<PaginatedResponse<TestSuite>>('/test-suites', { params: { project_id: projectId, ...params } })
    return response.data
  },
  get: async (suiteId: number) => {
    const response = await api.get<TestSuiteDetail>(`/test-suites/${suiteId}`)
    return response.data
  },
  create: async (data: { project_id: number; name: string; description?: string; status?: string; visibility?: ArtefactVisibility; test_case_ids?: number[] }) => {
    const response = await api.post<TestSuiteDetail>('/test-suites', data)
    return response.data
  },
  update: async (suiteId: number, data: { name?: string; description?: string; status?: string; visibility?: ArtefactVisibility }) => {
    const response = await api.patch<TestSuiteDetail>(`/test-suites/${suiteId}`, data)
    return response.data
  },
  delete: async (suiteId: number) => {
    await api.delete(`/test-suites/${suiteId}`)
  },
  addItem: async (suiteId: number, testCaseId: number) => {
    const response = await api.post<TestSuiteItem>(`/test-suites/${suiteId}/items?test_case_id=${testCaseId}`)
    return response.data
  },
  removeItem: async (suiteId: number, itemId: number) => {
    await api.delete(`/test-suites/${suiteId}/items/${itemId}`)
  },
}

export const linksApi = {
  list: async (params: { project_id: number; source_type?: string; source_id?: number; target_type?: string; target_id?: number }) => {
    const response = await api.get<ArtefactLink[]>('/links', { params })
    return response.data
  },
  create: async (data: Omit<ArtefactLink, 'id' | 'created_at'>) => {
    const response = await api.post<ArtefactLink>('/links', data)
    return response.data
  },
  delete: async (linkId: number) => {
    await api.delete(`/links/${linkId}`)
  },
}

export const designsApi = {
  list: async (projectId: number, params?: { skip?: number; limit?: number }) => {
    const response = await api.get<PaginatedResponse<DesignItem>>('/designs', { params: { project_id: projectId, ...params } })
    return response.data
  },
  get: async (id: number) => {
    const response = await api.get<DesignItem>(`/designs/${id}`)
    return response.data
  },
  create: async (data: {
    project_id: number
    title: string
    description?: string | null
    status?: string
    visibility?: ArtefactVisibility
    priority?: string
    design_type?: string
  }) => {
    const response = await api.post<DesignItem>('/designs', data)
    return response.data
  },
  update: async (id: number, data: Partial<DesignItem>) => {
    const response = await api.patch<DesignItem>(`/designs/${id}`, data)
    return response.data
  },
  delete: async (id: number) => {
    await api.delete(`/designs/${id}`)
  },
}

export const risksApi = {
  list: async (projectId: number, params?: { skip?: number; limit?: number }) => {
    const response = await api.get<PaginatedResponse<RiskItem>>('/risks', { params: { project_id: projectId, ...params } })
    return response.data
  },
  get: async (id: number) => {
    const response = await api.get<RiskItem>(`/risks/${id}`)
    return response.data
  },
  create: async (data: {
    project_id: number
    title: string
    description?: string | null
    status?: string
    visibility?: ArtefactVisibility
    severity?: string
    probability?: string
    mitigation?: string | null
    risk_category?: string
  }) => {
    const response = await api.post<RiskItem>('/risks', data)
    return response.data
  },
  update: async (id: number, data: Partial<RiskItem>) => {
    const response = await api.patch<RiskItem>(`/risks/${id}`, data)
    return response.data
  },
  delete: async (id: number) => {
    await api.delete(`/risks/${id}`)
  },
}

export const changesApi = {
  list: async (projectId: number, params?: { skip?: number; limit?: number }) => {
    const response = await api.get<PaginatedResponse<ChangeRequest>>('/changes', { params: { project_id: projectId, ...params } })
    return response.data
  },
  get: async (id: number) => {
    const response = await api.get<ChangeRequest>(`/changes/${id}`)
    return response.data
  },
  create: async (data: Omit<ChangeRequest, 'id' | 'change_id' | 'created_at' | 'updated_at'>) => {
    const response = await api.post<ChangeRequest>('/changes', data)
    return response.data
  },
  update: async (id: number, data: Partial<ChangeRequest>) => {
    const response = await api.patch<ChangeRequest>(`/changes/${id}`, data)
    return response.data
  },
  delete: async (id: number) => {
    await api.delete(`/changes/${id}`)
  },
}

export const defectsApi = {
  list: async (projectId: number, listParams?: { status?: string; severity?: string; skip?: number; limit?: number }) => {
    const response = await api.get<PaginatedResponse<Defect>>('/defects', { params: { project_id: projectId, ...listParams } })
    return response.data
  },
  get: async (id: number) => {
    const response = await api.get<Defect>(`/defects/${id}`)
    return response.data
  },
  create: async (data: {
    project_id: number
    title: string
    description?: string | null
    status?: string
    visibility?: ArtefactVisibility
    severity?: string
    priority?: string
    source_type?: string | null
    source_id?: number | null
    owner_id?: number | null
    reporter_id?: number | null
    reviewer_id?: number | null
    resolution_summary?: string | null
    external_tracker?: string | null
    external_repo_full_name?: string | null
    external_issue_number?: number | null
    external_issue_url?: string | null
    external_issue_state?: string | null
  }) => {
    const response = await api.post<Defect>('/defects', data)
    return response.data
  },
  update: async (id: number, data: Partial<Defect>) => {
    const response = await api.patch<Defect>(`/defects/${id}`, data)
    return response.data
  },
  delete: async (id: number) => {
    await api.delete(`/defects/${id}`)
  },
}

export interface IntegrationSetting {
  id: number
  project_id: number
  tracker: string
  base_url: string | null
  has_token: boolean
  has_webhook_secret: boolean
  enabled: boolean
  created_at: string
  updated_at: string
}

export interface SyncEvent {
  id: number
  defect_id: number
  direction: string
  tracker: string
  event_type: string
  payload_summary: string | null
  success: boolean
  error_message: string | null
  created_at: string
}

export const integrationsApi = {
  listSettings: async (projectId: number) => {
    const response = await api.get<IntegrationSetting[]>('/integrations/settings', { params: { project_id: projectId } })
    return response.data
  },
  createSetting: async (data: { project_id: number; tracker: string; base_url?: string; token?: string; webhook_secret?: string; enabled?: boolean }) => {
    const response = await api.post<IntegrationSetting>('/integrations/settings', data)
    return response.data
  },
  updateSetting: async (id: number, data: { base_url?: string; token?: string; webhook_secret?: string; enabled?: boolean }) => {
    const response = await api.patch<IntegrationSetting>(`/integrations/settings/${id}`, data)
    return response.data
  },
  deleteSetting: async (id: number) => {
    await api.delete(`/integrations/settings/${id}`)
  },
  listSyncEvents: async (defectId: number) => {
    const response = await api.get<SyncEvent[]>('/integrations/sync-events', { params: { defect_id: defectId } })
    return response.data
  },
  refreshExternal: async (defectId: number, token?: string) => {
    const response = await api.post<Defect>(
      `/defects/${defectId}/refresh-external`,
      token ? { token } : {}
    )
    return response.data
  },
}

export const baselinesApi = {
  list: async (projectId?: number) => {
    const response = await api.get<Baseline[]>('/baselines', { params: projectId ? { project_id: projectId } : undefined })
    return response.data
  },
  get: async (id: number) => {
    const response = await api.get<Baseline>(`/baselines/${id}`)
    return response.data
  },
  create: async (data: { project_id: number; name: string; description?: string; baseline_type?: string }) => {
    const response = await api.post<Baseline>('/baselines', data)
    return response.data
  },
  update: async (id: number, data: Partial<Baseline>) => {
    const response = await api.patch<Baseline>(`/baselines/${id}`, data)
    return response.data
  },
  delete: async (id: number) => {
    await api.delete(`/baselines/${id}`)
  },
}

export const testConceptsApi = {
  list: async (projectId: number, params?: { skip?: number; limit?: number }) => {
    const response = await api.get<PaginatedResponse<TestConcept>>('/test-concepts', { params: { project_id: projectId, ...params } })
    return response.data
  },
  get: async (id: number) => {
    const response = await api.get<TestConcept>(`/test-concepts/${id}`)
    return response.data
  },
  create: async (data: { project_id: number; name: string; description?: string | null; status?: string; visibility?: ArtefactVisibility; coverage?: number }) => {
    const response = await api.post<TestConcept>('/test-concepts', data)
    return response.data
  },
  update: async (id: number, data: Partial<TestConcept>) => {
    const response = await api.patch<TestConcept>(`/test-concepts/${id}`, data)
    return response.data
  },
  delete: async (id: number) => {
    await api.delete(`/test-concepts/${id}`)
  },
}

export interface ImportRequest {
  source_project_id: number
  doc_type: string
  doc_ids: number[]
  include_links: boolean
}

export interface ImportResult {
  imported: number
  skipped: number
  new_ids: string[]
  errors: string[]
}

export interface ReqIFImportResult {
  imported: number
  skipped: number
  links_created: number
  specifications: number
  new_ids: string[]
  errors: string[]
}

export const importApi = {
  import: async (projectId: number, data: ImportRequest): Promise<ImportResult> => {
    const response = await api.post<ImportResult>(`/projects/${projectId}/import`, data)
    return response.data
  },
  importReqif: async (projectId: number, file: File): Promise<ReqIFImportResult> => {
    const form = new FormData()
    form.append('file', file)
    const response = await api.post<ReqIFImportResult>(
      `/projects/${projectId}/import/reqif`,
      form,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    )
    return response.data
  },
}

export interface SearchResultItem {
  type: string
  id: number
  doc_id: string | null
  title: string
  status: string | null
  project_id: number
  project_prefix: string
  project_name: string
}

export interface SearchResponse {
  query: string
  total: number
  items: SearchResultItem[]
}

export const exportApi = {
  /** Download a server-side export, preserving the backend's filename. */
  download: async (
    projectId: number,
    kind: 'requirements' | 'traceability',
    format?: 'csv' | 'pdf'
  ): Promise<void> => {
    const response = await api.get<Blob>(`/projects/${projectId}/export/${kind}`, {
      params: format ? { format } : {},
      responseType: 'blob',
    })
    const disposition = (response.headers['content-disposition'] as string | undefined) ?? ''
    const filename = /filename="([^"]+)"/.exec(disposition)?.[1] ?? `${kind}.${format ?? 'csv'}`
    const url = URL.createObjectURL(response.data)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = filename
    anchor.click()
    URL.revokeObjectURL(url)
  },
}

export interface Notification {
  id: number
  event_type: string
  title: string
  body: string | null
  link_path: string | null
  project_id: number | null
  read_at: string | null
  created_at: string
}

export interface NotificationList {
  items: Notification[]
  total: number
  unread: number
}

export const notificationsApi = {
  list: async (options?: { unreadOnly?: boolean; limit?: number }): Promise<NotificationList> => {
    const response = await api.get<NotificationList>('/notifications', {
      params: {
        ...(options?.unreadOnly ? { unread_only: true } : {}),
        ...(options?.limit ? { limit: options.limit } : {}),
      },
    })
    return response.data
  },
  unreadCount: async (): Promise<number> => {
    const response = await api.get<{ unread: number }>('/notifications/unread-count')
    return response.data.unread
  },
  markRead: async (id: number): Promise<Notification> => {
    const response = await api.post<Notification>(`/notifications/${id}/read`)
    return response.data
  },
  markAllRead: async (): Promise<void> => {
    await api.post('/notifications/read-all')
  },
}

export const searchApi = {
  global: async (q: string, options?: { projectId?: number; limit?: number }): Promise<SearchResponse> => {
    const response = await api.get<SearchResponse>('/search', {
      params: {
        q,
        ...(options?.projectId ? { project_id: options.projectId } : {}),
        ...(options?.limit ? { limit: options.limit } : {}),
      },
    })
    return response.data
  },
}

export const artefactsApi = {
  listComments: async (artefactType: string, artefactId: number) => {
    const response = await api.get<ArtefactComment[]>(`/artefacts/${artefactType}/${artefactId}/comments`)
    return response.data
  },
  createComment: async (artefactType: string, artefactId: number, body: string) => {
    const response = await api.post<ArtefactComment>(`/artefacts/${artefactType}/${artefactId}/comments`, { body })
    return response.data
  },
  listActivity: async (artefactType: string, artefactId: number) => {
    const response = await api.get<ArtefactActivity[]>(`/artefacts/${artefactType}/${artefactId}/activity`)
    return response.data
  },
  getRelated: async (artefactType: string, artefactId: number) => {
    const response = await api.get<ArtefactRelated>(`/artefacts/${artefactType}/${artefactId}/related`)
    return response.data
  },
  transition: async (artefactType: string, artefactId: number, status: string) => {
    const response = await api.post<{ status: string; allowed_transitions: string[] }>(`/artefacts/${artefactType}/${artefactId}/transition`, { status })
    return response.data
  },
}
