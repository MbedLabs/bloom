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
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
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

const client = await import('../api/client')
const ProjectEdit = (await import('../pages/ProjectEdit')).default

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

function renderEdit(prefix = 'VCU') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <MemoryRouter initialEntries={[`/projects/${prefix}/edit`]}>
          <Routes>
            <Route path="/projects/:prefix/edit" element={<ProjectEdit />} />
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
})

afterEach(cleanup)

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
    // Two buttons read "Delete project": the one that opens the dialog and the
    // one inside it.
    const all = await screen.findAllByRole('button', { name: /delete project/i })
    return {
      confirm: all[all.length - 1] as HTMLButtonElement,
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

describe('project members', () => {
  beforeEach(() => {
    vi.mocked(client.projectMembersApi.list).mockResolvedValue([projectMember] as never)
  })

  it('offers only users who are not already members, and never an admin', async () => {
    renderEdit()
    await screen.findByText(projectMember.full_name)

    const picker = screen.getByTitle('Select user to add') as HTMLSelectElement
    const offered = Array.from(picker.options).map((option) => option.textContent)
    // An admin already reaches every project, and the external is a member.
    expect(offered).toEqual([
      'Select a user',
      `${addableMaintainer.full_name} (${addableMaintainer.email})`,
      `${addableExternal.full_name} (${addableExternal.email})`,
    ])
  })

  it('adds an external member with the document types that were ticked', async () => {
    renderEdit()
    await screen.findByText(projectMember.full_name)

    fireEvent.change(screen.getByTitle('Select user to add'), {
      target: { value: String(addableExternal.id) },
    })
    // The form starts with four types ticked; drop one.
    const addForm = screen.getByTitle('Project role').closest('form') as HTMLElement
    fireEvent.click(within(addForm).getByLabelText('CMP'))
    fireEvent.click(screen.getByRole('button', { name: /add member/i }))

    await waitFor(() =>
      expect(lastCall(client.projectMembersApi.create)).toEqual([
        project.id,
        { user_id: addableExternal.id, role: 'external', doc_types: ['REQ', 'TC', 'CPT'] },
      ]),
    )
  })

  it('sends no document types for a maintainer, who sees everything', async () => {
    renderEdit()
    await screen.findByText(projectMember.full_name)

    fireEvent.change(screen.getByTitle('Select user to add'), {
      target: { value: String(addableMaintainer.id) },
    })
    fireEvent.change(screen.getByTitle('Project role'), { target: { value: 'maintainer' } })
    fireEvent.click(screen.getByRole('button', { name: /add member/i }))

    await waitFor(() =>
      expect(lastCall(client.projectMembersApi.create)[1]).toEqual({
        user_id: addableMaintainer.id,
        role: 'maintainer',
        doc_types: undefined,
      }),
    )
  })

  it('reports why a member could not be added', async () => {
    vi.mocked(client.projectMembersApi.create).mockRejectedValueOnce(
      apiError('That user is already a member of this project'),
    )
    renderEdit()
    await screen.findByText(projectMember.full_name)

    fireEvent.change(screen.getByTitle('Select user to add'), {
      target: { value: String(addableExternal.id) },
    })
    fireEvent.click(screen.getByRole('button', { name: /add member/i }))

    expect((await screen.findAllByText(/already a member/i)).length).toBeGreaterThan(0)
  })

  it('saves a change to an existing member’s visibility', async () => {
    renderEdit()
    await screen.findByText(projectMember.full_name)

    const row = screen
      .getByTitle(`Project role for ${projectMember.full_name}`)
      .closest('div.rounded-lg') as HTMLElement
    fireEvent.click(within(row).getByLabelText('TC'))
    fireEvent.click(within(row).getByRole('button', { name: /save member settings/i }))

    // The fixture member can see REQ only; ticking TC adds it.
    await waitFor(() =>
      expect(lastCall(client.projectMembersApi.update)).toEqual([
        project.id,
        projectMember.id,
        { role: 'external', doc_types: ['REQ', 'TC'] },
      ]),
    )
  })

  it('clears the document types when a member is promoted to maintainer', async () => {
    renderEdit()
    await screen.findByText(projectMember.full_name)

    const roleField = screen.getByTitle(`Project role for ${projectMember.full_name}`)
    fireEvent.change(roleField, { target: { value: 'maintainer' } })

    const row = roleField.closest('div.rounded-lg') as HTMLElement
    expect(within(row).getByText(/maintainers can access the full project surface/i)).toBeTruthy()
    fireEvent.click(within(row).getByRole('button', { name: /save member settings/i }))

    // Leaving the old types behind would keep a stale restriction on record.
    await waitFor(() =>
      expect(lastCall(client.projectMembersApi.update)[2]).toEqual({
        role: 'maintainer',
        doc_types: [],
      }),
    )
  })

  it('removes a member', async () => {
    renderEdit()
    await screen.findByText(projectMember.full_name)

    fireEvent.click(screen.getByRole('button', { name: /^remove$/i }))

    await waitFor(() =>
      expect(lastCall(client.projectMembersApi.remove)).toEqual([project.id, projectMember.id]),
    )
  })

  it('says plainly when a project has no explicit members', async () => {
    vi.mocked(client.projectMembersApi.list).mockResolvedValue([] as never)
    renderEdit()

    expect(await screen.findByText(/no explicit project members yet/i)).toBeTruthy()
  })
})
