import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || '/api'

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('bloom_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('bloom_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export interface User {
  id: number
  email: string
  full_name: string
  role: 'admin' | 'maintainer' | 'reviewer'
  is_active: boolean
  created_at: string
  updated_at: string
}

export const APP_VERSION = '0.1.4'

export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

export const authApi = {
  login: async (email: string, password: string): Promise<LoginResponse> => {
    const response = await api.post<LoginResponse>('/auth/login', { email, password })
    return response.data
  },
  getMe: async (): Promise<User> => {
    const response = await api.get<User>('/auth/me')
    return response.data
  },
  updateMe: async (data: { full_name?: string; email?: string }): Promise<User> => {
    const response = await api.put<User>('/auth/me', data)
    return response.data
  },
  changePassword: async (currentPassword: string, newPassword: string): Promise<User> => {
    const response = await api.put<User>('/auth/me/password', { current_password: currentPassword, new_password: newPassword })
    return response.data
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
  total_documents: number
  total_campaigns: number
  active_campaigns: number
  coverage_percent: number
  uncovered_requirements: number
  requirement_status_distribution: Record<string, number>
  test_case_status_distribution: Record<string, number>
  campaign_result_distribution: Record<string, number>
  projects: { id: number; name: string; prefix: string; status: string; requirement_count: number; test_case_count: number }[]
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
  design_count: number
  risk_count: number
  change_count: number
  test_concept_count: number
  test_suite_count: number
  created_at: string
  updated_at: string
}

export interface RequirementSummary {
  id: number
  req_id: string
  title: string
  status: string
}

export interface TestCaseSummary {
  id: number
  tc_id: string
  title: string
  status: string
}

export interface TestSuiteSummary {
  id: number
  suite_id: string
  name: string
  status: string
}

export interface TestCampaignSummary {
  id: number
  name: string
  status: string
}

export interface RequirementVerifiedByLink {
  id: number
  link_type: string
  created_at: string
  test_case: TestCaseSummary
}

export interface TestCaseVerifiesLink {
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
  reviewer_id: number | null
  approver_id: number | null
  reviewed_by_id: number | null
  approved_by_id: number | null
  reviewed_at: string | null
  approved_at: string | null
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

export type TcsRowType = 'precondition' | 'step' | 'loop' | 'postcondition'

export interface TcsRow {
  id: string
  row_type: TcsRowType
  label: string
  description: string
  expected_result: string
  indent_level: number
  collapsed: boolean
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

export interface CoverageGap {
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

export interface RequirementLinkResponse {
  id: number
  source_id: number
  target_id: number
  link_type: string
  created_at: string
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
  priority: string
  change_type: string
  impact_assessment: string | null
  justification: string | null
  source_ref?: string | null
  source_project_id?: number | null
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

export interface RelatedRequirementSummary {
  id: number
  req_id: string
  title: string
  status: string
}

export interface RelatedTestCaseSummary {
  id: number
  tc_id: string
  title: string
  status: string
}

export interface RelatedDocumentSummary {
  id: number
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

export interface DocShell {
  id: number
  doc_id: string
  doc_type: string
  title: string
  status: string
  priority: string | null
  project_id: number
  created_at: string
  updated_at: string
}

export interface DocDetailFacade extends DocShell {
  description: string | null
  content_json: Record<string, unknown> | null
  content_html: string | null
}

export const docsApi = {
  list: async (projectRef: string, params?: { type?: string[]; status?: string; q?: string }) => {
    const query = new URLSearchParams()
    if (params?.type) params.type.forEach(t => query.append('type', t))
    if (params?.status) query.set('status', params.status)
    if (params?.q) query.set('q', params.q)
    const qs = query.toString()
    const response = await api.get<DocShell[]>(`/projects/${projectRef}/docs${qs ? '?' + qs : ''}`)
    return response.data
  },
  get: async (projectRef: string, docId: string) => {
    const response = await api.get<DocDetailFacade>(`/projects/${projectRef}/docs/${docId}`)
    return response.data
  },
}

export const requirementsApi = {
  list: async (projectId: number) => {
    const response = await api.get<Requirement[]>(`/requirements`, { params: { project_id: projectId } })
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

  linkTestCase: async (requirementId: number, testCaseId: number, linkType: string = 'verifies') => {
    const response = await api.post(`/requirements/${requirementId}/link-testcase`, { test_case_id: testCaseId, link_type: linkType })
    return response.data
  },

  unlinkTestCase: async (requirementId: number, testCaseId: number) => {
    await api.delete(`/requirements/${requirementId}/link-testcase/${testCaseId}`)
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
  list: async (projectId: number) => {
    const response = await api.get<TestCase[]>(`/test-cases`, { params: { project_id: projectId } })
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

  linkRequirement: async (testCaseId: number, requirementId: number, linkType: string = 'verifies') => {
    const response = await api.post(`/test-cases/${testCaseId}/link-requirement`, {
      requirement_id: requirementId,
      link_type: linkType,
    })
    return response.data
  },

  unlinkRequirement: async (testCaseId: number, requirementId: number) => {
    await api.delete(`/test-cases/${testCaseId}/link-requirement/${requirementId}`)
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

  createRequirementLink: async (sourceId: number, data: { target_id: number; link_type: string }) => {
    const response = await api.post<RequirementLinkResponse>(`/traceability/requirement-links?source_id=${sourceId}`, data)
    return response.data
  },

  deleteRequirementLink: async (linkId: number) => {
    await api.delete(`/traceability/requirement-links/${linkId}`)
  },

  getRequirementLinks: async (requirementId: number, direction?: string) => {
    const query = direction ? `?direction=${direction}` : ''
    const response = await api.get<RequirementLinkResponse[]>(`/traceability/requirement-links/${requirementId}${query}`)
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
    const response = await api.get<Document[]>(`/projects/${projectId}/documents`)
    return response.data
  },
  get: async (documentId: number) => {
    const response = await api.get<DocumentDetail>(`/documents/${documentId}`)
    return response.data
  },
  create: async (data: { project_id: number; title: string; doc_type?: string; description?: string; content_json?: Record<string, unknown> | null; content_html?: string | null }) => {
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
  created_at: string
  updated_at: string
  total_items: number
}

export interface TestSuiteDetail extends TestSuite {
  items: TestSuiteItem[]
  related_requirements: RequirementSummary[]
  linked_campaigns: TestCampaignSummary[]
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
  configuration_id: number | null
  suite_id: number | null
  bud_run_id: number | null
  bud_run_url: string | null
  bud_run_status: string | null
  name: string
  description: string | null
  status: string
  started_at: string | null
  completed_at: string | null
  created_at: string
  updated_at: string
  total_items: number
  passed: number
  failed: number
  blocked: number
  pending: number
  configuration: TestConfiguration | null
  suite: TestSuiteSummary | null
}

export interface TestCampaignDetail extends TestCampaign {
  items: TestCampaignItem[]
  related_requirements: RequirementSummary[]
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
  list: async (projectId: number, status?: string) => {
    const params = new URLSearchParams({ project_id: String(projectId) })
    if (status) params.set('status', status)
    const response = await api.get<TestCampaign[]>(`/campaigns?${params}`)
    return response.data
  },

  get: async (campaignId: number) => {
    const response = await api.get<TestCampaignDetail>(`/campaigns/${campaignId}`)
    return response.data
  },

  create: async (data: { project_id: number; name: string; description?: string; configuration_id?: number; suite_id?: number; status?: string; bud_run_id?: number; bud_run_url?: string; bud_run_status?: string; test_case_ids?: number[] }) => {
    const response = await api.post<TestCampaignDetail>('/campaigns', data)
    return response.data
  },

  update: async (campaignId: number, data: Partial<Pick<TestCampaign, 'name' | 'description' | 'status' | 'bud_run_id' | 'bud_run_url' | 'bud_run_status'>> & { configuration_id?: number; suite_id?: number | null }) => {
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
  list: async (projectId: number) => {
    const response = await api.get<TestSuite[]>('/test-suites', { params: { project_id: projectId } })
    return response.data
  },
  get: async (suiteId: number) => {
    const response = await api.get<TestSuiteDetail>(`/test-suites/${suiteId}`)
    return response.data
  },
  create: async (data: { project_id: number; name: string; description?: string; status?: string; test_case_ids?: number[] }) => {
    const response = await api.post<TestSuiteDetail>('/test-suites', data)
    return response.data
  },
  update: async (suiteId: number, data: { name?: string; description?: string; status?: string }) => {
    const response = await api.patch<TestSuite>(`/test-suites/${suiteId}`, data)
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
  list: async (projectId: number) => {
    const response = await api.get<DesignItem[]>('/designs', { params: { project_id: projectId } })
    return response.data
  },
  get: async (id: number) => {
    const response = await api.get<DesignItem>(`/designs/${id}`)
    return response.data
  },
  create: async (data: Omit<DesignItem, 'id' | 'design_id' | 'created_at' | 'updated_at'>) => {
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
  list: async (projectId: number) => {
    const response = await api.get<RiskItem[]>('/risks', { params: { project_id: projectId } })
    return response.data
  },
  get: async (id: number) => {
    const response = await api.get<RiskItem>(`/risks/${id}`)
    return response.data
  },
  create: async (data: Omit<RiskItem, 'id' | 'risk_id' | 'created_at' | 'updated_at'>) => {
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
  list: async (projectId: number) => {
    const response = await api.get<ChangeRequest[]>('/changes', { params: { project_id: projectId } })
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
  list: async (projectId: number) => {
    const response = await api.get<TestConcept[]>('/test-concepts', { params: { project_id: projectId } })
    return response.data
  },
  get: async (id: number) => {
    const response = await api.get<TestConcept>(`/test-concepts/${id}`)
    return response.data
  },
  create: async (data: { project_id: number; name: string; description?: string | null; status?: string; linked_requirement_ids?: number[]; coverage?: number }) => {
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

export const importApi = {
  import: async (projectId: number, data: ImportRequest): Promise<ImportResult> => {
    const response = await api.post<ImportResult>(`/projects/${projectId}/import`, data)
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
