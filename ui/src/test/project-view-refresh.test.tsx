// @vitest-environment jsdom
import '@testing-library/jest-dom/vitest'
import { QueryClientProvider, useQuery } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createQueryClient } from '../lib/queryClient'
import { refreshProjectViews } from '../lib/refreshProjectViews'
import { ToastProvider } from '../components/Toast'
import { DOC_TYPE_SLUGS, type DocType } from '../types/doc'
import { docDetail, project, resetApiMocks, user } from './apiFixtures'

vi.mock('../api/client', async importOriginal => {
  const { mockApiModule } = await import('./apiFixtures')
  return mockApiModule(await importOriginal<Record<string, unknown>>(), vi)
})
vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ user, isLoading: false, isAuthenticated: true }),
}))
vi.mock('../components/editor/DocEditor', () => ({ default: () => <div /> }))

const api = await import('../api/client')
const DocCreate = (await import('../pages/DocCreate')).default
const UnifiedDocDetail = (await import('../pages/UnifiedDocDetail')).default
const TestCampaigns = (await import('../pages/TestCampaigns')).default
const Defects = (await import('../pages/Defects')).default
const Layout = (await import('../components/Layout')).default
const WorkflowPanel = (await import('../components/WorkflowPanel')).default
const DocumentAttachmentsPanel = (await import('../components/DocumentAttachmentsPanel')).default
const kinds: DocType[] = ['REQ', 'TC', 'DES', 'RSK', 'CHG', 'CPT', 'SPEC', 'PRT', 'RPT', 'STD']
const details: Partial<Record<DocType, string>> = { REQ: 'requirement', TC: 'testCase', DES: 'design', RSK: 'risk', CHG: 'change', CPT: 'testConcept' }
const writes = {
  REQ: api.requirementsApi, TC: api.testCasesApi, DES: api.designsApi,
  RSK: api.risksApi, CHG: api.changesApi, CPT: api.testConceptsApi,
  SPEC: api.documentsApi, PRT: api.documentsApi, RPT: api.documentsApi, STD: api.documentsApi,
}
const allWrites = { ...writes, DEF: api.defectsApi, TS: api.testSuitesApi, CMP: api.campaignsApi }
const allDetails = { ...details, DEF: 'defect', TS: 'testSuite', CMP: 'campaign' }

/** Observe real cached project views while a mutation page is mounted. */
function Views({ calls, prefix = 'VCU', projectId = 1 }: { calls: ReturnType<typeof vi.fn<() => Promise<unknown>>>[]; prefix?: string; projectId?: number }) {
  useQuery({ queryKey: ['all-docs', prefix, 'requirements', 'filter'], queryFn: calls[0] })
  useQuery({ queryKey: ['project-doc-type-summary', prefix], queryFn: calls[1] })
  useQuery({ queryKey: ['traceability', projectId, 'page'], queryFn: calls[2] })
  return null
}

/** Observe the edited record with a query that must disappear after deletion. */
function Detail({ detailKey, fetch }: { detailKey: string; fetch: ReturnType<typeof vi.fn<() => Promise<unknown>>> }) {
  useQuery({ queryKey: [detailKey, 11], queryFn: fetch })
  return null
}

/** Mount a real editor with cached views from two projects. */
async function editor(type: DocType, mode: 'create' | 'edit') {
  const client = createQueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  const calls = Array.from({ length: 3 }, () => vi.fn(async () => []))
  const other = Array.from({ length: 3 }, () => vi.fn(async () => []))
  const detailKey = details[type] || 'document'
  const detailFetch = vi.fn(async () => { throw new Error('Deleted detail fetched again') })
  client.setQueryData(['project-by-prefix', 'VCU'], project)
  client.setQueryData([detailKey, 11], docDetail)
  const docId = `VCU-${type}-001`
  vi.mocked(api.docsApi.get).mockResolvedValue({ ...docDetail, doc_type: type, doc_id: docId } as never)
  vi.mocked(writes[type as keyof typeof writes].get).mockResolvedValue({ ...docDetail, name: docDetail.title, req_id: docId, tc_id: docId, design_id: docId, risk_id: docId, change_id: docId, concept_id: docId, doc_id: docId } as never)
  const path = mode === 'create' ? `/projects/VCU/docs/new?type=${type}` : `/projects/VCU/docs/${DOC_TYPE_SLUGS[type]}/${docId}/edit`
  render(<QueryClientProvider client={client}><ToastProvider><MemoryRouter initialEntries={[path]}>
    <Views calls={calls} /><Views calls={other} prefix="OTHER" projectId={42} />
    <Routes>
      <Route path="/projects/:prefix/docs/new" element={<DocCreate />} />
      <Route path="/projects/:prefix/docs/:kind/:docId/edit" element={<><DocCreate editMode /><Detail detailKey={detailKey} fetch={detailFetch} /></>} />
      <Route path="*" element={<p>List destination</p>} />
    </Routes>
  </MemoryRouter></ToastProvider></QueryClientProvider>)
  const title = await screen.findByPlaceholderText('Untitled')
  if (mode === 'edit') await waitFor(() => expect(title).toHaveValue(docDetail.title))
  fireEvent.change(title, { target: { value: 'Updated title' } })
  await waitFor(() => expect(screen.getByRole('button', { name: /^Save$/ })).toBeEnabled())
  await waitFor(() => calls.forEach(call => expect(call).toHaveBeenCalledTimes(1)))
  await waitFor(() => other.forEach(call => expect(call).toHaveBeenCalledTimes(1)))
  return { client, calls, other, detailFetch, detailKey, facadeFetches: vi.mocked(api.docsApi.get).mock.calls.length }
}

beforeEach(() => {
  vi.clearAllMocks()
  resetApiMocks(api as unknown as Record<string, unknown>, vi)
  window.matchMedia = vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() })) as unknown as typeof window.matchMedia
  window.confirm = () => true
})
afterEach(cleanup)

/** Mount a routed page alongside project views with the production cache defaults. */
async function mountedPage(element: React.ReactElement, path: string, route: string, prepare?: (client: ReturnType<typeof createQueryClient>) => void) {
  const client = createQueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  const calls = Array.from({ length: 3 }, () => vi.fn(async () => []))
  client.setQueryData(['project-by-prefix', 'VCU'], project)
  prepare?.(client)
  render(<QueryClientProvider client={client}><ToastProvider><MemoryRouter initialEntries={[path]}>
    <Views calls={calls} />
    <Routes><Route path={route} element={element} /><Route path="*" element={<p>List destination</p>} /></Routes>
  </MemoryRouter></ToastProvider></QueryClientProvider>)
  await waitFor(() => calls.forEach(call => expect(call).toHaveBeenCalledTimes(1)))
  return { client, calls }
}

describe('native document detail deletion', () => {
  it.each(Object.keys(allWrites) as DocType[])('%s refreshes views without refetching deleted detail', async type => {
    const endpoint = allWrites[type]
    const record = await endpoint.get(0) as unknown as { id: number; project_id: number }
    const detailKey = allDetails[type] || 'document'
    const docId = `VCU-${type}-001`
    const shell = { ...docDetail, id: record.id, doc_type: type, doc_id: docId }
    vi.mocked(api.docsApi.get).mockResolvedValue(shell as never)
    const { client, calls } = await mountedPage(<UnifiedDocDetail />, `/projects/VCU/docs/${DOC_TYPE_SLUGS[type]}/${docId}`, '/projects/:prefix/docs/:kind/:docId', client => {
      client.setQueryData([detailKey, record.id], record)
      client.setQueryData(['doc-facade', 'VCU', DOC_TYPE_SLUGS[type], docId], shell)
    })
    fireEvent.click(await screen.findByRole('button', { name: /^Delete$/ }))
    const buttons = screen.getAllByRole('button', { name: /^Delete$/ })
    fireEvent.click(buttons[buttons.length - 1])
    await screen.findByText('List destination')
    await waitFor(() => calls.forEach(call => expect(call).toHaveBeenCalledTimes(2)))
    expect(endpoint.get).toHaveBeenCalledTimes(1)
    expect(api.docsApi.get).not.toHaveBeenCalled()
    expect(client.getQueryCache().find({ queryKey: [detailKey, record.id], exact: true })).toBeUndefined()
  })
})

describe('dedicated create and update pages', () => {
  it.each(['DEF', 'TS', 'CMP'] as const)('%s create refreshes cached project views', async type => {
    const { calls } = await mountedPage(type === 'DEF' ? <Defects /> : <TestCampaigns />, '/projects/VCU/manage', '/projects/:prefix/manage')
    fireEvent.click(await screen.findByRole('button', { name: type === 'DEF' ? /new defect/i : type === 'TS' ? /new suite/i : /new campaign/i }))
    if (type === 'DEF') {
      fireEvent.change(await screen.findByTitle('Title'), { target: { value: 'Example defect' } })
    } else if (type === 'TS') {
      const heading = await screen.findByText('New Test Suite')
      fireEvent.change(within(heading.parentElement!.parentElement!).getAllByRole('textbox')[0], { target: { value: 'Example suite' } })
      fireEvent.click(screen.getAllByRole('checkbox')[0])
    } else {
      fireEvent.change(await screen.findByPlaceholderText('Campaign name'), { target: { value: 'Example campaign' } })
      fireEvent.click(screen.getAllByRole('checkbox')[0])
    }
    fireEvent.click(screen.getByRole('button', { name: type === 'DEF' ? /^create defect$/i : type === 'TS' ? /^create suite$/i : /^create campaign$/i }))
    await waitFor(() => expect(allWrites[type].create).toHaveBeenCalled())
    await waitFor(() => calls.forEach(call => expect(call).toHaveBeenCalledTimes(2)))
  })

  it.each(['DEF', 'TS', 'CMP'] as const)('%s update refreshes cached project views', async type => {
    const record = await allWrites[type].get(0) as unknown as { id: number }
    const shell = { ...docDetail, id: record.id, doc_type: type, doc_id: `VCU-${type}-001` }
    vi.mocked(api.docsApi.get).mockResolvedValue(shell as never)
    const { calls } = await mountedPage(<UnifiedDocDetail />, `/projects/VCU/docs/${DOC_TYPE_SLUGS[type]}/${shell.doc_id}`, '/projects/:prefix/docs/:kind/:docId', client => {
      client.setQueryData([allDetails[type], record.id], record)
      client.setQueryData(['doc-facade', 'VCU', DOC_TYPE_SLUGS[type], shell.doc_id], shell)
    })
    fireEvent.click(await screen.findByRole('button', { name: /^edit$/i }))
    const save = await screen.findByRole('button', { name: type === 'DEF' ? /^save changes$/i : /^save$/i })
    fireEvent.change(within(save.closest('form')!).getAllByRole('textbox')[0], { target: { value: 'Updated name' } })
    fireEvent.click(save)
    await waitFor(() => expect(allWrites[type].update).toHaveBeenCalled())
    await waitFor(() => calls.forEach(call => expect(call).toHaveBeenCalledTimes(2)))
  })
})

describe('project views after real editor changes', () => {
  it.each(kinds)('%s create refreshes mounted project views', async type => {
    const { calls, other } = await editor(type, 'create')
    fireEvent.click(screen.getByRole('button', { name: /^Save$/ }))
    await waitFor(() => expect(writes[type as keyof typeof writes].create).toHaveBeenCalled())
    await waitFor(() => calls.forEach(call => expect(call).toHaveBeenCalledTimes(2)))
    other.forEach(call => expect(call).toHaveBeenCalledTimes(1))
  })

  it.each(kinds)('%s update refreshes mounted project views', async type => {
    const { calls, other } = await editor(type, 'edit')
    fireEvent.click(screen.getByRole('button', { name: /^Save$/ }))
    await waitFor(() => expect(writes[type as keyof typeof writes].update).toHaveBeenCalled())
    await waitFor(() => calls.forEach(call => expect(call).toHaveBeenCalledTimes(2)))
    other.forEach(call => expect(call).toHaveBeenCalledTimes(1))
  })

  it.each(kinds)('%s deletion unmounts before removing detail and refreshing views', async type => {
    const { calls, other, client, detailFetch, detailKey, facadeFetches } = await editor(type, 'edit')
    fireEvent.click(screen.getByRole('button', { name: /^Delete$/ }))
    await screen.findByText('List destination')
    await waitFor(() => calls.forEach(call => expect(call).toHaveBeenCalledTimes(2)))
    expect(client.getQueryCache().find({ queryKey: [detailKey, 11], exact: true })).toBeUndefined()
    expect(api.docsApi.get).toHaveBeenCalledTimes(facadeFetches)
    expect(detailFetch).not.toHaveBeenCalled()
    other.forEach(call => expect(call).toHaveBeenCalledTimes(1))
  })

  it('failed saves refresh nothing', async () => {
    const { calls, other } = await editor('REQ', 'edit')
    vi.mocked(api.requirementsApi.update).mockRejectedValueOnce(new Error('Save refused'))
    fireEvent.click(screen.getByRole('button', { name: /^Save$/ }))
    await screen.findAllByText('Save refused')
    calls.forEach(call => expect(call).toHaveBeenCalledTimes(1))
    other.forEach(call => expect(call).toHaveBeenCalledTimes(1))
  })
})

describe('shared project refresh', () => {
  it('attachment uploads refresh project views while project metadata is unavailable', async () => {
    vi.mocked(api.projectsApi.getByPrefix).mockImplementation(() => new Promise(() => {}))
    const { client, calls } = await mountedPage(<DocumentAttachmentsPanel documentId={31} docType="SPEC" projectId={1} />, '/projects/VCU/manage', '/projects/:prefix/manage', client => client.removeQueries({ queryKey: ['project-by-prefix', 'VCU'] }))
    const input = document.querySelector('input[type="file"]')!
    fireEvent.change(input, { target: { files: [new File(['sample'], 'example.txt', { type: 'text/plain' })] } })
    await waitFor(() => expect(api.attachmentsApi.upload).toHaveBeenCalled())
    await waitFor(() => calls.forEach(call => expect(call).toHaveBeenCalledTimes(2)))
    expect(client.getQueryData(['project-by-prefix', 'VCU'])).toBeUndefined()
    client.clear()
  })
  it('workflow comments refresh project views without cached project metadata', async () => {
    const { client, calls } = await mountedPage(<WorkflowPanel artefactType="requirement" artefactId={11} projectPrefix="VCU" projectId={1} />, '/projects/VCU/manage', '/projects/:prefix/manage')
    client.removeQueries({ queryKey: ['project-by-prefix', 'VCU'] })
    const discussion = await screen.findByRole('region', { name: 'Document discussion' })
    fireEvent.change(await within(discussion).findByRole('textbox', { name: 'Comment' }), { target: { value: 'Review comment' } })
    fireEvent.click(within(discussion).getByRole('button', { name: /^Comment$/ }))
    await waitFor(() => expect(api.artefactsApi.createComment).toHaveBeenCalled())
    await waitFor(() => calls.forEach(call => expect(call).toHaveBeenCalledTimes(2)))
  })
  it('marks a retired project prefix stale without refetching its old URL', async () => {
    const { client, calls } = await mountedPage(<p>Renamed project</p>, '/projects/VCU/manage', '/projects/:prefix/manage')
    refreshProjectViews(client, { prefix: 'VCU', projectId: 1 }, 'none')
    calls.forEach(call => expect(call).toHaveBeenCalledTimes(1))
    expect(client.getQueryState(['all-docs', 'VCU', 'requirements', 'filter'])?.isInvalidated).toBe(true)
  })
  it('marking notifications read does not refetch project views', async () => {
    vi.mocked(api.notificationsApi.unreadCount).mockResolvedValue(1)
    const { calls } = await mountedPage(<Layout />, '/projects/VCU/manage', '/projects/:prefix/manage')
    fireEvent.click(await screen.findByRole('button', { name: /^Notifications/ }))
    fireEvent.click(await screen.findByRole('button', { name: /mark all read/i }))
    await waitFor(() => expect(api.notificationsApi.unreadCount).toHaveBeenCalledTimes(2))
    expect(api.notificationsApi.markAllRead).toHaveBeenCalledTimes(1)
    calls.forEach(call => expect(call).toHaveBeenCalledTimes(1))
  })
  it('a different project save does not refetch mounted project views', async () => {
    const { client, calls } = await mountedPage(<p>Another project</p>, '/projects/VCU/manage', '/projects/:prefix/manage')
    refreshProjectViews(client, { prefix: 'OTHER', projectId: 42 })
    calls.forEach(call => expect(call).toHaveBeenCalledTimes(1))
  })
  it('marks hidden filtered views stale without fetching until they mount', async () => {
    const client = createQueryClient()
    const calls = Array.from({ length: 3 }, () => vi.fn(async () => []))
    await client.prefetchQuery({ queryKey: ['all-docs', 'VCU', 'requirements', 'filter'], queryFn: calls[0] })
    await client.prefetchQuery({ queryKey: ['project-doc-type-summary', 'VCU'], queryFn: calls[1] })
    await client.prefetchQuery({ queryKey: ['traceability', 1, 'page'], queryFn: calls[2] })
    refreshProjectViews(client, { prefix: 'VCU', projectId: 1 })
    calls.forEach(call => expect(call).toHaveBeenCalledTimes(1))
    render(<QueryClientProvider client={client}><Views calls={calls} /></QueryClientProvider>)
    await waitFor(() => calls.forEach(call => expect(call).toHaveBeenCalledTimes(2)))
  })

  it('does not wait for active refetches', async () => {
    const client = createQueryClient()
    const calls = Array.from({ length: 3 }, () => vi.fn(async () => []))
    client.setQueryData(['project-by-prefix', 'VCU'], project)
    render(<QueryClientProvider client={client}><Views calls={calls} /></QueryClientProvider>)
    await waitFor(() => calls.forEach(call => expect(call).toHaveBeenCalledTimes(1)))
    calls.forEach(call => call.mockImplementation(() => new Promise(() => {})))
    expect(refreshProjectViews(client, { prefix: 'VCU' })).toBeUndefined()
    await waitFor(() => calls.forEach(call => expect(call).toHaveBeenCalledTimes(2)))
    client.clear()
  })
})
