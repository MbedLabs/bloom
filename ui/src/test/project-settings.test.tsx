import { createQueryClient } from '../lib/queryClient'
// @vitest-environment jsdom
/**
 * Project settings: renaming, re-prefixing, per-member access, and deletion.
 *
 * Two things here are irreversible. Changing the prefix rewrites the scheme
 * every item in the project is identified by, so the page has to refuse a
 * prefix that is malformed or already taken - and follow the project to its
 * new address once it succeeds. Deleting takes the project and everything
 * scoped to it, so it is guarded by typing an exact phrase rather than a
 * single click. Both were largely uncovered, as was the member editor that
 * decides which document types an external user may see at all.
 */
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ToastProvider } from '../components/Toast'
import { project, projectMember, resetApiMocks, user } from './apiFixtures'
import { settle } from './settle'

vi.mock('../api/client', async (importOriginal) => {
  const { mockApiModule: build } = await import('./apiFixtures')
  return build(await importOriginal<Record<string, unknown>>(), vi)
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

vi.mock('../components/IntegrationSettingsPanel', () => ({
  default: () => <div data-testid="tracker-panel" />,
}))

vi.mock('../components/ProjectDocTopology', () => ({
  default: () => <div data-testid="project-topology" />,
}))

const client = await import('../api/client')
const ProjectEdit = (await import('../pages/ProjectEdit')).default
const ProjectDetail = (await import('../pages/ProjectDetail')).default

const otherProject = { ...project, id: 2, name: 'Battery Management', prefix: 'BMS' }
/** A maintainer and an external, neither of them already a member. */
const addableMaintainer = {
  ...user,
  id: 8,
  full_name: 'Grace Hopper',
  email: 'grace@example.com',
  role: 'maintainer' as const,
}
const addableExternal = {
  ...user,
  id: 9,
  full_name: 'Vic Endor',
  email: 'vic@supplier.example',
  role: 'external' as const,
}
const addableAdmin = {
  ...user,
  id: 7,
  full_name: 'Charles Babbage',
  email: 'charles@example.com',
  role: 'admin' as const,
}

function renderEdit(prefix = 'VCU', overview = false) {
  const queryClient = createQueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <MemoryRouter initialEntries={[`/projects/${prefix}${overview ? '' : '/edit'}`]}>
          <Routes>
            <Route path="/projects/:prefix/edit" element={<ProjectEdit />} />
            <Route path="/projects/:prefix" element={<ProjectDetail />} />
            <Route path="/projects" element={<div>project list</div>} />
          </Routes>
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
}

/** The arguments of the most recent call to a mocked endpoint. */
function lastCall(fn: unknown): unknown[] {
  const mock = vi.mocked(fn as (...args: unknown[]) => unknown)
  expect(mock.mock.calls.length).toBeGreaterThan(0)
  return mock.mock.calls[mock.mock.calls.length - 1]
}

/** An axios-shaped rejection carrying the server's message. */
function apiError(detail: string) {
  return Object.assign(new Error('Request failed'), {
    isAxiosError: true,
    response: { data: { detail } },
  })
}

/** The save button, which is the one guarded by the prefix rules. */
function saveButton(): HTMLButtonElement {
  return screen.getByRole('button', { name: /save project/i }) as HTMLButtonElement
}

beforeEach(() => {
  vi.clearAllMocks()
  resetApiMocks(client as unknown as Record<string, unknown>, vi)
  vi.mocked(client.projectsApi.list).mockResolvedValue([project, otherProject] as never)
  vi.mocked(client.usersApi.list).mockResolvedValue([
    user,
    addableMaintainer,
    addableExternal,
  ] as never)
  vi.mocked(client.groupsApi.assignmentOptions).mockResolvedValue({ projects: [project, otherProject], users: [user, addableAdmin, addableMaintainer, addableExternal] })
})

afterEach(() => {
  cleanup()
  ;(user as { role: string }).role = 'admin'
  delete (user as { application_permissions?: Record<string, string[]> }).application_permissions
})

describe('project ownership capabilities', () => {
  it('lets an Owner save metadata without administrative catalogues or controls', async () => {
    ;(user as { role: string }).role = 'maintainer'
    vi.mocked(client.projectsApi.capabilities).mockResolvedValue({
      can_edit: true, can_delete: false, can_manage_access: false,
    })
    renderEdit()
    fireEvent.change(await screen.findByTitle('Project name'), { target: { value: 'Updated project' } })
    fireEvent.click(saveButton())
    await waitFor(() => expect(client.projectsApi.update).toHaveBeenCalledWith(project.id, expect.objectContaining({ name: 'Updated project' })))
    expect(client.usersApi.list).not.toHaveBeenCalled()
    expect(client.policiesApi.list).not.toHaveBeenCalled()
    expect(client.tagsApi.list).not.toHaveBeenCalled()
    expect(client.projectsApi.list).not.toHaveBeenCalled()
    expect(client.projectMembersApi.list).not.toHaveBeenCalled()
    expect(client.projectMembersApi.access).not.toHaveBeenCalled()
    expect(screen.queryByRole('button', { name: /delete project/i })).toBeNull()
    expect(screen.queryByText('Project members')).toBeNull()
    expect(screen.queryByText('Access requests')).toBeNull()
  })

  it('keeps the metadata form unavailable without ownership', async () => {
    ;(user as { role: string }).role = 'maintainer'
    vi.mocked(client.projectsApi.capabilities).mockResolvedValue({
      can_edit: false, can_delete: false, can_manage_access: false,
    })
    renderEdit()
    expect(await screen.findByText(/Project Owner access is required/)).toBeTruthy()
    expect(screen.queryByTitle('Project name')).toBeNull()
  })

  it('keeps the metadata form unavailable after a failed capability read', async () => {
    ;(user as { role: string }).role = 'maintainer'
    vi.mocked(client.projectsApi.capabilities).mockRejectedValue(apiError('Forbidden'))
    renderEdit()
    expect(await screen.findByText(/Project Owner access is required/)).toBeTruthy()
    expect(screen.queryByTitle('Project name')).toBeNull()
  })

  it('does not expose a metadata form while the capability read is pending', async () => {
    ;(user as { role: string }).role = 'maintainer'
    vi.mocked(client.projectsApi.capabilities).mockReturnValue(new Promise(() => {}))
    renderEdit()
    await waitFor(() => expect(client.projectsApi.capabilities).toHaveBeenCalledWith(project.id))
    expect(screen.queryByTitle('Project name')).toBeNull()
  })

  it('shows the Owner edit link on the project overview', async () => {
    ;(user as { role: string }).role = 'maintainer'
    vi.mocked(client.projectsApi.capabilities).mockResolvedValue({
      can_edit: true, can_delete: false, can_manage_access: false,
    })
    renderEdit('VCU', true)
    expect(await screen.findByRole('link', { name: 'Edit project' })).toBeTruthy()
  })

  it('hides the overview edit link when ownership is absent', async () => {
    ;(user as { role: string }).role = 'maintainer'
    vi.mocked(client.projectsApi.capabilities).mockResolvedValue({
      can_edit: false, can_delete: false, can_manage_access: false,
    })
    renderEdit('VCU', true)
    await waitFor(() => expect(client.projectsApi.capabilities).toHaveBeenCalledWith(project.id))
    await settle()
    expect(screen.queryByRole('link', { name: 'Edit project' })).toBeNull()
  })
})

describe('pending document requests on the project', () => {
  it('shows the server-filtered review and approval requests with document links', async () => {
    vi.mocked(client.workflowApi.listProjectRequests).mockResolvedValue([
      { id: 71, kind: 'review', status: 'pending', created_at: '2026-10-11T10:00:00Z',
        artefact_type: 'document', artefact_id: 11, doc_type: 'SPEC', public_id: 'VCU-SPEC-001', revision_number: 2 },
      { id: 72, kind: 'approval', status: 'pending', created_at: '2026-10-11T11:00:00Z',
        artefact_type: 'test-suite', artefact_id: 12, doc_type: 'TS', public_id: 'VCU-TS-001', revision_number: 1 },
    ])
    renderEdit('VCU', true)
    expect((await screen.findByRole('link', { name: 'VCU-SPEC-001' })).getAttribute('href')).toBe('/projects/VCU/docs/specifications/VCU-SPEC-001')
    expect(screen.getByRole('link', { name: 'VCU-TS-001' }).getAttribute('href')).toBe('/projects/VCU/docs/test-suites/VCU-TS-001')
    expect(screen.getByText('Review')).toBeTruthy()
    expect(screen.getByText('Approval')).toBeTruthy()
    expect(screen.getByText('Revision 2')).toBeTruthy()
    expect(client.workflowApi.listProjectRequests).toHaveBeenCalledWith(project.id)
    expect(screen.queryByRole('button', { name: /accept review/i })).toBeNull()
  })

  it('shows an explicit empty state for no pending requests', async () => {
    renderEdit('VCU', true)
    expect(await screen.findByText('No pending document requests.')).toBeTruthy()
  })

  it('shows a read failure instead of claiming there are no pending requests', async () => {
    vi.mocked(client.workflowApi.listProjectRequests).mockRejectedValue(apiError('Unavailable'))
    renderEdit('VCU', true)
    expect(await screen.findByText('Could not load document requests.')).toBeTruthy()
    expect(screen.queryByText('No pending document requests.')).toBeNull()
  })
})

describe('changing a project’s prefix', () => {
  it('upper-cases it and caps it at three characters', async () => {
    renderEdit()
    const prefix = (await screen.findByTitle('Project prefix')) as HTMLInputElement

    expect(prefix.maxLength).toBe(3)
    fireEvent.change(prefix, { target: { value: 'bms' } })
    expect(prefix.value).toBe('BMS')
  })

  it('refuses a prefix another project already uses', async () => {
    renderEdit()
    const prefix = await screen.findByTitle('Project prefix')

    fireEvent.change(prefix, { target: { value: 'BMS' } })

    // Identifiers would collide across the two projects.
    expect(await screen.findByText(/already uses prefix BMS/i)).toBeTruthy()
    await waitFor(() => expect(saveButton().disabled).toBe(true))
  })

  it('allows the project to keep its own prefix', async () => {
    renderEdit()
    await screen.findByTitle('Project prefix')

    // The project's current prefix is "taken" by the project itself, which
    // must not count against it.
    expect(saveButton().disabled).toBe(false)
    expect(screen.queryByText(/already uses prefix/i)).toBeNull()
  })

  it('explains a malformed prefix rather than only disabling save', async () => {
    renderEdit()
    fireEvent.change(await screen.findByTitle('Project prefix'), { target: { value: 'B1' } })

    expect(await screen.findByText(/exactly three uppercase letters/i)).toBeTruthy()
    await waitFor(() => expect(saveButton().disabled).toBe(true))
  })

  it('follows the project to its new address once the prefix changes', async () => {
    vi.mocked(client.projectsApi.update).mockResolvedValue({
      ...project,
      prefix: 'VCX',
    } as never)
    renderEdit()
    fireEvent.change(await screen.findByTitle('Project prefix'), { target: { value: 'VCX' } })
    fireEvent.click(saveButton())

    // Staying on /projects/VCU/edit would 404 the moment the page reloaded.
    await waitFor(() =>
      expect((lastCall(client.projectsApi.update)[1] as { prefix: string }).prefix).toBe('VCX'),
    )
    await waitFor(() => expect(screen.getByTitle('Project prefix')).toBeTruthy())
  })
})

describe('editing the project details', () => {
  it('saves the status and description alongside the name', async () => {
    renderEdit()
    await screen.findByTitle('Project name')

    fireEvent.change(screen.getByTitle('Project status'), { target: { value: 'Archived' } })
    fireEvent.change(screen.getByTitle('Project description'), {
      target: { value: 'Retired after the B-sample' },
    })
    fireEvent.click(saveButton())

    await waitFor(() =>
      expect(lastCall(client.projectsApi.update)).toEqual([
        project.id,
        expect.objectContaining({
          status: 'Archived',
          description: 'Retired after the B-sample',
        }),
      ]),
    )
  })

  it('shows the server’s refusal on the form', async () => {
    vi.mocked(client.projectsApi.update).mockRejectedValueOnce(
      apiError('That prefix was claimed a moment ago'),
    )
    renderEdit()
    fireEvent.change(await screen.findByTitle('Project name'), { target: { value: 'Renamed' } })
    fireEvent.click(saveButton())

    expect((await screen.findAllByText(/claimed a moment ago/i)).length).toBeGreaterThan(0)
  })
})

describe('deleting a project', () => {
  async function openDialog() {
    renderEdit()
    await screen.findByTitle('Project name')
    const buttons = screen.getAllByRole('button', { name: /delete project/i })
    fireEvent.click(buttons[0])
    const dialog = await screen.findByRole('dialog', { name: 'Delete project' })
    return {
      confirm: within(dialog).getByRole('button', { name: 'Delete project' }) as HTMLButtonElement,
      field: screen.getByPlaceholderText(`Delete ${project.prefix}`),
    }
  }

  it('names the project and the phrase that unlocks the button', async () => {
    const dialog = await openDialog()

    expect(screen.getByText(/permanently removes/i).textContent).toContain(project.name)
    expect(dialog.confirm.disabled).toBe(true)
  })

  it('stays locked for a phrase that is close but wrong', async () => {
    const dialog = await openDialog()

    fireEvent.change(dialog.field, { target: { value: 'delete vcu' } })

    // The phrase is compared exactly; lower case is not the same phrase.
    await waitFor(() => expect(dialog.confirm.disabled).toBe(true))
    fireEvent.click(dialog.confirm)
    await settle()
    expect(client.projectsApi.delete).not.toHaveBeenCalled()
  })

  it('deletes once the exact phrase is typed', async () => {
    const dialog = await openDialog()

    fireEvent.change(dialog.field, { target: { value: `Delete ${project.prefix}` } })
    await waitFor(() => expect(dialog.confirm.disabled).toBe(false))
    fireEvent.click(dialog.confirm)

    await waitFor(() => expect(client.projectsApi.delete).toHaveBeenCalled())
    expect(vi.mocked(client.projectsApi.delete).mock.calls[0][0]).toBe(project.id)
    expect(await screen.findByText('project list')).toBeTruthy()
  })

  it('ignores whitespace around the phrase', async () => {
    const dialog = await openDialog()

    fireEvent.change(dialog.field, { target: { value: `  Delete ${project.prefix}  ` } })

    await waitFor(() => expect(dialog.confirm.disabled).toBe(false))
  })

  it('reports a refusal without leaving the dialog', async () => {
    vi.mocked(client.projectsApi.delete).mockRejectedValueOnce(
      apiError('This project still has a running campaign'),
    )
    const dialog = await openDialog()

    fireEvent.change(dialog.field, { target: { value: `Delete ${project.prefix}` } })
    await waitFor(() => expect(dialog.confirm.disabled).toBe(false))
    fireEvent.click(dialog.confirm)

    expect((await screen.findAllByText(/running campaign/i)).length).toBeGreaterThan(0)
    expect(screen.queryByText('project list')).toBeNull()
  })

  it('forgets what was typed when the dialog is reopened', async () => {
    const dialog = await openDialog()
    fireEvent.change(dialog.field, { target: { value: `Delete ${project.prefix}` } })
    fireEvent.click(screen.getAllByRole('button', { name: /^cancel$/i })[0])

    await waitFor(() =>
      expect(screen.queryByPlaceholderText(`Delete ${project.prefix}`)).toBeNull(),
    )
    fireEvent.click(screen.getAllByRole('button', { name: /delete project/i })[0])

    const field = (await screen.findByPlaceholderText(
      `Delete ${project.prefix}`,
    )) as HTMLInputElement
    expect(field.value).toBe('')
    await settle()
    expect(client.projectsApi.delete).not.toHaveBeenCalled()
  })
})

describe('project policy group rosters', () => {
  it('shows four default sections on every project, including empty rosters', async () => {
    vi.mocked(client.projectMembersApi.list).mockResolvedValue([])
    renderEdit()
    for (const name of ['Administrators', 'Developers', 'Product Owners', 'Testers']) {
      expect(await screen.findByRole('region', { name })).toBeTruthy()
    }
    expect(screen.queryByRole('region', { name: 'Customers' })).toBeNull()
    expect(screen.queryByTitle('Select user to add')).toBeNull()
    expect(client.groupsApi.assign).not.toHaveBeenCalled()
    expect(client.projectMembersApi.create).not.toHaveBeenCalled()
    expect(client.usersApi.list).not.toHaveBeenCalled()
  })

  it('assigns multiple selected people including an account admin on this project', async () => {
    renderEdit()
    const roster = within(await screen.findByRole('region', { name: 'Administrators' }))
    fireEvent.click(roster.getByRole('button', { name: 'Choose people' }))
    fireEvent.click(roster.getByRole('checkbox', { name: `Select ${user.full_name}` }))
    fireEvent.click(roster.getByRole('checkbox', { name: `Select ${addableAdmin.full_name}` }))
    fireEvent.click(roster.getByRole('button', { name: 'Save selection' }))
    await waitFor(() => expect(client.groupsApi.assign).toHaveBeenCalledWith(12, project.id, [user.id, addableAdmin.id].sort((a, b) => a - b)))
    expect(client.groupsApi.addMembers).not.toHaveBeenCalled()
  })

  it('uses the same Administrators bundle on a different project', async () => {
    vi.mocked(client.projectsApi.getByPrefix).mockResolvedValue(otherProject as never)
    renderEdit('BMS')
    const roster = within(await screen.findByRole('region', { name: 'Administrators' }))
    fireEvent.click(roster.getByRole('button', { name: 'Choose people' }))
    fireEvent.click(roster.getByRole('checkbox', { name: `Select ${addableAdmin.full_name}` }))
    fireEvent.click(roster.getByRole('button', { name: 'Save selection' }))
    await waitFor(() => expect(client.groupsApi.assign).toHaveBeenCalledWith(12, otherProject.id, [addableAdmin.id]))
  })

  it('assigns a Maintainer to the Administrators roster for this project', async () => {
    renderEdit()
    const roster = within(await screen.findByRole('region', { name: 'Administrators' }))
    fireEvent.click(roster.getByRole('button', { name: 'Choose people' }))
    fireEvent.click(roster.getByRole('checkbox', { name: `Select ${addableMaintainer.full_name}` }))
    fireEvent.click(roster.getByRole('button', { name: 'Save selection' }))

    await waitFor(() => expect(client.groupsApi.assign).toHaveBeenCalledWith(12, project.id, [addableMaintainer.id]))
    expect(client.groupsApi.addMembers).not.toHaveBeenCalled()
    expect(client.usersApi.update).not.toHaveBeenCalled()
  })

  it('keeps legacy entries until an explicit roster assignment replaces them', async () => {
    vi.mocked(client.projectMembersApi.list).mockResolvedValue([{ ...projectMember, owner: true, inherit_policies: false, policy_ids: [] }])
    renderEdit()
    expect(await screen.findByText('Owner')).toBeTruthy()
    expect(screen.queryByLabelText(`Policy group for ${projectMember.full_name}`)).toBeNull()
    expect(client.groupsApi.assign).not.toHaveBeenCalled()
    expect(client.projectMembersApi.update).not.toHaveBeenCalled()
    expect(client.projectMembersApi.remove).not.toHaveBeenCalled()
  })

  it('adds Customers as an optional section without saving an assignment', async () => {
    renderEdit()
    await screen.findByRole('region', { name: 'Administrators' })
    fireEvent.change(screen.getByLabelText('Additional policy group'), { target: { value: '11' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add group' }))
    expect(await screen.findByRole('region', { name: 'Customers' })).toBeTruthy()
    expect(client.groupsApi.assign).not.toHaveBeenCalled()
  })

  it('shows persisted people under their project group', async () => {
    vi.mocked(client.projectMembersApi.list).mockResolvedValue([{ ...projectMember, inherit_policies: false, policy_group_id: 10, policy_group_name: 'Developers' }])
    renderEdit()
    const roster = within(await screen.findByRole('region', { name: 'Developers' }))
    expect(roster.getByText(projectMember.full_name)).toBeTruthy()
    fireEvent.click(roster.getByRole('button', { name: `Remove ${projectMember.full_name} from project` }))
    await waitFor(() => expect(client.projectMembersApi.remove).toHaveBeenCalledWith(project.id, projectMember.id))
    expect(client.usersApi.delete).not.toHaveBeenCalled()
  })

  it('removes an individual project assignment without deleting the account', async () => {
    vi.mocked(client.projectMembersApi.list).mockResolvedValue([{ ...projectMember, owner: true, inherit_policies: false, policy_ids: [] }])
    renderEdit()
    fireEvent.click(await screen.findByRole('button', { name: `Remove ${projectMember.full_name} from project` }))
    await waitFor(() => expect(client.projectMembersApi.remove).toHaveBeenCalledWith(project.id, projectMember.id))
    expect(client.usersApi.delete).not.toHaveBeenCalled()
  })

  it('includes assigned people once in the checklist with their boxes checked', async () => {
    vi.mocked(client.groupsApi.assignmentOptions).mockResolvedValue({ projects: [project], users: [user, addableMaintainer, { ...projectMember, id: projectMember.user_id, role: 'external' }] })
    vi.mocked(client.projectMembersApi.list).mockResolvedValue([{ ...projectMember, inherit_policies: false, policy_group_id: 10, policy_group_name: 'Developers' }])
    renderEdit()
    const roster = within(await screen.findByRole('region', { name: 'Developers' }))
    fireEvent.click(roster.getByRole('button', { name: 'Choose people' }))
    expect((roster.getByRole('checkbox', { name: `Select ${projectMember.full_name}` }) as HTMLInputElement).checked).toBe(true)
    expect(roster.getAllByText(projectMember.full_name)).toHaveLength(1)
    expect((roster.getByRole('checkbox', { name: `Select ${addableMaintainer.full_name}` }) as HTMLInputElement).checked).toBe(false)
    expect(roster.queryByRole('button', { name: `Remove ${projectMember.full_name} from project` })).toBeNull()
    expect((roster.getByRole('button', { name: 'Save selection' }) as HTMLButtonElement).disabled).toBe(true)
    expect(client.groupsApi.assign).not.toHaveBeenCalled()
    expect(client.projectMembersApi.remove).not.toHaveBeenCalled()
  })

  it('saves only new people while retaining the existing project assignments', async () => {
    vi.mocked(client.projectMembersApi.list).mockResolvedValue([{ ...projectMember, inherit_policies: false, policy_group_id: 10, policy_group_name: 'Developers' }])
    renderEdit()
    const roster = within(await screen.findByRole('region', { name: 'Developers' }))
    fireEvent.click(roster.getByRole('button', { name: 'Choose people' }))
    fireEvent.click(roster.getByRole('checkbox', { name: `Select ${addableMaintainer.full_name}` }))
    fireEvent.click(roster.getByRole('button', { name: 'Save selection' }))
    await waitFor(() => expect(client.groupsApi.assign).toHaveBeenCalledWith(10, project.id, [addableMaintainer.id]))
    expect(client.projectMembersApi.remove).not.toHaveBeenCalled()
    expect(client.usersApi.update).not.toHaveBeenCalled()
  })

  it('unchecks an assigned person without removing them until Save', async () => {
    const retained = { ...projectMember, id: 92, user_id: addableMaintainer.id, full_name: addableMaintainer.full_name, email: addableMaintainer.email, inherit_policies: false, policy_group_id: 10, policy_group_name: 'Developers' }
    vi.mocked(client.projectMembersApi.list).mockResolvedValue([{ ...projectMember, inherit_policies: false, policy_group_id: 10, policy_group_name: 'Developers' }, retained])
    renderEdit()
    const roster = within(await screen.findByRole('region', { name: 'Developers' }))
    fireEvent.click(roster.getByRole('button', { name: 'Choose people' }))
    fireEvent.click(roster.getByRole('checkbox', { name: `Select ${projectMember.full_name}` }))
    expect(client.projectMembersApi.remove).not.toHaveBeenCalled()
    fireEvent.click(roster.getByRole('button', { name: 'Save selection' }))
    await waitFor(() => expect(client.projectMembersApi.remove).toHaveBeenCalledWith(project.id, projectMember.id))
    expect(client.projectMembersApi.remove).toHaveBeenCalledTimes(1)
    expect(client.groupsApi.assign).not.toHaveBeenCalled()
    expect(client.usersApi.delete).not.toHaveBeenCalled()
  })

  it('can save an empty roster after unchecking its last assigned person', async () => {
    vi.mocked(client.projectMembersApi.list).mockResolvedValue([{ ...projectMember, inherit_policies: false, policy_group_id: 10, policy_group_name: 'Developers' }])
    renderEdit()
    const roster = within(await screen.findByRole('region', { name: 'Developers' }))
    fireEvent.click(roster.getByRole('button', { name: 'Choose people' }))
    fireEvent.click(roster.getByRole('checkbox', { name: `Select ${projectMember.full_name}` }))
    expect((roster.getByRole('button', { name: 'Save selection' }) as HTMLButtonElement).disabled).toBe(false)
    fireEvent.click(roster.getByRole('button', { name: 'Save selection' }))
    await waitFor(() => expect(client.projectMembersApi.remove).toHaveBeenCalledWith(project.id, projectMember.id))
    expect(client.groupsApi.assign).not.toHaveBeenCalled()
  })

  it('restores assigned checkboxes after cancelling an unsaved removal', async () => {
    vi.mocked(client.projectMembersApi.list).mockResolvedValue([{ ...projectMember, inherit_policies: false, policy_group_id: 10, policy_group_name: 'Developers' }])
    renderEdit()
    const roster = within(await screen.findByRole('region', { name: 'Developers' }))
    fireEvent.click(roster.getByRole('button', { name: 'Choose people' }))
    fireEvent.click(roster.getByRole('checkbox', { name: `Select ${projectMember.full_name}` }))
    fireEvent.click(roster.getByRole('button', { name: 'Cancel selection' }))
    expect(roster.getByRole('button', { name: `Remove ${projectMember.full_name} from project` })).toBeTruthy()
    fireEvent.click(roster.getByRole('button', { name: 'Choose people' }))
    expect((roster.getByRole('checkbox', { name: `Select ${projectMember.full_name}` }) as HTMLInputElement).checked).toBe(true)
    expect(client.groupsApi.assign).not.toHaveBeenCalled()
    expect(client.projectMembersApi.remove).not.toHaveBeenCalled()
  })

  it('keeps assigned accounts visible when absent from active assignment choices', async () => {
    vi.mocked(client.projectMembersApi.list).mockResolvedValue([{ ...projectMember, inherit_policies: false, policy_group_id: 10, policy_group_name: 'Developers' }])
    renderEdit()
    const roster = within(await screen.findByRole('region', { name: 'Developers' }))
    fireEvent.click(roster.getByRole('button', { name: 'Choose people' }))
    fireEvent.change(roster.getByRole('textbox', { name: 'Search people for Developers' }), { target: { value: projectMember.full_name } })
    expect((roster.getByRole('checkbox', { name: `Select ${projectMember.full_name}` }) as HTMLInputElement).checked).toBe(true)
  })

  it('requires deletion authority to uncheck an existing assignment', async () => {
    ;(user as { role: string }).role = 'maintainer'
    ;(user as { application_permissions?: Record<string, string[]> }).application_permissions = { access: ['view', 'edit'] }
    vi.mocked(client.projectMembersApi.list).mockResolvedValue([{ ...projectMember, inherit_policies: false, policy_group_id: 10, policy_group_name: 'Developers' }])
    renderEdit()
    const roster = within(await screen.findByRole('region', { name: 'Developers' }))
    fireEvent.click(roster.getByRole('button', { name: 'Choose people' }))
    const assignedBox = roster.getByRole('checkbox', { name: `Select ${projectMember.full_name}` }) as HTMLInputElement
    expect(assignedBox.checked).toBe(true)
    expect(assignedBox.disabled).toBe(true)
    expect((roster.getByRole('checkbox', { name: `Select ${addableMaintainer.full_name}` }) as HTMLInputElement).disabled).toBe(false)
    expect(client.projectMembersApi.remove).not.toHaveBeenCalled()
  })

  it('retains checked people after a failed assignment and shows the error', async () => {
    vi.mocked(client.groupsApi.assign).mockRejectedValueOnce(apiError('Assignment rejected'))
    renderEdit()
    const roster = within(await screen.findByRole('region', { name: 'Testers' }))
    fireEvent.click(roster.getByRole('button', { name: 'Choose people' }))
    const person = roster.getByRole('checkbox', { name: `Select ${addableMaintainer.full_name}` }) as HTMLInputElement
    fireEvent.click(person)
    fireEvent.click(roster.getByRole('button', { name: 'Save selection' }))
    expect((await screen.findAllByText('Assignment rejected')).length).toBeGreaterThan(0)
    expect(person.checked).toBe(true)
  })

  it('blocks duplicate submissions while the selected people are saving', async () => {
    let finish: (value: never[]) => void = () => {}
    vi.mocked(client.groupsApi.assign).mockImplementationOnce(() => new Promise((resolve) => { finish = resolve }))
    renderEdit()
    const roster = within(await screen.findByRole('region', { name: 'Developers' }))
    fireEvent.click(roster.getByRole('button', { name: 'Choose people' }))
    fireEvent.click(roster.getByRole('checkbox', { name: `Select ${addableMaintainer.full_name}` }))
    fireEvent.click(roster.getByRole('button', { name: 'Save selection' }))
    await waitFor(() => expect((roster.getByRole('button', { name: 'Saving...' }) as HTMLButtonElement).disabled).toBe(true))
    expect((roster.getByRole('checkbox', { name: `Select ${addableMaintainer.full_name}` }) as HTMLInputElement).disabled).toBe(true)
    expect(client.groupsApi.assign).toHaveBeenCalledTimes(1)
    finish([])
    await settle()
  })

  it('discards an unsaved selection when it is cancelled', async () => {
    renderEdit()
    const roster = within(await screen.findByRole('region', { name: 'Developers' }))
    fireEvent.click(roster.getByRole('button', { name: 'Choose people' }))
    fireEvent.click(roster.getByRole('checkbox', { name: `Select ${addableMaintainer.full_name}` }))
    fireEvent.click(roster.getByRole('button', { name: 'Cancel selection' }))
    fireEvent.click(roster.getByRole('button', { name: 'Choose people' }))
    expect((roster.getByRole('checkbox', { name: `Select ${addableMaintainer.full_name}` }) as HTMLInputElement).checked).toBe(false)
    expect(client.groupsApi.assign).not.toHaveBeenCalled()
  })

  it('lets an Access Manager reach the roster without document admission or metadata editing', async () => {
    ;(user as { role: string }).role = 'maintainer'
    ;(user as { application_permissions?: Record<string, string[]> }).application_permissions = { access: ['view', 'create', 'edit', 'delete'] }
    vi.mocked(client.projectsApi.getByPrefix).mockRejectedValueOnce(apiError('No project access'))
    renderEdit()
    const roster = within(await screen.findByRole('region', { name: 'Developers' }))
    fireEvent.click(roster.getByRole('button', { name: 'Choose people' }))
    fireEvent.click(roster.getByRole('checkbox', { name: `Select ${addableMaintainer.full_name}` }))
    fireEvent.click(roster.getByRole('button', { name: 'Save selection' }))
    await waitFor(() => expect(client.groupsApi.assign).toHaveBeenCalledWith(10, project.id, [addableMaintainer.id]))
    expect(screen.queryByTitle('Project name')).toBeNull()
    expect(screen.queryByTestId('tracker-panel')).toBeNull()
    expect(screen.queryByText('Danger zone')).toBeNull()
    expect(client.usersApi.list).not.toHaveBeenCalled()
  })

  it('filters roster candidates transitively by base role', async () => {
    renderEdit()
    const adminsRoster = within(await screen.findByRole('region', { name: 'Administrators' }))
    fireEvent.click(adminsRoster.getByRole('button', { name: 'Choose people' }))
    expect(adminsRoster.queryByRole('checkbox', { name: `Select ${addableAdmin.full_name}` })).toBeTruthy()
    expect(adminsRoster.queryByRole('checkbox', { name: `Select ${addableMaintainer.full_name}` })).toBeTruthy()
    expect(adminsRoster.queryByRole('checkbox', { name: `Select ${addableExternal.full_name}` })).toBeNull()

    const devsRoster = within(await screen.findByRole('region', { name: 'Developers' }))
    fireEvent.click(devsRoster.getByRole('button', { name: 'Choose people' }))
    expect(devsRoster.queryByRole('checkbox', { name: `Select ${addableAdmin.full_name}` })).toBeTruthy()
    expect(devsRoster.queryByRole('checkbox', { name: `Select ${addableMaintainer.full_name}` })).toBeTruthy()
    expect(devsRoster.queryByRole('checkbox', { name: `Select ${addableExternal.full_name}` })).toBeNull()

    fireEvent.change(screen.getByLabelText('Additional policy group'), { target: { value: '11' } })
    fireEvent.click(screen.getByRole('button', { name: 'Add group' }))
    const customersRoster = within(await screen.findByRole('region', { name: 'Customers' }))
    fireEvent.click(customersRoster.getByRole('button', { name: 'Choose people' }))
    expect(customersRoster.queryByRole('checkbox', { name: `Select ${addableAdmin.full_name}` })).toBeTruthy()
    expect(customersRoster.queryByRole('checkbox', { name: `Select ${addableMaintainer.full_name}` })).toBeTruthy()
    expect(customersRoster.queryByRole('checkbox', { name: `Select ${addableExternal.full_name}` })).toBeTruthy()
  })
})

describe('who has access', () => {
  it('does not render who has access section', async () => {
    renderEdit()
    await screen.findByRole('region', { name: 'Administrators' })
    expect(screen.queryByText('Who has access')).toBeNull()
  })
})
