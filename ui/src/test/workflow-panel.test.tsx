// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ToastProvider } from '../components/Toast'
import { RESPONSES, change, defect, docDetail, requirement, resetApiMocks, testCase, testSuite, user } from './apiFixtures'

let currentUser = { ...user, role: 'maintainer' as 'admin' | 'maintainer' | 'external' }
const reviewer = { ...user, id: 2, full_name: 'Grace Hopper', email: 'grace@example.com', role: 'maintainer' as const }
const approver = { ...user, id: 3, full_name: 'Charles Babbage', email: 'charles@example.com', role: 'maintainer' as const }

vi.mock('../api/client', async (importOriginal) => {
  const { mockApiModule } = await import('./apiFixtures')
  return mockApiModule(await importOriginal<Record<string, unknown>>(), vi)
})

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ user: currentUser, isLoading: false, isAuthenticated: true }),
}))

const client = await import('../api/client')
const RequirementDetail = (await import('../pages/RequirementDetail')).default
const TestCaseDetail = (await import('../pages/TestCaseDetail')).default
const DocumentDetail = (await import('../pages/DocumentDetail')).default
const ArtefactDetail = (await import('../pages/ArtefactDetail')).default
const DocCreate = (await import('../pages/DocCreate')).default
const SuiteDetail = (await import('../pages/SuiteDetail')).default

const workflowState = {
  controlled: true, revision_number: 1, phase: 'Draft', status: 'Draft', creator: user,
  reviewer, approver, reviewed_by: null, reviewed_at: null, approved_by: null, approved_at: null,
  authorizing_change: null, options: { reviewers: [reviewer], approvers: [approver], changes: [] },
  actions: { request_review: false, request_approval: false, approve: false, decline: false, assign_reviewer: false, assign_approver: false, comment: false, start_revision: false, start_draft: false, edit_current: true, plan_current: true },
  pending_request: null, last_request: null, revisions: [],
}

function renderAt(path: string, url: string, element: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } },
  })
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

function renderAssignedDocument(type: 'REQ' | 'TC', status: 'Draft' | 'Review' | 'Approved') {
  const record = {
    ...(RESPONSES[type === 'REQ' ? 'requirementsApi.get' : 'testCasesApi.get'] as object),
    status,
    created_by_id: user.id,
    reviewer_id: reviewer.id,
    approver_id: approver.id,
    reviewed_by_id: null,
    reviewed_at: null,
    approved_by_id: null,
    approved_at: null,
  }
  if (type === 'REQ') {
    vi.mocked(client.requirementsApi.get).mockResolvedValue(record as never)
    return renderAt('/projects/:prefix/requirements/:itemId', `/projects/VCU/requirements/${requirement.id}`, <RequirementDetail allowedActions={['edit', 'review', 'approve']} />)
  }
  vi.mocked(client.testCasesApi.get).mockResolvedValue(record as never)
  return renderAt('/projects/:prefix/test-cases/:itemId', `/projects/VCU/test-cases/${testCase.id}`, <TestCaseDetail allowedActions={['edit', 'review', 'approve']} />)
}

beforeEach(() => {
  vi.clearAllMocks()
  resetApiMocks(client as unknown as Record<string, unknown>, vi)
  currentUser = { ...user, role: 'maintainer' }
  vi.mocked(client.projectMembersApi.permissions).mockResolvedValue({ '*': ['view', 'create', 'edit', 'review', 'approve'] })
  vi.mocked(client.usersApi.listMentionable).mockResolvedValue([user, reviewer, approver])
  vi.mocked(client.workflowApi.get).mockResolvedValue(workflowState)
  window.confirm = () => true
})

afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe('controlled document handoffs', () => {
  it.each(['REQ', 'TC'] as const)('lets the creator request review of an assigned Draft %s', async (type) => {
    vi.mocked(client.workflowApi.get).mockResolvedValue({ ...workflowState, actions: { ...workflowState.actions, request_review: true } })
    renderAssignedDocument(type, 'Draft')
    const action = await screen.findByRole('button', { name: /^request review$/i })
    expect(screen.getByRole('heading', { name: 'Review' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Approval' })).toBeTruthy()
    expect(screen.queryByRole('heading', { name: 'Workflow' })).toBeNull()
    expect(screen.queryByText(/Creator:/)).toBeNull()
    expect(screen.getByText(/Draft · Revision 1/)).toBeTruthy()
    expect(action.classList.contains('bg-amber-500/90')).toBe(true)
    expect(screen.getByRole('button', { name: /^mark approved$/i }).classList.contains('bg-emerald-600')).toBe(true)
    expect((action as HTMLButtonElement).disabled).toBe(false)
    expect((screen.getByRole('button', { name: /^mark reviewed$/i }) as HTMLButtonElement).disabled).toBe(true)
    expect((screen.getByRole('button', { name: /^mark approved$/i }) as HTMLButtonElement).disabled).toBe(true)
    fireEvent.click(action)
    await waitFor(() => expect(client.workflowApi.request).toHaveBeenCalledWith(type === 'REQ' ? 'requirement' : 'test-case', type === 'REQ' ? requirement.id : testCase.id, 'review'))
  })

  it.each(['REQ', 'TC'] as const)('lets the assigned reviewer comment on a %s before requesting approval', async (type) => {
    currentUser = reviewer
    vi.mocked(client.workflowApi.get).mockResolvedValueOnce({ ...workflowState, phase: 'Review', actions: { ...workflowState.actions, comment: true } }).mockResolvedValue({ ...workflowState, phase: 'Review', actions: { ...workflowState.actions, comment: true, request_approval: true } })
    renderAssignedDocument(type, 'Review')
    fireEvent.click(await screen.findByRole('button', { name: /^comments$/i }))
    expect((screen.getByRole('button', { name: /^mark reviewed$/i }) as HTMLButtonElement).disabled).toBe(true)
    fireEvent.change(screen.getByRole('textbox', { name: 'Comment' }), { target: { value: 'Reviewed the current content.' } })
    fireEvent.click(screen.getByRole('button', { name: /^post comment$/i }))
    await waitFor(() => expect(client.artefactsApi.createComment).toHaveBeenCalledWith(
      type === 'REQ' ? 'requirement' : 'test-case',
      type === 'REQ' ? requirement.id : testCase.id,
      'Reviewed the current content.',
    ))
    expect((await screen.findByRole('button', { name: /^mark reviewed$/i }) as HTMLButtonElement).disabled).toBe(false)
    fireEvent.click(screen.getByRole('button', { name: /^mark reviewed$/i }))
    await waitFor(() => expect(client.workflowApi.request).toHaveBeenCalledWith(type === 'REQ' ? 'requirement' : 'test-case', type === 'REQ' ? requirement.id : testCase.id, 'approval'))
  })
})

describe('assigned reviewer comment authority', () => {
  it('keeps a visible defect read-only for comments when the administrator is not its assigned reviewer', async () => {
    currentUser = { ...user, role: 'admin' }
    vi.mocked(client.workflowApi.get).mockResolvedValue({ ...workflowState, controlled: false })
    vi.mocked(client.defectsApi.get).mockResolvedValue({ ...defect, reviewer_id: reviewer.id } as never)
    renderAt('/projects/:prefix/defects/:itemId', `/projects/VCU/defects/${defect.id}`, <ArtefactDetail kind="defect" allowedActions={['edit']} />)
    fireEvent.click(await screen.findByRole('button', { name: /^comments$/i }))
    expect(screen.queryByRole('textbox')).toBeNull()
    expect(screen.queryByRole('button', { name: /^post comment$/i })).toBeNull()
    expect(client.artefactsApi.createComment).not.toHaveBeenCalled()
  })
})

describe('approved revision preservation', () => {
  it('offers the normal Edit action for an Approved requirement correction', async () => {
    vi.mocked(client.workflowApi.get).mockResolvedValue({ ...workflowState, phase: 'Approved', status: 'Approved', actions: { ...workflowState.actions, edit_current: true } })
    renderAssignedDocument('REQ', 'Approved')
    await screen.findByRole('heading', { name: requirement.title })
    expect(await screen.findByRole('button', { name: /^edit$/i })).toBeTruthy()
    expect(screen.queryByRole('combobox', { name: 'Approved change request' })).toBeNull()
    expect(screen.queryByRole('button', { name: /^start revision$/i })).toBeNull()
  })

  it('offers revision history for an Approved specification', async () => {
    vi.mocked(client.documentsApi.get).mockResolvedValue({ ...docDetail, doc_type: 'SPEC', doc_id: 'VCU-SPEC-001', status: 'Approved', version: '1.0', sections: [] } as never)
    renderAt('/projects/:prefix/docs/:kind/:docId', `/projects/VCU/docs/specifications/${docDetail.id}`, <DocumentDetail allowedActions={['edit']} />)
    expect(await screen.findByRole('button', { name: /^revision history$/i })).toBeTruthy()
  })

  it('does not expose Edit for an Approved change request', async () => {
    vi.mocked(client.changesApi.get).mockResolvedValue({ ...change, status: 'Approved' } as never)
    vi.mocked(client.workflowApi.get).mockResolvedValue({ ...workflowState, phase: 'Approved', status: 'Approved', actions: { ...workflowState.actions, edit_current: false } })
    renderAt('/projects/:prefix/changes/:itemId', `/projects/VCU/changes/${change.id}`, <ArtefactDetail kind="change" allowedActions={['edit', 'review', 'approve']} />)
    await screen.findByRole('heading', { name: change.title })
    expect(screen.queryByRole('button', { name: /^edit$/i })).toBeNull()
  })

  it('does not expose lifecycle transitions for an Approved change request', async () => {
    vi.mocked(client.changesApi.get).mockResolvedValue({ ...change, status: 'Approved' } as never)
    renderAt('/projects/:prefix/changes/:itemId', `/projects/VCU/changes/${change.id}`, <ArtefactDetail kind="change" allowedActions={['edit', 'review', 'approve']} />)
    await screen.findByRole('heading', { name: change.title })
    expect(screen.queryAllByRole('button', { name: /^move to /i })).toHaveLength(0)
    expect(client.artefactsApi.transition).not.toHaveBeenCalled()
  })
})

describe('controlled creation metadata', () => {
  it.each(['REQ', 'SPEC', 'TC', 'DES', 'CPT', 'PRT', 'CHG'])('offers only Draft for a new %s', async type => {
    vi.mocked(client.tagsApi.scope).mockResolvedValue({ limited: true, tags: [{ id: 4, name: 'Field', created_at: '' }] })
    renderAt('/projects/:prefix/docs/new', `/projects/VCU/docs/new?type=${type}`, <DocCreate />)
    const status = await screen.findByTitle('Select status') as HTMLSelectElement
    expect([...status.options].map(option => option.value)).toEqual(['Draft'])
    await screen.findByRole('button', { name: 'Field' })
    fireEvent.change(screen.getByTitle('Select origin'), { target: { value: type === 'REQ' ? 'Customer' : 'customer' } })
    expect(screen.queryByTitle('Select visibility')).toBeNull()
    expect(screen.getAllByText('Origin', { exact: true })).toHaveLength(1)
    fireEvent.change(screen.getByPlaceholderText('Untitled'), { target: { value: 'Initial Draft' } })
    fireEvent.click(screen.getByRole('button', { name: /^save$/i }))
    const api = type === 'REQ' ? client.requirementsApi : type === 'TC' ? client.testCasesApi : type === 'DES' ? client.designsApi : type === 'CPT' ? client.testConceptsApi : type === 'CHG' ? client.changesApi : client.documentsApi
    await waitFor(() => expect(api.create).toHaveBeenCalled())
    expect(vi.mocked(api.create).mock.calls[0][0]).toMatchObject({ status: 'Draft', visibility: 'customer', tag_ids: [4] })
  })

  it('removes direct status and assignment editing from a controlled writer', async () => {
    vi.mocked(client.docsApi.get).mockResolvedValue({ ...docDetail, doc_type: 'SPEC', status: 'Mitigated', content_json: null, content_html: '' } as never)
    renderAt('/projects/:prefix/docs/:kind/:docId/edit', '/projects/VCU/docs/specifications/VCU-SPEC-001/edit', <DocCreate editMode />)
    await screen.findByDisplayValue(docDetail.title)
    expect(screen.getAllByText('Draft', { exact: true })).toHaveLength(2)
    expect(screen.queryByText('Mitigated')).toBeNull()
    expect(screen.queryByTitle('Select status')).toBeNull()
    expect(screen.queryByRole('combobox', { name: 'Select reviewer' })).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: /^save$/i }))
    await waitFor(() => expect(client.documentsApi.update).toHaveBeenCalled())
    expect(vi.mocked(client.documentsApi.update).mock.calls[0][1]).not.toHaveProperty('status')
    expect(vi.mocked(client.documentsApi.update).mock.calls[0][1]).not.toHaveProperty('reviewer_id')
  })

  it('keeps the writer read-only when the server denies editing', async () => {
    vi.mocked(client.docsApi.get).mockResolvedValue({ ...docDetail, doc_type: 'SPEC', status: 'Approved' } as never)
    vi.mocked(client.workflowApi.get).mockResolvedValue({ ...workflowState, phase: 'Approved', status: 'Approved', actions: { ...workflowState.actions, edit_current: false } })
    renderAt('/projects/:prefix/docs/:kind/:docId/edit', '/projects/VCU/docs/specifications/VCU-SPEC-001/edit', <DocCreate editMode />)
    expect(await screen.findByText('This document is read-only.')).toBeTruthy()
    expect(screen.queryByPlaceholderText('Untitled')).toBeNull()
    expect(screen.queryByRole('button', { name: /^save$/i })).toBeNull()
  })
})

describe('approved document corrections use the existing editor', () => {
  it('saves an approved specification through the normal update API', async () => {
    vi.mocked(client.docsApi.get).mockResolvedValue({ ...docDetail, doc_type: 'SPEC', status: 'Approved', version: '1' } as never)
    vi.mocked(client.workflowApi.get).mockResolvedValue({ ...workflowState, phase: 'Approved', status: 'Approved', actions: { ...workflowState.actions, edit_current: true } })
    renderAt('/projects/:prefix/docs/:kind/:docId/edit', '/projects/VCU/docs/specifications/VCU-SPEC-001/edit', <DocCreate editMode />)
    const title = await screen.findByPlaceholderText('Untitled')
    fireEvent.change(title, { target: { value: 'Corrected specification' } })
    fireEvent.click(screen.getByRole('button', { name: /^save$/i }))
    await waitFor(() => expect(client.documentsApi.update).toHaveBeenCalledWith(docDetail.id, expect.objectContaining({ title: 'Corrected specification' })))
    const payload = vi.mocked(client.documentsApi.update).mock.calls[0][1]
    expect(payload).not.toHaveProperty('version')
    expect(payload).not.toHaveProperty('status')
    expect(payload).not.toHaveProperty('change_request_id')
    expect(client.workflowApi.startRevision).not.toHaveBeenCalled()
  })

  it('discards an approved-document edit without changing content or revision', async () => {
    vi.mocked(client.docsApi.get).mockResolvedValue({ ...docDetail, doc_type: 'SPEC', status: 'Approved' } as never)
    vi.mocked(client.workflowApi.get).mockResolvedValue({ ...workflowState, phase: 'Approved', status: 'Approved', actions: { ...workflowState.actions, edit_current: true } })
    renderAt('/projects/:prefix/docs/:kind/:docId/edit', '/projects/VCU/docs/specifications/VCU-SPEC-001/edit', <DocCreate editMode />)
    const title = await screen.findByPlaceholderText('Untitled')
    fireEvent.change(title, { target: { value: 'Discarded correction' } })
    fireEvent.click(screen.getByRole('button', { name: /^discard$/i }))
    expect(client.documentsApi.update).not.toHaveBeenCalled()
    expect(client.workflowApi.startRevision).not.toHaveBeenCalled()
  })
})

describe('suite planning authority', () => {
  it('allows mutable suite membership with Plan and without Edit', async () => {
    vi.mocked(client.projectMembersApi.permissions).mockResolvedValue({ TS: ['view', 'plan'] })
    vi.mocked(client.workflowApi.get).mockResolvedValue({ ...workflowState, actions: { ...workflowState.actions, edit_current: false, plan_current: true } })
    renderAt('/projects/:prefix/suites/:suiteId', `/projects/VCU/suites/${testSuite.id}`, <SuiteDetail allowedActions={['plan']} />)
    fireEvent.click(await screen.findByRole('button', { name: /^add test case$/i }))
    fireEvent.click(await screen.findByRole('button', { name: new RegExp(testCase.tc_id) }))
    await waitFor(() => expect(client.testSuitesApi.addItem).toHaveBeenCalledWith(testSuite.id, testCase.id))
    expect(screen.queryByRole('button', { name: /^edit$/i })).toBeNull()
  })
})

describe('workflow capability boundaries', () => {
  it.each(['REQ', 'TC', 'DES', 'CPT', 'CHG'] as const)('keeps the %s writer payload free of lifecycle and assignment fields', async type => {
    vi.mocked(client.docsApi.get).mockResolvedValue({ ...docDetail, doc_type: type, status: 'Draft' } as never)
    renderAt('/projects/:prefix/docs/:kind/:docId/edit', `/projects/VCU/docs/documents/VCU-${type}-001/edit`, <DocCreate editMode />)
    await screen.findByPlaceholderText('Untitled')
    expect(screen.queryByTitle('Select status')).toBeNull()
    expect(screen.queryByRole('combobox', { name: 'Select reviewer' })).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: /^save$/i }))
    const api = type === 'REQ' ? client.requirementsApi : type === 'TC' ? client.testCasesApi : type === 'DES' ? client.designsApi : type === 'CPT' ? client.testConceptsApi : client.changesApi
    await waitFor(() => expect(api.update).toHaveBeenCalled())
    expect(vi.mocked(api.update).mock.calls[0][1]).not.toHaveProperty('status')
    expect(vi.mocked(api.update).mock.calls[0][1]).not.toHaveProperty('reviewer_id')
    expect(vi.mocked(api.update).mock.calls[0][1]).not.toHaveProperty('approver_id')
  })

  it('exposes no workflow mutations while the authoritative response is pending', async () => {
    vi.mocked(client.workflowApi.get).mockReturnValue(new Promise(() => {}))
    renderAssignedDocument('REQ', 'Draft')
    await screen.findByRole('heading', { name: requirement.title })
    expect(screen.queryByRole('button', { name: /^edit$/i })).toBeNull()
    expect(screen.queryByRole('button', { name: /^request review$/i })).toBeNull()
    expect(screen.queryByRole('combobox', { name: /select reviewer/i })).toBeNull()
  })

  it('fails closed after an authoritative workflow response is refused', async () => {
    vi.mocked(client.workflowApi.get).mockRejectedValue(new Error('Not visible'))
    renderAssignedDocument('REQ', 'Draft')
    expect(await screen.findByText('Could not load review details.')).toBeTruthy()
    expect(screen.queryByRole('button', { name: /^edit$/i })).toBeNull()
    expect(screen.queryByRole('button', { name: /^request review$/i })).toBeNull()
  })

  it('assigns only a server-returned reviewer without changing account authority', async () => {
    vi.mocked(client.workflowApi.get).mockResolvedValue({ ...workflowState, actions: { ...workflowState.actions, assign_reviewer: true } })
    renderAssignedDocument('REQ', 'Draft')
    fireEvent.click(await screen.findByRole('combobox', { name: 'Select reviewer' }))
    expect(screen.queryByRole('option', { name: approver.full_name })).toBeNull()
    fireEvent.click(screen.getByRole('option', { name: reviewer.full_name }))
    await waitFor(() => expect(client.workflowApi.assign).toHaveBeenCalledWith('requirement', requirement.id, { reviewer_id: reviewer.id }))
    expect(client.usersApi.update).not.toHaveBeenCalled()
  })

  it('submits approval and decline against the current server-returned request', async () => {
    vi.mocked(client.workflowApi.get).mockResolvedValue({ ...workflowState, phase: 'Approval', pending_request: { id: 72, kind: 'approval', status: 'pending', created_at: '2026-10-11T00:00:00Z' }, actions: { ...workflowState.actions, approve: true, decline: true } })
    renderAssignedDocument('REQ', 'Review')
    fireEvent.click(await screen.findByRole('button', { name: /^mark approved$/i }))
    await waitFor(() => expect(client.workflowApi.approve).toHaveBeenCalledWith('requirement', requirement.id))
    await waitFor(() => expect((screen.getByRole('button', { name: /^decline$/i }) as HTMLButtonElement).disabled).toBe(false))
    fireEvent.click(screen.getByRole('button', { name: /^decline$/i }))
    await waitFor(() => expect(client.workflowApi.decline).toHaveBeenCalledWith(72))
  })

  it('opens retained approved content and files without a separate CHG selector', async () => {
    const approved = { ...workflowState, phase: 'Approved', status: 'Approved', options: { ...workflowState.options, changes: [{ id: change.id, change_id: change.change_id, title: change.title }] }, actions: { ...workflowState.actions, edit_current: true, start_revision: true }, revisions: [{ revision_number: 1, captured_at: '2026-10-10T00:00:00Z', approved_by: approver, approved_at: '2026-10-10T00:00:00Z', authorizing_change_id: null }] }
    vi.mocked(client.workflowApi.get).mockResolvedValue(approved)
    vi.mocked(client.workflowApi.getRevision).mockResolvedValue({ revision_number: 1, approved_by: approver, approved_at: '2026-10-10T00:00:00Z', authorizing_change: null, snapshot: { fields: { title: 'Original approved title', description: 'Original approved body', preconditions: 'Original approved precondition' }, sections: [], suite_items: [], attachments: [{ id: 501, original_filename: 'approved.pdf', content_type: 'application/pdf', file_size: 10 }] } })
    renderAssignedDocument('REQ', 'Approved')
    expect(await screen.findByRole('button', { name: /^edit$/i })).toBeTruthy()
    expect(screen.queryByRole('combobox', { name: 'Approved change request' })).toBeNull()
    expect(screen.queryByRole('button', { name: /^start revision$/i })).toBeNull()
    expect(client.workflowApi.startRevision).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: /^revision history$/i }))
    fireEvent.click(await screen.findByRole('button', { name: /^open revision 1$/i }))
    expect(await screen.findByText('Original approved body')).toBeTruthy()
    expect(screen.getByText('Original approved precondition')).toBeTruthy()
    expect(screen.getByRole('button', { name: 'Download approved.pdf' })).toBeTruthy()
    expect(client.workflowApi.getRevision).toHaveBeenCalledWith('requirement', requirement.id, 1)
    expect(screen.getByRole('dialog', { name: 'Approved revision 1' }).querySelector('textarea')).toBeNull()
    const createObjectURL = vi.fn(() => 'blob:approved-file')
    const revokeObjectURL = vi.fn()
    vi.stubGlobal('URL', { createObjectURL, revokeObjectURL })
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    fireEvent.click(screen.getByRole('button', { name: 'Download approved.pdf' }))
    await waitFor(() => expect(client.workflowApi.downloadRevisionAttachment).toHaveBeenCalledWith('requirement', requirement.id, 1, 501))
    await waitFor(() => expect(click).toHaveBeenCalled())
    expect(createObjectURL).toHaveBeenCalled()
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:approved-file')
  })
})


describe('workflow timestamp display', () => {
  it('uses the preferred timezone and minute precision in requests, comments and revision history', async () => {
    localStorage.setItem('bloom-timezone', 'Asia/Tokyo')
    const timestamp = '2026-10-11T12:34:56Z'
    vi.mocked(client.workflowApi.get).mockResolvedValue({ ...workflowState, phase: 'Approval', pending_request: { id: 72, kind: 'approval', status: 'pending', created_at: timestamp }, revisions: [{ revision_number: 1, captured_at: timestamp, approved_by: approver, approved_at: timestamp, authorizing_change_id: null }] })
    vi.mocked(client.artefactsApi.listComments).mockResolvedValue([{ id: 22, author_name: reviewer.full_name, body: 'Reviewed text', created_at: timestamp }] as never)
    vi.mocked(client.workflowApi.getRevision).mockResolvedValue({ revision_number: 1, approved_by: approver, approved_at: timestamp, authorizing_change: null, snapshot: { fields: { title: 'Approved title' }, sections: [], suite_items: [], attachments: [] } } as never)
    try {
      const view = renderAssignedDocument('REQ', 'Review')
      const pending = await screen.findByText(/Pending approval request/)
      expect(pending.textContent).toMatch(/21:34|09:34 PM/)
      expect(pending.textContent).not.toContain('12:34:56Z')
      fireEvent.click(screen.getByRole('button', { name: /^comments$/i }))
      await screen.findByText('Reviewed text')
      expect(view.container.querySelector('time')?.textContent).toMatch(/21:34|09:34 PM/)
      expect(view.container.querySelector('time')?.textContent).not.toContain('12:34:56Z')
      fireEvent.click(screen.getByRole('button', { name: /^revision history$/i }))
      fireEvent.click(await screen.findByRole('button', { name: /^open revision 1$/i }))
      await screen.findByText('Approved title')
      expect(screen.getByRole('dialog', { name: 'Approved revision 1' }).textContent).toMatch(/21:34|09:34 PM/)
      expect(view.container.textContent).not.toContain(timestamp)
    } finally {
      localStorage.removeItem('bloom-timezone')
    }
  })
})
