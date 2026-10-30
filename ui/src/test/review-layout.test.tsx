// @vitest-environment jsdom
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, within } from '@testing-library/react'
import type { ReactElement } from 'react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ToastProvider } from '../components/Toast'
import { createQueryClient } from '../lib/queryClient'
import { change, defect, design, docDetail, requirement, resetApiMocks, risk, testCase, testConcept, testSuite, user } from './apiFixtures'

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
    vi.mocked(client.testCasesApi.get).mockResolvedValue({ ...testCase, content_json: richContent } as never)
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
  suite: () => { renderAt('/projects/:prefix/suites/:suiteId', `/projects/PRJ/suites/${testSuite.id}`, <SuiteDetail />) },
  campaign: () => { renderAt('/projects/:prefix/campaigns/:campaignId', '/projects/PRJ/campaigns/51', <CampaignDetail />) },
  defect: () => { renderAt('/projects/:prefix/defects/:itemId', `/projects/PRJ/defects/${defect.id}`, <ArtefactDetail kind="defect" />) },
}

beforeEach(() => {
  vi.clearAllMocks()
  resetApiMocks(client as unknown as Record<string, unknown>, vi)
})

afterEach(() => {
  cleanup()
})

describe('the layout of a rich-text document page', () => {
  it.each(Object.keys(richPages))('puts the %s comments in a 380 px column before the content below 1024 px and beside it from 1024 px', async page => {
    richPages[page]()
    const aside = await screen.findByRole('complementary', { name: 'Document comments column' })
    expect(within(aside).getByRole('region', { name: 'Document comments' })).toBeTruthy()
    expect(aside.classList.contains('order-first')).toBe(true)
    expect(aside.classList.contains('lg:order-last')).toBe(true)
    const grid = aside.parentElement!
    expect(grid.classList.contains('grid-cols-1')).toBe(true)
    expect(grid.classList.contains('lg:grid-cols-[minmax(0,1fr)_380px]')).toBe(true)
    const contentColumn = grid.firstElementChild!
    expect(contentColumn).not.toBe(aside)
    expect(within(contentColumn as HTMLElement).getByTestId('doc-editor')).toBeTruthy()
    expect(within(aside).queryByTestId('doc-editor')).toBeNull()
    expect(screen.queryByRole('complementary', { name: 'Document side panel' })).toBeNull()
  })

  it.each(Object.keys(richPages))('shows the %s review bar with Details above the content and the comments', async page => {
    richPages[page]()
    const aside = await screen.findByRole('complementary', { name: 'Document comments column' })
    await screen.findByRole('button', { name: 'Details' })
    const review = screen.getByRole('region', { name: 'Document review' })
    expect(within(review).getByRole('button', { name: 'Details' }).getAttribute('aria-expanded')).toBe('false')
    expect(aside.contains(review)).toBe(false)
    expect(review.compareDocumentPosition(aside.parentElement!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(review.compareDocumentPosition(screen.getByTestId('doc-editor')) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(screen.queryByRole('region', { name: 'Document discussion' })).toBeNull()
  })

  it('moves the requirement metadata and test runs below the content in the main column', async () => {
    richPages.requirement()
    const aside = await screen.findByRole('complementary', { name: 'Document comments column' })
    const contentColumn = aside.parentElement!.firstElementChild as HTMLElement
    const metadata = await within(contentColumn).findByRole('heading', { name: 'Metadata' })
    expect(screen.getByTestId('doc-editor').compareDocumentPosition(metadata) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(within(aside).queryByRole('heading', { name: 'Metadata' })).toBeNull()
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
  })
})
