import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || '/api'

export const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

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
  steps: Step[] | null
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
    const response = await api.get<Requirement[]>(`/projects/${projectId}/requirements`)
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
    const response = await api.get<TestCase[]>(`/projects/${projectId}/test-cases`)
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
  getMatrix: async (projectId: number) => {
    const response = await api.get<TraceabilityItem[]>(`/traceability/${projectId}`)
    return response.data
  },
}
