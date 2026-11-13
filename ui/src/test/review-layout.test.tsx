// @vitest-environment jsdom
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import type { ReactElement } from 'react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ToastProvider } from '../components/Toast'
import { createQueryClient } from '../lib/queryClient'
import { artefactRelated, change, defect, design, docDetail, project, requirement, resetApiMocks, risk, testCase, testConcept, testSuite, user } from './apiFixtures'

vi.mock('../api/client', async importOriginal => {
  const { mockApiModule } = await import('./apiFixtures')
  return mockApiModule(await importOriginal<Record<string, unknown>>(), vi)
})

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ user, isLoading: false, isAuthenticated: true }),
}))

vi.mock('../components/editor/DocEditor', () => ({
  default: () => <div data-testid="doc-editor" />,
}))

const client = await import('../api/client')
const RequirementDetail = (await import('../pages/RequirementDetail')).default
const TestCaseDetail = (await import('../pages/TestCaseDetail')).default
const DocumentDetail = (await import('../pages/DocumentDetail')).default
const ArtefactDetail = (await import('../pages/ArtefactDetail')).default
const SuiteDetail = (await import('../pages/SuiteDetail')).default
const CampaignDetail = (await import('../pages/CampaignDetail')).default

const richContent = { type: 'doc', content: [{ type: 'paragraph', content: [{ type: 'text', text: 'The brake shall engage.' }] }] }

/** Render a page at a route, as the app mounts it. */
function renderAt(path: string, url: string, element: ReactElement) {
  const queryClient = createQueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <MemoryRouter initialEntries={[url]}>
          <Routes><Route path={path} element={element} /></Routes>
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
}

const richPages: Record<string, () => void> = {
  requirement: () => {
    vi.mocked(client.requirementsApi.get).mockResolvedValue({ ...requirement, content_json: richContent } as never)
    renderAt('/projects/:prefix/requirements/:itemId', `/projects/PRJ/requirements/${requirement.id}`, <RequirementDetail />)
  },
  'test case': () => {
    vi.mocked(client.testCasesApi.get).mockResolvedValue({ ...testCase, content_json: richContent, last_execution_status: 'Passed', last_executed_at: '2026-10-11T00:00:00Z', last_bud_run_id: 77 } as never)
    renderAt('/projects/:prefix/test-cases/:itemId', `/projects/PRJ/test-cases/${testCase.id}`, <TestCaseDetail />)
  },
  document: () => {
    vi.mocked(client.documentsApi.get).mockResolvedValue({ ...docDetail, content_json: richContent } as never)
    renderAt('/projects/:prefix/docs/:kind/:docId', `/projects/PRJ/docs/specifications/${docDetail.id}`, <DocumentDetail />)
  },
  design: () => {
    vi.mocked(client.designsApi.get).mockResolvedValue({ ...design, content_json: richContent } as never)
    renderAt('/projects/:prefix/designs/:itemId', `/projects/PRJ/designs/${design.id}`, <ArtefactDetail kind="design" />)
  },
  risk: () => {
    vi.mocked(client.risksApi.get).mockResolvedValue({ ...risk, content_json: richContent } as never)
    renderAt('/projects/:prefix/risks/:itemId', `/projects/PRJ/risks/${risk.id}`, <ArtefactDetail kind="risk" />)
  },
  change: () => {
    vi.mocked(client.changesApi.get).mockResolvedValue({ ...change, content_json: richContent } as never)
    renderAt('/projects/:prefix/changes/:itemId', `/projects/PRJ/changes/${change.id}`, <ArtefactDetail kind="change" />)
  },
  'test concept': () => {
    vi.mocked(client.testConceptsApi.get).mockResolvedValue({ ...testConcept, content_json: richContent } as never)
    renderAt('/projects/:prefix/test-concepts/:itemId', `/projects/PRJ/test-concepts/${testConcept.id}`, <ArtefactDetail kind="test-concept" />)
  },
}

const sidePanelPages: Record<string, () => void> = {
  suite: () => { renderAt('/projects/:prefix/suites/:suiteId', `/projects/PRJ/suites/${testSuite.suite_id}`, <SuiteDetail />) },
  campaign: () => { renderAt('/projects/:prefix/campaigns/:campaignId', '/projects/PRJ/campaigns/PRJ-CMP-001', <CampaignDetail />) },
  defect: () => { renderAt('/projects/:prefix/defects/:itemId', `/projects/PRJ/defects/${defect.id}`, <ArtefactDetail kind="defect" />) },
}

beforeEach(() => {
  vi.clearAllMocks()
  resetApiMocks(client as unknown as Record<string, unknown>, vi)
  vi.mocked(client.artefactsApi.getRelated).mockResolvedValue({ ...artefactRelated, project: { id: project.id, prefix: project.prefix, name: project.name } } as never)
})

afterEach(() => {
  cleanup()
})

const detailSections: Record<string, [string, string[]]> = {
  requirement: ['Details', ['Type', 'Priority']],
  'test case': ['Last Execution', ['Result', 'Executed', 'Bud Run']],
  document: ['Details', ['Version']],
  design: ['Details', ['Priority']],
  risk: ['Details', ['Category', 'Severity', 'Probability']],
  change: ['Details', ['Change Type', 'Priority']],
  'test concept': ['Details', ['Coverage']],
}

const METADATA_LABELS = ['Origin', 'ID', 'Project', 'Created', 'Updated']

describe('the layout of a rich-text document page', () => {
  beforeEach(() => {
    localStorage.removeItem('bloom-document-info-collapsed')
  })

  it.each(Object.keys(richPages))('puts the %s comments in a 380 px column before the content below 1024 px and beside it from 1024 px', async page => {
    richPages[page]()
    const aside = await screen.findByRole('complementary', { name: 'Document comments column' })
    expect(within(aside).getByRole('region', { name: 'Document comments' })).toBeTruthy()
    const column = aside.parentElement!
    expect(column.classList.contains('order-first')).toBe(true)
    expect(column.classList.contains('lg:order-last')).toBe(true)
    const grid = column.parentElement!
    expect(grid.classList.contains('grid-cols-1')).toBe(true)
    expect(grid.classList.contains('lg:grid-cols-[minmax(0,1fr)_380px]')).toBe(true)
    const contentColumn = grid.firstElementChild!
    expect(contentColumn).not.toBe(column)
    expect(within(contentColumn as HTMLElement).getByTestId('doc-editor')).toBeTruthy()
    expect(within(column).queryByTestId('doc-editor')).toBeNull()
    expect(screen.queryByRole('complementary', { name: 'Document side panel' })).toBeNull()
  })

  it.each(Object.keys(richPages))('shows the %s workflow, details and metadata in one open panel above the comments, beside the content', async page => {
    richPages[page]()
    const panel = await screen.findByRole('complementary', { name: 'Document information' })
    const comments = screen.getByRole('complementary', { name: 'Document comments column' })
    expect(panel.parentElement).toBe(comments.parentElement)
    expect(panel.compareDocumentPosition(comments) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(panel.contains(screen.getByTestId('doc-editor'))).toBe(false)

    const workflow = within(panel).getByRole('region', { name: 'Workflow state' })
    const review = await within(workflow).findByRole('region', { name: 'Document review' })
    expect(within(review).getByRole('button', { name: 'Details' }).getAttribute('aria-expanded')).toBe('false')

    const [detailTitle, detailLabels] = detailSections[page]
    const details = within(panel).getByRole('region', { name: detailTitle })
    for (const label of detailLabels) expect(within(details).getByText(label)).toBeTruthy()
    expect(within(details).queryByText('Design Type')).toBeNull()
    expect(within(panel).queryByRole('heading', { name: 'Workflow state' })).toBeNull()
    expect(screen.queryByRole('heading', { name: 'Content' })).toBeNull()

    const metadata = within(panel).getByRole('region', { name: 'Metadata' })
    for (const label of METADATA_LABELS) expect(within(metadata).getByText(label)).toBeTruthy()
    expect(await within(metadata).findByText('PRJ · Demo')).toBeTruthy()
  })

  it.each(Object.keys(richPages))('shows the %s workflow, details and metadata only once and nothing between the title and the content', async page => {
    richPages[page]()
    const panel = await screen.findByRole('complementary', { name: 'Document information' })
    await within(panel).findByRole('region', { name: 'Document review' })
    expect(screen.getAllByRole('region', { name: 'Document review' })).toHaveLength(1)
    expect(screen.getAllByRole('region', { name: 'Metadata' })).toHaveLength(1)
    expect(screen.queryByRole('heading', { name: 'Metadata', level: 3 })?.closest('aside')).toBe(panel)
    expect(screen.getAllByText('Created')).toHaveLength(1)
    expect(screen.getAllByText('Updated')).toHaveLength(1)
    const [detailTitle] = detailSections[page]
    expect(screen.getAllByRole('heading', { name: detailTitle })).toHaveLength(1)
    expect(screen.queryByRole('region', { name: 'Document discussion' })).toBeNull()
    const titleBlock = screen.getByRole('heading', { level: 2 }).closest('.animate-fade-in > div')!
    const body = titleBlock.nextElementSibling as HTMLElement
    expect(body.contains(screen.getByTestId('doc-editor'))).toBe(true)
    expect(body.nextElementSibling).toBeNull()
  })

  it.each(Object.keys(richPages))('hides and shows the %s information panel with a button and remembers the choice', async page => {
    richPages[page]()
    const panel = await screen.findByRole('complementary', { name: 'Document information' })
    fireEvent.click(within(panel).getByRole('button', { name: 'Hide document information' }))
    const hidden = screen.getByRole('complementary', { name: 'Document information' })
    expect(within(hidden).queryByRole('region', { name: 'Metadata' })).toBeNull()
    expect(within(hidden).queryByRole('region', { name: 'Document review' })).toBeNull()
    expect(localStorage.getItem('bloom-document-info-collapsed')).toBe('true')
    expect(screen.getByRole('complementary', { name: 'Document comments column' })).toBeTruthy()

    fireEvent.click(within(hidden).getByRole('button', { name: 'Show document information' }))
    expect(within(screen.getByRole('complementary', { name: 'Document information' })).getByRole('region', { name: 'Metadata' })).toBeTruthy()
    expect(localStorage.getItem('bloom-document-info-collapsed')).toBe('false')
  })

  it('opens the panel hidden when the reader hid it before', async () => {
    localStorage.setItem('bloom-document-info-collapsed', 'true')
    richPages.requirement()
    const panel = await screen.findByRole('complementary', { name: 'Document information' })
    expect(within(panel).getByRole('button', { name: 'Show document information' }).getAttribute('aria-expanded')).toBe('false')
    expect(within(panel).queryByRole('region', { name: 'Metadata' })).toBeNull()
  })

  it('keeps the requirement test runs below the content in the main column', async () => {
    const run = { id: 1, test_run_id: 77, test_run_name: 'Nightly run', status: 'Passed', teststation_url: null, created_at: '2026-10-11T00:00:00Z' }
    vi.mocked(client.requirementsApi.get).mockResolvedValue({ ...requirement, content_json: richContent, linked_test_runs: [run] } as never)
    renderAt('/projects/:prefix/requirements/:itemId', `/projects/PRJ/requirements/${requirement.id}`, <RequirementDetail />)
    const aside = await screen.findByRole('complementary', { name: 'Document comments column' })
    const contentColumn = aside.parentElement!.parentElement!.firstElementChild as HTMLElement
    const runs = await within(contentColumn).findByRole('heading', { name: 'Test runs' })
    expect(screen.getByTestId('doc-editor').compareDocumentPosition(runs) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })
})

describe('the layout of a page without rich content', () => {
  it.each(Object.keys(sidePanelPages))('keeps the %s side panel with its discussion', async page => {
    sidePanelPages[page]()
    const panel = await screen.findByRole('complementary', { name: 'Document side panel' })
    expect(await within(panel).findByRole('region', { name: 'Document discussion' })).toBeTruthy()
    expect(screen.queryByRole('complementary', { name: 'Document comments column' })).toBeNull()
    expect(screen.queryByRole('region', { name: 'Document comments' })).toBeNull()
    expect(screen.queryByRole('button', { name: 'Details' })).toBeNull()
    expect(screen.queryByRole('complementary', { name: 'Document information' })).toBeNull()
  })
})
