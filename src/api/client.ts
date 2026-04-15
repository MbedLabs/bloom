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
  created_at: string
  updated_at: string
}

export interface Requirement {
  id: number
  project_id: number
  parent_id: number | null
  req_id: string
  title: string
  description: string | null
  status: string
  priority: string
  req_type: string
  req_origin: string
  test_case_count: number
  children: Requirement[]
  linked_test_cases: TestCase[]
  linked_test_runs: TestRunLink[]
  created_at: string
  updated_at: string
}

export interface TestCase {
  id: number
  project_id: number
  tc_id: string
  title: string
  description: string | null
  preconditions: string | null
  steps: Step[] | TcsRow[] | null
  status: string
  requirement_count: number
  linked_requirements: Requirement[]
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

export const projectsApi = {
  list: async () => {
    const response = await api.get<Project[]>('/projects')
    return response.data
  },

  get: async (id: number) => {
    const response = await api.get<Project>(`/projects/${id}`)
    return response.data
  },

  create: async (data: { name: string; prefix: string; description?: string }) => {
    const response = await api.post<Project>('/projects', data)
    return response.data
  },

  update: async (id: number, data: Partial<Project>) => {
    const response = await api.put<Project>(`/projects/${id}`, data)
    return response.data
  },

  delete: async (id: number) => {
    await api.delete(`/projects/${id}`)
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
    const response = await api.put<Requirement>(`/requirements/${id}`, data)
    return response.data
  },

  delete: async (id: number) => {
    await api.delete(`/requirements/${id}`)
  },

  linkTestCase: async (requirementId: number, testCaseId: number) => {
    const response = await api.post(`/requirements/${requirementId}/link-test-case`, { test_case_id: testCaseId })
    return response.data
  },

  unlinkTestCase: async (requirementId: number, testCaseId: number) => {
    await api.delete(`/requirements/${requirementId}/unlink-test-case/${testCaseId}`)
  },

  linkTestRun: async (requirementId: number, testRunId: number) => {
    const response = await api.post(`/requirements/${requirementId}/link-test-run`, { test_run_id: testRunId })
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
    steps?: Step[]
  }) => {
    const response = await api.post<TestCase>('/test-cases', data)
    return response.data
  },

  update: async (id: number, data: Partial<TestCase>) => {
    const response = await api.put<TestCase>(`/test-cases/${id}`, data)
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
  title: string
  doc_type: string
  status: string
  version: string
  description: string | null
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
  linked_requirement_id: number | null
  created_at: string
  updated_at: string
  child_sections: DocumentSection[]
}

export interface DocumentDetail extends Omit<Document, 'section_count'> {
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
  create: async (data: { project_id: number; title: string; doc_type?: string; description?: string }) => {
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
  addSection: async (documentId: number, data: { title: string; content?: string; section_type?: string; order?: number; linked_requirement_id?: number }) => {
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
}

export interface TestCampaignDetail extends TestCampaign {
  items: TestCampaignItem[]
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

  create: async (data: { project_id: number; name: string; description?: string; configuration_id?: number; test_case_ids?: number[] }) => {
    const response = await api.post<TestCampaignDetail>('/campaigns', data)
    return response.data
  },

  update: async (campaignId: number, data: Partial<Pick<TestCampaign, 'name' | 'description' | 'status'>> & { configuration_id?: number }) => {
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

  updateItem: async (campaignId: number, itemId: number, data: { status?: string; result?: string; comment?: string }) => {
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
