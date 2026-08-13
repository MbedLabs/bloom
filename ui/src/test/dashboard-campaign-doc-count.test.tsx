import { renderPage } from './render'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'

import type { DashboardStats, Project } from '../api/client'
import Dashboard from '../pages/Dashboard'

const project: Project = {
  id: 1,
  name: 'Dashboard Project',
  prefix: 'DSH',
  description: null,
  status: 'Active',
  requirement_count: 1,
  test_case_count: 1,
  campaign_count: 1,
  design_count: 0,
  risk_count: 0,
  change_count: 0,
  test_concept_count: 0,
  test_suite_count: 0,
  defect_count: 0,
  coverage_percent: 0,
  uncovered_requirement_count: 1,
  created_at: '',
  updated_at: '',
}

const stats: DashboardStats = {
  total_projects: 1,
  active_projects: 1,
  total_requirements: 1,
  total_test_cases: 1,
  total_campaigns: 1,
  active_campaigns: 1,
  coverage_percent: 0,
  uncovered_requirements: 1,
  requirement_status_distribution: { Draft: 1 },
  test_case_status_distribution: { Draft: 1 },
  campaign_result_distribution: {},
  total_defects: 0,
  open_defects: 0,
  defect_severity_distribution: {},
  defect_status_distribution: {},
  projects: [],
}

describe('Dashboard document totals', () => {
  it('counts campaigns as controlled documents', async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    queryClient.setQueryData(['dashboard-stats'], stats)
    queryClient.setQueryData(['projects'], [project])

    const html = renderPage(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <Dashboard />
        </MemoryRouter>
      </QueryClientProvider>,
    )

    expect(html).toContain('>Docs</p><p class="mt-1.5 text-xl font-semibold text-foreground">3</p>')
    expect(html).toContain('>CMP</span>')
  })
})
