// @vitest-environment jsdom
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import type { ReactElement } from 'react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ToastProvider } from '../components/Toast'
import { getBreadcrumbs } from '../lib/breadcrumbs'
import { docRegistryListLabel } from '../lib/docRegistryParams'
import { resourceLabel } from '../lib/policySummary'
import { createQueryClient } from '../lib/queryClient'
import { visionStage } from '../lib/visionStage'
import { isServerAssignedDocIdOnCreate } from '../pages/docCreateIdPolicy'
import {
  DOC_TYPE_LABELS,
  getDocLinkOptions,
  isDocLinkRoleAllowed,
  isDocTagTargetAllowed,
  isWorkflowControlledDocType,
} from '../types/doc'
import { docDetail, resetApiMocks, user, workflowFixture } from './apiFixtures'

vi.mock('../api/client', async importOriginal => {
  const { mockApiModule } = await import('./apiFixtures')
  return mockApiModule(await importOriginal<Record<string, unknown>>(), vi)
})

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ user, isLoading: false, isAuthenticated: true }),
}))

vi.mock('../hooks/useDarkMode', () => ({
  useDarkMode: () => [false, vi.fn()] as const,
}))

vi.mock('../components/ProjectDocTopology', () => ({
  default: () => <div data-testid="project-topology" />,
}))

vi.mock('../components/editor/DocEditor', () => ({
  default: () => <div data-testid="doc-editor" />,
}))

const client = await import('../api/client')
const DocumentDetail = (await import('../pages/DocumentDetail')).default
const Layout = (await import('../components/Layout')).default
const ProjectDetail = (await import('../pages/ProjectDetail')).default
const Documents = (await import('../pages/Documents')).default
const { DocumentLinksPanel } = await import('../components/DocumentLinksPanel')

const approvedRevision = { revision_number: 1, captured_at: '2026-10-27T10:00:00Z', approved_by: user, approved_at: '2026-10-27T10:00:00Z', authorizing_change_id: null }

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

/** Open a shared document of the given type with the given workflow. */
async function openDocument(docType: string, slug: string, workflow: object) {
  vi.mocked(client.documentsApi.get).mockResolvedValue({ ...docDetail, doc_type: docType, doc_id: `PRJ-${docType}-001` } as never)
  vi.mocked(client.workflowApi.get).mockResolvedValue({ ...workflowFixture, ...workflow } as never)
  renderAt('/projects/:prefix/docs/:kind/:docId', `/projects/PRJ/docs/${slug}/${docDetail.id}`, <DocumentDetail />)
  await screen.findAllByText(`PRJ-${docType}-001`)
}

/** The outgoing link roles the picker offers from one type to another. */
function outgoingRoles(source: 'REQ' | 'SPEC' | 'CHG' | 'RSK' | 'VIS', target: 'VIS' | 'STD') {
  return getDocLinkOptions(source, target).filter(option => option.displayDirection === 'outgoing').map(option => option.role)
}

beforeEach(() => resetApiMocks(client as unknown as Record<string, unknown>, vi))
afterEach(cleanup)

describe('the Visions type', () => {
  it('is a controlled document type named Vision, collected as Visions', () => {
    expect(DOC_TYPE_LABELS.VIS).toBe('Vision')
    expect(docRegistryListLabel('VIS')).toBe('Visions')
    expect(isWorkflowControlledDocType('VIS')).toBe(true)
    expect(isServerAssignedDocIdOnCreate('VIS')).toBe(true)
    expect(resourceLabel('VIS')).toBe('VIS · Visions')
    const crumbs = getBreadcrumbs('/projects/PRJ/docs/new', '?type=visions', [{ id: 1, name: 'Demo', prefix: 'PRJ' }])
    expect(crumbs[crumbs.length - 1]).toEqual({
      label: 'Visions',
      href: '/projects/PRJ/docs?type=visions',
      emphasize: true,
    })
  })

  it('lists Visions first among the document types in the project sidebar', async () => {
    const queryClient = createQueryClient({ defaultOptions: { queries: { retry: false } } })
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/projects/PRJ']}>
          <Layout />
        </MemoryRouter>
      </QueryClientProvider>,
    )
    const visions = await screen.findByRole('link', { name: 'Visions' })
    const requirements = screen.getByRole('link', { name: 'Requirements' })
    expect(visions.compareDocumentPosition(requirements) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('links only through its manual rows, and takes and gives tags', () => {
    expect(outgoingRoles('REQ', 'VIS')).toEqual(['derives_from', 'refines', 'references'])
    expect(outgoingRoles('SPEC', 'VIS')).toEqual(['derives_from', 'refines', 'references'])
    expect(outgoingRoles('CHG', 'VIS')).toEqual(['impacts', 'implements', 'blocks', 'references'])
    expect(outgoingRoles('RSK', 'VIS')).toEqual(['impacts', 'references'])
    expect(outgoingRoles('VIS', 'STD')).toEqual(['references'])
    expect(isDocLinkRoleAllowed('DES', 'VIS', 'satisfies')).toBe(false)
    expect(isDocLinkRoleAllowed('VIS', 'REQ', 'derives_from')).toBe(false)
    expect(isDocTagTargetAllowed('VIS', 'REQ')).toBe(true)
    expect(isDocTagTargetAllowed('REQ', 'VIS')).toBe(true)
  })
})

describe('Idea or Binding', () => {
  it.each([
    ['never approved', { phase: 'Draft', revision_number: 1, revisions: [] }, 'Idea'],
    ['approved', { phase: 'Approved', revision_number: 1, revisions: [approvedRevision] }, 'Binding'],
    ['revision 2 in Draft', { phase: 'Draft', revision_number: 2, revisions: [] }, 'Binding'],
    ['a correction the viewer may see', { phase: 'Draft', revision_number: 1, revisions: [approvedRevision] }, 'Binding'],
    ['a correction the viewer may not see', { phase: 'Draft', revision_number: 1, revisions: [] }, 'Idea'],
  ])('reads %s as the label', (_case, workflow, label) => {
    expect(visionStage(workflow as never)).toBe(label)
  })

  it('reads Idea while the workflow is not loaded', () => {
    expect(visionStage(undefined)).toBe('Idea')
  })

  it('shows Idea on a vision that was never approved', async () => {
    await openDocument('VIS', 'visions', { phase: 'Draft', revisions: [] })
    expect(await screen.findByText('Idea')).toBeTruthy()
    expect(screen.queryByText('Binding')).toBeNull()
  })

  it('shows Binding on an approved vision', async () => {
    await openDocument('VIS', 'visions', { phase: 'Approved', revisions: [approvedRevision] })
    expect(await screen.findByText('Binding')).toBeTruthy()
    expect(screen.queryByText('Idea')).toBeNull()
  })

  it('shows neither label on a specification', async () => {
    await openDocument('SPEC', 'specifications', { phase: 'Approved', revisions: [approvedRevision] })
    expect(screen.queryByText('Binding')).toBeNull()
    expect(screen.queryByText('Idea')).toBeNull()
  })
})

describe('Visions in the project pages', () => {
  it('links to Visions first on the project overview', async () => {
    renderAt('/projects/:prefix', '/projects/PRJ', <ProjectDetail />)
    const visions = await screen.findByRole('link', { name: /Visions/ }, { timeout: 4000 })
    expect(visions.getAttribute('href')).toBe('/projects/PRJ/docs?type=visions')
    const protocols = screen.getByRole('link', { name: /Protocols/ })
    expect(visions.compareDocumentPosition(protocols) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('offers VIS first in the registry Kind filter', async () => {
    renderAt('/projects/:prefix/docs', '/projects/PRJ/docs', <Documents />)
    fireEvent.click(await screen.findByRole('button', { name: /Filters/ }))
    const kinds = await screen.findAllByRole('button', { name: /^(VIS|REQ|SPEC|STD)$/ })
    expect(kinds.map((button) => button.textContent)).toEqual(['VIS', 'REQ', 'SPEC', 'STD'])
  })

  it.each([
    ['REQ', 'Visions'],
    ['VIS', 'Standards'],
  ])('offers the right target in the links panel of a %s', async (sourceType, target) => {
    vi.mocked(client.docsApi.typeSummary).mockResolvedValue({
      types: [
        { doc_type: 'VIS', count: 1, suspect_links: 0 },
        { doc_type: 'STD', count: 1, suspect_links: 0 },
        { doc_type: 'DES', count: 1, suspect_links: 0 },
      ],
      total: 3,
      membership_edges: [],
    } as never)
    renderAt('/', '/', <DocumentLinksPanel projectId={1} projectPrefix="PRJ" sourceType={sourceType} sourceId={21} sourceDocId={`PRJ-${sourceType}-001`} />)
    fireEvent.click(await screen.findByRole('button', { name: /link artefact/i }))
    const picker = await screen.findByRole('combobox', { name: 'Target artefact kind' })
    await waitFor(() => expect(picker.hasAttribute('disabled')).toBe(false))
    fireEvent.click(picker)
    const options = (await screen.findAllByRole('option')).map((option) => option.textContent?.trim())
    expect(options).toContain(target)
  })
})
