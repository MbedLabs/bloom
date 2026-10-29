import { createQueryClient } from '../lib/queryClient'
// @vitest-environment jsdom
/**
 * Every signed-in route renders its data.
 *
 * The existing smoke test covers only the five public screens, and it renders
 * to a string, so it stops at the first loading state. These mount the real
 * route in jsdom with the API answering in the shapes the backend returns, then
 * wait for the page to settle and assert what a user would actually see. That
 * is the difference between "the module imports" and "the screen works".
 */
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ToastProvider } from '../components/Toast'
import { RESPONSES, user } from './apiFixtures'

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  const mocked: Record<string, unknown> = { ...actual }
  for (const [groupName, group] of Object.entries(actual)) {
    if (!groupName.endsWith('Api') || typeof group !== 'object' || group === null) continue
    const replacement: Record<string, unknown> = {}
    for (const [method, value] of Object.entries(group)) {
      if (typeof value !== 'function') {
        replacement[method] = value
        continue
      }
      const key = `${groupName}.${method}`
      replacement[method] = vi.fn(async () => {
        if (!(key in RESPONSES)) throw new Error(`no fixture for ${key}`)
        return RESPONSES[key]
      })
    }
    mocked[groupName] = replacement
  }
  return mocked
})

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({
    user,
    isLoading: false,
    isAuthenticated: true,
    login: vi.fn(),
    logout: vi.fn(),
    refreshUser: vi.fn(),
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
}))

vi.mock('../components/editor/DocEditor', () => ({
  default: () => <div data-testid="doc-editor" />,
}))

vi.mock('../components/ProjectDocTopology', () => ({
  default: () => <div data-testid="doc-topology" />,
}))

function renderRoute(routePath: string, url: string) {
  const queryClient = createQueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <MemoryRouter initialEntries={[url]}>
          <Routes>
            <Route path={routePath} element={<Outlet routePath={routePath} />} />
          </Routes>
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
}

/** Lazily resolves the component for a route so one harness serves them all. */
function Outlet({ routePath }: { routePath: string }) {
  const Component = ROUTE_COMPONENTS[routePath]
  return <Component />
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const ROUTE_COMPONENTS: Record<string, any> = {}

async function registerRoutes() {
  const [
    Dashboard,
    Projects,
    ProjectDetail,
    Documents,
    Defects,
    TestCampaigns,
    TraceabilityMatrix,
    Baselines,
    Users,
    Settings,
    Reports,
    ProjectParameters,
    ImpactAnalysis,
    SuiteDetail,
    CampaignDetail,
    ArtefactDetail,
    DocCreate,
    UnifiedDocDetail,
    ImportWizard,
    ProjectEdit,
  ] = await Promise.all([
    import('../pages/Dashboard'),
    import('../pages/Projects'),
    import('../pages/ProjectDetail'),
    import('../pages/Documents'),
    import('../pages/Defects'),
    import('../pages/TestCampaigns'),
    import('../pages/TraceabilityMatrix'),
    import('../pages/Baselines'),
    import('../pages/Users'),
    import('../pages/Settings'),
    import('../pages/Reports'),
    import('../pages/ProjectParameters'),
    import('../pages/ImpactAnalysis'),
    import('../pages/SuiteDetail'),
    import('../pages/CampaignDetail'),
    import('../pages/ArtefactDetail'),
    import('../pages/DocCreate'),
    import('../pages/UnifiedDocDetail'),
    import('../pages/ImportWizard'),
    import('../pages/ProjectEdit'),
  ])
  Object.assign(ROUTE_COMPONENTS, {
    '/': Dashboard.default,
    '/projects': Projects.default,
    '/projects/:prefix': ProjectDetail.default,
    '/projects/:prefix/docs': Documents.default,
    '/projects/:prefix/defects': Defects.default,
    '/projects/:prefix/campaigns': TestCampaigns.default,
    '/projects/:prefix/traceability': TraceabilityMatrix.default,
    '/projects/:prefix/baselines': Baselines.default,
    '/projects/:prefix/parameters': ProjectParameters.default,
    '/projects/:prefix/impact-analysis/:requirementId': ImpactAnalysis.default,
    '/projects/:prefix/suites/:suiteId': SuiteDetail.default,
    '/projects/:prefix/campaigns/:campaignId': CampaignDetail.default,
    '/projects/:prefix/defects/:itemId': () => <ArtefactDetail.default kind="defect" />,
    '/users': Users.default,
    '/settings': Settings.default,
    '/reports': Reports.default,
    '/projects/:prefix/docs/new': DocCreate.default,
    '/projects/:prefix/docs/:kind/:docId/edit': () => <DocCreate.default editMode />,
    '/projects/:prefix/docs/:kind/:docId': UnifiedDocDetail.default,
    '/projects/:prefix/import': ImportWizard.default,
    '/projects/:prefix/edit': ProjectEdit.default,
  })
}

await registerRoutes()

beforeEach(() => {
  window.sessionStorage.clear()
  window.localStorage.clear()
  window.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('signed-in routes render their data', () => {
  it.each([
    ['/', '/', 'Demo'],
    ['/projects', '/projects', 'Demo'],
    ['/projects/:prefix', '/projects/PRJ', 'Demo'],
    ['/projects/:prefix/docs', '/projects/PRJ/docs', 'PRJ-REQ-001'],
    ['/projects/:prefix/defects', '/projects/PRJ/defects', 'Screen flickers on wake'],
    ['/projects/:prefix/campaigns', '/projects/PRJ/campaigns', 'Release candidate sweep'],
    ['/projects/:prefix/traceability', '/projects/PRJ/traceability', 'PRJ-REQ-001'],
    ['/projects/:prefix/baselines', '/projects/PRJ/baselines', 'Release 1.0'],
    ['/projects/:prefix/parameters', '/projects/PRJ/parameters', 'BOOT_BUDGET_MS'],
    [
      '/projects/:prefix/impact-analysis/:requirementId',
      '/projects/PRJ/impact-analysis/11',
      'PRJ-REQ-001',
    ],
    ['/projects/:prefix/suites/:suiteId', '/projects/PRJ/suites/41', 'Smoke suite'],
    [
      '/projects/:prefix/campaigns/:campaignId',
      '/projects/PRJ/campaigns/31',
      'Release candidate sweep',
    ],
    ['/projects/:prefix/defects/:itemId', '/projects/PRJ/defects/51', 'Screen flickers on wake'],
    ['/users', '/users', 'Ada Lovelace'],
    ['/settings', '/settings', 'Settings'],
    ['/reports', '/reports', 'Reports'],
    ['/projects/:prefix/docs/new', '/projects/PRJ/docs/new?type=REQ', 'PRJ-REQ-004'],
    [
      '/projects/:prefix/docs/:kind/:docId/edit',
      '/projects/PRJ/docs/requirements/PRJ-REQ-001/edit',
      'PRJ-REQ-001',
    ],
    [
      '/projects/:prefix/docs/:kind/:docId',
      '/projects/PRJ/docs/requirements/PRJ-REQ-001',
      'The system shall boot within 2 seconds',
    ],
    ['/projects/:prefix/import', '/projects/PRJ/import', 'Import'],
    ['/projects/:prefix/edit', '/projects/PRJ/edit', 'Demo'],
  ])('%s shows its content', async (routePath, url, expected) => {
    renderRoute(routePath, url)
    const found = await screen.findAllByText(new RegExp(expected, 'i'), {}, { timeout: 4000 })
    expect(found.length).toBeGreaterThan(0)
  })
})

describe('document collections are named in the plural', () => {
  it('on the dashboard count tiles', async () => {
    renderRoute('/', '/')
    expect(await screen.findByText('Designs', {}, { timeout: 4000 })).toBeTruthy()
    for (const label of ['Requirements', 'Changes', 'Standards', 'Test Campaigns']) {
      expect(screen.getAllByText(label).length).toBeGreaterThan(0)
    }
    for (const label of ['Design', 'Change Request', 'External Standard', 'Campaign']) {
      expect(screen.queryByText(label)).toBeNull()
    }
  })

  it('on the project overview tiles', async () => {
    renderRoute('/projects/:prefix', '/projects/PRJ')
    expect(await screen.findByText('Designs', {}, { timeout: 4000 })).toBeTruthy()
    expect(screen.queryByText('Design')).toBeNull()
  })
})
