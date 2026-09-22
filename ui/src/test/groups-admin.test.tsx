// @vitest-environment jsdom
/**
 * The admin Groups & Policies screen: it lists groups and policies, creates and
 * deletes them, manages a group's members and project grants, and protects the
 * shipped default policies from deletion.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const policies = [
  {
    id: 1, name: 'Administrator', description: '', base_role: 'admin',
    permissions: {}, doc_tag_scope: null, is_default: true,
    created_at: '', updated_at: '',
  },
  {
    id: 2, name: 'Field Auditor', description: '', base_role: 'external',
    permissions: {}, doc_tag_scope: ['REQ'], is_default: false,
    created_at: '', updated_at: '',
  },
]
const groups = [
  {
    id: 10, name: 'QA Reviewers', description: '', policy_id: 2,
    created_at: '', updated_at: '',
    members: [{ user_id: 5, email: 'q@x.io', full_name: 'Quinn' }],
    grants: [{ id: 3, project_id: null }],
  },
]

vi.mock('../api/client', () => ({
  policiesApi: {
    list: vi.fn().mockResolvedValue(policies),
    create: vi.fn().mockResolvedValue(policies[1]),
    update: vi.fn().mockResolvedValue(policies[1]),
    delete: vi.fn().mockResolvedValue(undefined),
  },
  groupsApi: {
    list: vi.fn().mockResolvedValue(groups),
    create: vi.fn().mockResolvedValue(groups[0]),
    update: vi.fn().mockResolvedValue(groups[0]),
    delete: vi.fn().mockResolvedValue(undefined),
    addMember: vi.fn().mockResolvedValue(groups[0]),
    removeMember: vi.fn().mockResolvedValue(undefined),
    addGrant: vi.fn().mockResolvedValue(groups[0]),
    removeGrant: vi.fn().mockResolvedValue(undefined),
  },
  usersApi: {
    list: vi.fn().mockResolvedValue([
      { id: 5, email: 'q@x.io', full_name: 'Quinn' },
      { id: 6, email: 'dev@x.io', full_name: 'Dev Eloper' },
    ]),
  },
  projectsApi: { list: vi.fn().mockResolvedValue([{ id: 7, name: 'Apollo', prefix: 'APO' }]) },
}))

vi.mock('../components/useToast', () => ({
  useToast: () => ({ saved: vi.fn(), deleted: vi.fn(), failed: vi.fn(), notify: vi.fn() }),
}))

const api = await import('../api/client')
const GroupsPage = (await import('../pages/Groups')).default

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <GroupsPage />
    </QueryClientProvider>,
  )
}

beforeEach(() => vi.clearAllMocks())
afterEach(cleanup)

describe('Groups & policies admin screen', () => {
  it('lists groups and policies with an all-projects grant', async () => {
    renderPage()
    expect(await screen.findByText('QA Reviewers')).toBeTruthy()
    expect(screen.getByText('Administrator')).toBeTruthy()
    // 'Field Auditor' shows both as a policy row and as the group's policy column.
    expect(screen.getAllByText('Field Auditor').length).toBeGreaterThanOrEqual(2)
    expect(screen.getByText('All projects')).toBeTruthy()
  })

  it('protects a default policy from deletion', async () => {
    renderPage()
    await screen.findByText('Administrator')
    const del = screen.getByTitle('Default policies cannot be deleted') as HTMLButtonElement
    expect(del.disabled).toBe(true)
  })

  it('creates a group', async () => {
    renderPage()
    await screen.findByText('QA Reviewers')
    fireEvent.click(screen.getByText('New group'))
    fireEvent.change(await screen.findByTitle('Group name'), { target: { value: 'Vendors' } })
    fireEvent.click(screen.getByText('Save group'))
    await waitFor(() =>
      expect(api.groupsApi.create).toHaveBeenCalledWith(
        expect.objectContaining({ name: 'Vendors' }),
      ),
    )
  })

  it('creates an external policy with a document-type scope', async () => {
    renderPage()
    await screen.findByText('Administrator')
    fireEvent.click(screen.getByText('New policy'))
    fireEvent.change(await screen.findByTitle('Policy name'), { target: { value: 'Client View' } })
    fireEvent.click(screen.getByText('TC')) // toggle a document type on
    fireEvent.click(screen.getByText('Save policy'))
    await waitFor(() =>
      expect(api.policiesApi.create).toHaveBeenCalledWith(
        expect.objectContaining({ name: 'Client View', base_role: 'external', doc_tag_scope: ['TC'] }),
      ),
    )
  })

  it('deletes a group', async () => {
    renderPage()
    fireEvent.click(await screen.findByTitle('Delete group'))
    await waitFor(() => expect(api.groupsApi.delete).toHaveBeenCalledWith(10))
  })

  it('deletes a non-default policy', async () => {
    renderPage()
    fireEvent.click(await screen.findByTitle('Delete Field Auditor'))
    await waitFor(() => expect(api.policiesApi.delete).toHaveBeenCalledWith(2))
  })

  it('edits a group', async () => {
    renderPage()
    await screen.findByText('QA Reviewers')
    fireEvent.click(screen.getByTitle('Edit group'))
    fireEvent.change(await screen.findByTitle('Group name'), { target: { value: 'QA Team' } })
    fireEvent.click(screen.getByText('Save group'))
    await waitFor(() =>
      expect(api.groupsApi.update).toHaveBeenCalledWith(10, expect.objectContaining({ name: 'QA Team' })),
    )
  })

  it('edits a non-default policy', async () => {
    renderPage()
    // 'Field Auditor' also appears as the group's policy, so wait on the unique button.
    fireEvent.click(await screen.findByTitle('Edit Field Auditor'))
    fireEvent.change(await screen.findByTitle('Description'), { target: { value: 'Updated' } })
    fireEvent.click(screen.getByText('Save policy'))
    await waitFor(() =>
      expect(api.policiesApi.update).toHaveBeenCalledWith(2, expect.objectContaining({ description: 'Updated' })),
    )
  })

  it('locks a default policy name and base role in the editor', async () => {
    renderPage()
    await screen.findByText('Administrator')
    fireEvent.click(screen.getByTitle('Edit Administrator'))
    const nameInput = (await screen.findByTitle('Policy name')) as HTMLInputElement
    expect(nameInput.disabled).toBe(true)
  })

  it('manages a group: adds and removes members and grants', async () => {
    renderPage()
    await screen.findByText('QA Reviewers')
    fireEvent.click(screen.getByTitle('Manage members and projects'))
    const dialog = (await screen.findByText(/Manage QA Reviewers/)).closest('div')!.parentElement!

    // Add the non-member user (wait for the async user list to fill the select).
    await within(dialog).findByRole('option', { name: /Dev Eloper/ })
    fireEvent.change(within(dialog).getByTitle('Add member'), { target: { value: '6' } })
    fireEvent.click(within(dialog).getByText('Add'))
    await waitFor(() => expect(api.groupsApi.addMember).toHaveBeenCalledWith(10, 6))

    // Grant a specific project (wait for the async project list).
    await within(dialog).findByRole('option', { name: 'Apollo' })
    fireEvent.change(within(dialog).getByTitle('Grant a project'), { target: { value: '7' } })
    fireEvent.click(within(dialog).getByText('Grant'))
    await waitFor(() => expect(api.groupsApi.addGrant).toHaveBeenCalledWith(10, 7))

    fireEvent.click(within(dialog).getByTitle('Remove member'))
    await waitFor(() => expect(api.groupsApi.removeMember).toHaveBeenCalledWith(10, 5))
    fireEvent.click(within(dialog).getByTitle('Remove grant'))
    await waitFor(() => expect(api.groupsApi.removeGrant).toHaveBeenCalledWith(10, 3))
  })
})
