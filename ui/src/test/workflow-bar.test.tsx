// @vitest-environment jsdom
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ToastProvider } from '../components/Toast'
import { createQueryClient } from '../lib/queryClient'
import { requirement, resetApiMocks, user, workflowFixture } from './apiFixtures'

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
const WorkflowPanel = (await import('../components/WorkflowPanel')).default

const reviewer = { ...user, id: 2, full_name: 'Grace Hopper' }
const approver = { ...user, id: 3, full_name: 'Charles Babbage' }
const noActions = { ...workflowFixture.actions, comment: false, edit_current: false, plan_current: false }
const state = { ...workflowFixture, phase: 'Review', revision_number: 2, assignee: user, reviewer, approver, options: { assignees: [user, reviewer], reviewers: [reviewer], approvers: [approver], changes: [] }, actions: noActions }
const ACTION_BUTTONS = ['Request review', 'Mark Reviewed', 'Mark Approved', 'Decline', 'Start working Draft']

/** Render the review bar of a requirement with the given workflow state. */
async function renderBar(workflow: Record<string, unknown>) {
  vi.mocked(client.workflowApi.get).mockResolvedValue(workflow as never)
  const queryClient = createQueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <MemoryRouter>
          <WorkflowPanel artefactType="requirement" artefactId={requirement.id} projectPrefix="VCU" projectId={1} layout="bar" />
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
  await screen.findByRole('button', { name: 'Details' })
  return screen.getByRole('region', { name: 'Document review' })
}

/** The names of the action buttons the bar shows, in order. */
function shownActions(bar: HTMLElement) {
  return within(bar).queryAllByRole('button').map(button => button.textContent).filter(name => ACTION_BUTTONS.includes(name ?? ''))
}

beforeEach(() => {
  vi.clearAllMocks()
  resetApiMocks(client as unknown as Record<string, unknown>, vi)
})

afterEach(() => {
  cleanup()
})

describe('the review bar above a document', () => {
  it('summarises the phase and the people on one line', async () => {
    const bar = await renderBar(state)
    expect(within(bar).getByText('Review · Revision 2')).toBeTruthy()
    expect(within(bar).getByText('Assignee').parentElement?.textContent).toBe(`Assignee ${user.full_name}`)
    expect(within(bar).getByText('Reviewer').parentElement?.textContent).toBe(`Reviewer ${reviewer.full_name}`)
    expect(within(bar).getByText('Approver').parentElement?.textContent).toBe(`Approver ${approver.full_name}`)
  })

  it('shows Unassigned for missing people and no assignee or approver on a non-controlled document', async () => {
    const bar = await renderBar({ ...state, controlled: false, reviewer: null })
    expect(within(bar).getByText('Reviewer').parentElement?.textContent).toBe('Reviewer Unassigned')
    expect(within(bar).queryByText('Assignee')).toBeNull()
    expect(within(bar).queryByText('Approver')).toBeNull()
  })

  it('shows no action button when no action is allowed', async () => {
    const bar = await renderBar(state)
    expect(shownActions(bar)).toEqual([])
  })

  it.each([
    ['request_review', 'Request review', () => expect(client.workflowApi.request).toHaveBeenCalledWith('requirement', requirement.id, 'review')],
    ['request_approval', 'Mark Reviewed', () => expect(client.workflowApi.request).toHaveBeenCalledWith('requirement', requirement.id, 'approval')],
    ['approve', 'Mark Approved', () => expect(client.workflowApi.approve).toHaveBeenCalledWith('requirement', requirement.id)],
    ['start_draft', 'Start working Draft', () => expect(client.workflowApi.startDraft).toHaveBeenCalledWith('requirement', requirement.id)],
  ] as const)('shows only %s as %s and sends it', async (action, label, sent) => {
    const bar = await renderBar({ ...state, actions: { ...noActions, [action]: true } })
    expect(shownActions(bar)).toEqual([label])
    fireEvent.click(within(bar).getByRole('button', { name: label }))
    await waitFor(sent)
  })

  it('shows Decline only with a pending request and declines that request', async () => {
    const without = await renderBar({ ...state, actions: { ...noActions, decline: true } })
    expect(shownActions(without)).toEqual([])
    cleanup()
    const bar = await renderBar({ ...state, pending_request: { id: 72, kind: 'review', status: 'pending', created_at: '2026-10-11T00:00:00Z' }, actions: { ...noActions, decline: true } })
    expect(shownActions(bar)).toEqual(['Decline'])
    fireEvent.click(within(bar).getByRole('button', { name: 'Decline' }))
    await waitFor(() => expect(client.workflowApi.decline).toHaveBeenCalledWith(72))
  })

  it('offers the review requests only on a controlled document', async () => {
    const bar = await renderBar({ ...state, controlled: false, actions: { ...noActions, request_review: true, request_approval: true, approve: true } })
    expect(shownActions(bar)).toEqual(['Mark Approved'])
  })

  it('reveals the Review and Approval cards with their selects and revision history under Details', async () => {
    const bar = await renderBar({ ...state, actions: { ...noActions, assign_assignee: true, assign_reviewer: true, assign_approver: true } })
    const details = within(bar).getByRole('button', { name: 'Details' })
    expect(details.getAttribute('aria-expanded')).toBe('false')
    expect(within(bar).queryByRole('heading', { name: 'Review' })).toBeNull()
    expect(within(bar).queryByRole('heading', { name: 'Approval' })).toBeNull()
    expect(within(bar).queryByRole('combobox')).toBeNull()

    fireEvent.click(details)
    expect(details.getAttribute('aria-expanded')).toBe('true')
    expect(within(bar).getByRole('heading', { name: 'Review' })).toBeTruthy()
    expect(within(bar).getByRole('heading', { name: 'Approval' })).toBeTruthy()
    expect(within(bar).getByRole('combobox', { name: 'Select assignee' })).toBeTruthy()
    expect(within(bar).getByRole('combobox', { name: 'Select reviewer' })).toBeTruthy()
    expect(within(bar).getByRole('combobox', { name: 'Select approver' })).toBeTruthy()
    expect(within(bar).getByRole('button', { name: 'Revision history' })).toBeTruthy()

    fireEvent.click(details)
    expect(details.getAttribute('aria-expanded')).toBe('false')
    expect(within(bar).queryByRole('heading', { name: 'Review' })).toBeNull()
  })

  it('has no discussion of its own', async () => {
    const bar = await renderBar({ ...state, actions: { ...noActions, comment: true } })
    expect(within(bar).queryByRole('region', { name: 'Document discussion' })).toBeNull()
    expect(within(bar).queryByRole('textbox')).toBeNull()
    expect(client.artefactsApi.listComments).not.toHaveBeenCalled()
  })
})
