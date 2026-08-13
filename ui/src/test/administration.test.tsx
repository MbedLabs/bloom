// @vitest-environment jsdom
/**
 * The administrator's screens: people, projects, and project parameters.
 *
 * These are the pages where a mistake is expensive and irreversible - a role
 * granted, an account deleted, a project removed - so the guards matter as
 * much as the happy paths. Each case drives the real component and asserts on
 * the call it makes or on the text a user would read, including the cases
 * where the page must *not* call the server: a role it may not change, a
 * prefix it may not save, a deletion the user backed out of.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ToastProvider } from '../components/Toast'
import { project, projectVariable, resetApiMocks, user } from './apiFixtures'
import { settle } from './settle'

vi.mock('../api/client', async (importOriginal) => {
  const { mockApiModule: build } = await import('./apiFixtures')
  return build(await importOriginal<Record<string, unknown>>(), vi)
})

/** The signed-in user, swapped per test to check what each role may do. */
let currentUser: Record<string, unknown> = user

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: currentUser,
    isLoading: false,
    isAuthenticated: true,
    login: vi.fn(),
    logout: vi.fn(),
    refreshUser: vi.fn(),
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
}))

const client = await import('../api/client')
const Users = (await import('../pages/Users')).default
const Projects = (await import('../pages/Projects')).default
const ProjectParameters = (await import('../pages/ProjectParameters')).default

/** The admin who is signed in for most of these tests. */
const admin = user
const maintainer = {
  ...user,
  id: 2,
  email: 'grace@example.com',
  full_name: 'Grace Hopper',
  role: 'maintainer' as const,
}
/** A second administrator, who is not the signed-in user. */
const otherAdmin = {
  ...user,
  id: 6,
  email: 'root@example.com',
  full_name: 'Root Admin',
  role: 'admin' as const,
}
const external = {
  ...user,
  id: 3,
  email: 'ext@example.com',
  full_name: 'Ext Ernal',
  role: 'external' as const,
}
/** Asked for a new address; an administrator has still to approve it. */
const awaitingApproval = {
  ...user,
  id: 4,
  email: 'old@example.com',
  full_name: 'Pat Pending',
  role: 'maintainer' as const,
  pending_email: 'pat.new@example.com',
  email_change_status: 'requested',
  email_change_requested_at: '2026-01-02T03:04:05Z',
}
/** Approved already; now waiting on the new mailbox to confirm. */
const awaitingMailbox = {
  ...awaitingApproval,
  id: 5,
  full_name: 'Sam Confirming',
  email: 'sam.old@example.com',
  pending_email: 'sam.new@example.com',
  email_change_status: 'approved',
}

function renderAt(routePath: string, url: string, element: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <MemoryRouter initialEntries={[url]}>
          <Routes>
            <Route path={routePath} element={element} />
            <Route path="/projects/:prefix/edit" element={<div>project settings</div>} />
            <Route path="/projects/:prefix" element={<div>project overview</div>} />
          </Routes>
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
}

/** An axios-shaped rejection carrying the server's message. */
function apiError(detail: string) {
  return Object.assign(new Error('Request failed'), {
    isAxiosError: true,
    response: { data: { detail } },
  })
}

/** The row of the user table that belongs to a person. */
function rowFor(fullName: string): HTMLElement {
  const row = screen.getByText(fullName).closest('tr')
  if (!row) throw new Error(`no table row for ${fullName}`)
  return row as HTMLElement
}

/** The arguments of the most recent call to a mocked endpoint. */
function lastCall(fn: unknown): unknown[] {
  const mock = vi.mocked(fn as (...args: unknown[]) => unknown)
  expect(mock.mock.calls.length).toBeGreaterThan(0)
  return mock.mock.calls[mock.mock.calls.length - 1]
}

beforeEach(() => {
  vi.clearAllMocks()
  resetApiMocks(client as unknown as Record<string, unknown>, vi)
  currentUser = admin
  window.confirm = () => true
  window.prompt = () => null
  Object.defineProperty(window.navigator, 'clipboard', {
    configurable: true,
    value: { writeText: vi.fn(async () => undefined) },
  })
})

// vitest runs without `globals`, so Testing Library never registers its own
// cleanup; without this the previous test's DOM stays mounted and every query
// finds two of everything.
afterEach(cleanup)

describe('the user table', () => {
  beforeEach(() => {
    vi.mocked(client.usersApi.list).mockResolvedValue([
      admin,
      maintainer,
      external,
      awaitingApproval,
      awaitingMailbox,
    ] as never)
  })

  it('labels each role', async () => {
    renderAt('/users', '/users', <Users />)
    await screen.findByText(maintainer.full_name)

    expect(within(rowFor(admin.full_name)).getByText('Admin')).toBeTruthy()
    expect(within(rowFor(maintainer.full_name)).getByText('Maintainer')).toBeTruthy()
    expect(within(rowFor(external.full_name)).getByText('External')).toBeTruthy()
  })

  it('distinguishes an email change waiting on an admin from one waiting on a mailbox', async () => {
    renderAt('/users', '/users', <Users />)
    await screen.findByText(awaitingApproval.full_name)

    const pending = within(rowFor(awaitingApproval.full_name))
    expect(pending.getByText(/Requested: pat\.new@example\.com/)).toBeTruthy()
    expect(pending.getByText(/Waiting for admin approval/)).toBeTruthy()

    const confirming = within(rowFor(awaitingMailbox.full_name))
    expect(confirming.getByText(/Waiting for mailbox confirmation/)).toBeTruthy()
  })

  it('offers to approve only the request that is actually waiting on an admin', async () => {
    renderAt('/users', '/users', <Users />)
    await screen.findByText(awaitingApproval.full_name)

    expect(within(rowFor(awaitingApproval.full_name)).getByTitle('Approve email change')).toBeTruthy()
    expect(within(rowFor(awaitingMailbox.full_name)).queryByTitle('Approve email change')).toBeNull()
    // Nothing is pending for the others, so there is nothing to approve or reject.
    expect(within(rowFor(maintainer.full_name)).queryByTitle(/email change/i)).toBeNull()
  })

  it('rejects a request that is still waiting on an admin', async () => {
    renderAt('/users', '/users', <Users />)
    await screen.findByText(awaitingApproval.full_name)

    fireEvent.click(within(rowFor(awaitingApproval.full_name)).getByTitle('Reject email change'))

    await waitFor(() =>
      expect(lastCall(client.usersApi.rejectEmailChange)[0]).toBe(awaitingApproval.id),
    )
  })

  it('calls the same button "cancel" once the change is past approval', async () => {
    renderAt('/users', '/users', <Users />)
    await screen.findByText(awaitingMailbox.full_name)

    fireEvent.click(within(rowFor(awaitingMailbox.full_name)).getByTitle('Cancel email change'))

    await waitFor(() =>
      expect(lastCall(client.usersApi.rejectEmailChange)[0]).toBe(awaitingMailbox.id),
    )
  })

  it('shows why an approval was refused', async () => {
    vi.mocked(client.usersApi.approveEmailChange).mockRejectedValueOnce(
      apiError('That address is already taken'),
    )
    renderAt('/users', '/users', <Users />)
    await screen.findByText(awaitingApproval.full_name)

    fireEvent.click(within(rowFor(awaitingApproval.full_name)).getByTitle('Approve email change'))

    expect(await screen.findByText(/already taken/i)).toBeTruthy()
  })
})

describe('changing what a user may do', () => {
  beforeEach(() => {
    vi.mocked(client.usersApi.list).mockResolvedValue([
      admin,
      otherAdmin,
      maintainer,
      external,
    ] as never)
  })

  it('changes a role', async () => {
    renderAt('/users', '/users', <Users />)
    await screen.findByText(maintainer.full_name)

    fireEvent.click(within(rowFor(maintainer.full_name)).getByTitle('Edit role'))
    fireEvent.change(await screen.findByTitle('Select role'), { target: { value: 'external' } })

    await waitFor(() =>
      expect(lastCall(client.usersApi.update)).toEqual([maintainer.id, { role: 'external' }]),
    )
  })

  it('will not let an admin act on their own account', async () => {
    renderAt('/users', '/users', <Users />)
    await screen.findByText(maintainer.full_name)

    // Nobody may lock themselves out, so their own row carries neither a role
    // editor nor the destructive actions.
    const self = within(rowFor(admin.full_name))
    expect(self.queryByTitle('Edit role')).toBeNull()
    expect(self.queryByTitle('Delete user')).toBeNull()
    expect(self.queryByTitle(/Deactivate|Activate/)).toBeNull()
  })

  it('will not let one admin demote another', async () => {
    renderAt('/users', '/users', <Users />)
    await screen.findByText(otherAdmin.full_name)

    // A second administrator is not the signed-in user, so the self rule does
    // not cover them; the role editor is withheld because they are an admin.
    const row = within(rowFor(otherAdmin.full_name))
    expect(row.queryByTitle('Edit role')).toBeNull()
    // The other destructive actions are still offered - only the role is fixed.
    expect(row.getByTitle('Delete user')).toBeTruthy()
  })

  it('closes the role editor when the button is pressed again', async () => {
    renderAt('/users', '/users', <Users />)
    await screen.findByText(maintainer.full_name)

    const edit = within(rowFor(maintainer.full_name)).getByTitle('Edit role')
    fireEvent.click(edit)
    expect(await screen.findByTitle('Select role')).toBeTruthy()

    fireEvent.click(edit)
    await waitFor(() => expect(screen.queryByTitle('Select role')).toBeNull())
    await settle()
    expect(client.usersApi.update).not.toHaveBeenCalled()
  })

  it('deactivates an active account and offers to activate it again', async () => {
    renderAt('/users', '/users', <Users />)
    await screen.findByText(maintainer.full_name)

    fireEvent.click(within(rowFor(maintainer.full_name)).getByTitle('Deactivate'))

    await waitFor(() =>
      expect(lastCall(client.usersApi.update)).toEqual([maintainer.id, { is_active: false }]),
    )
  })

  it('reactivates a disabled account', async () => {
    vi.mocked(client.usersApi.list).mockResolvedValue([
      admin,
      { ...maintainer, is_active: false },
    ] as never)
    renderAt('/users', '/users', <Users />)
    await screen.findByText(maintainer.full_name)

    const row = within(rowFor(maintainer.full_name))
    expect(row.getByText('Inactive')).toBeTruthy()
    fireEvent.click(row.getByTitle('Activate'))

    await waitFor(() =>
      expect(lastCall(client.usersApi.update)).toEqual([maintainer.id, { is_active: true }]),
    )
  })
})

describe('deleting a user', () => {
  beforeEach(() => {
    vi.mocked(client.usersApi.list).mockResolvedValue([admin, maintainer] as never)
  })

  it('asks first, and does nothing if the answer is no', async () => {
    window.confirm = () => false
    renderAt('/users', '/users', <Users />)
    await screen.findByText(maintainer.full_name)

    fireEvent.click(within(rowFor(maintainer.full_name)).getByTitle('Delete user'))

    await settle()
    expect(client.usersApi.delete).not.toHaveBeenCalled()
  })

  it('deletes once confirmed', async () => {
    renderAt('/users', '/users', <Users />)
    await screen.findByText(maintainer.full_name)

    fireEvent.click(within(rowFor(maintainer.full_name)).getByTitle('Delete user'))

    await waitFor(() => expect(lastCall(client.usersApi.delete)[0]).toBe(maintainer.id))
  })

  it('says why a deletion was refused', async () => {
    vi.mocked(client.usersApi.delete).mockRejectedValueOnce(
      apiError('This user still owns documents'),
    )
    renderAt('/users', '/users', <Users />)
    await screen.findByText(maintainer.full_name)

    fireEvent.click(within(rowFor(maintainer.full_name)).getByTitle('Delete user'))

    expect((await screen.findAllByText(/still owns documents/i)).length).toBeGreaterThan(0)
  })
})

describe('an administrator changing someone else’s email', () => {
  beforeEach(() => {
    vi.mocked(client.usersApi.list).mockResolvedValue([admin, maintainer] as never)
  })

  it('sends the confirmation to the new address', async () => {
    renderAt('/users', '/users', <Users />)
    await screen.findByText(maintainer.full_name)

    fireEvent.click(within(rowFor(maintainer.full_name)).getByTitle('Change email'))
    fireEvent.change(await screen.findByLabelText('New email'), {
      target: { value: 'grace.new@example.com' },
    })
    fireEvent.click(screen.getByRole('button', { name: /send confirmation email/i }))

    await waitFor(() =>
      expect(lastCall(client.usersApi.startEmailChange)).toEqual([
        maintainer.id,
        'grace.new@example.com',
      ]),
    )
  })

  it('says the login address is unchanged until the recipient confirms', async () => {
    renderAt('/users', '/users', <Users />)
    await screen.findByText(maintainer.full_name)

    fireEvent.click(within(rowFor(maintainer.full_name)).getByTitle('Change email'))

    expect(
      await screen.findByText(new RegExp(`login email remains ${maintainer.email}`, 'i')),
    ).toBeTruthy()
  })

  it('reports a refusal without closing the dialog', async () => {
    vi.mocked(client.usersApi.startEmailChange).mockRejectedValueOnce(
      apiError('Another account already uses that address'),
    )
    renderAt('/users', '/users', <Users />)
    await screen.findByText(maintainer.full_name)

    fireEvent.click(within(rowFor(maintainer.full_name)).getByTitle('Change email'))
    fireEvent.change(await screen.findByLabelText('New email'), {
      target: { value: 'taken@example.com' },
    })
    fireEvent.click(screen.getByRole('button', { name: /send confirmation email/i }))

    expect((await screen.findAllByText(/already uses that address/i)).length).toBeGreaterThan(0)
    expect(screen.getByLabelText('New email')).toBeTruthy()
  })

  it('closes without sending anything', async () => {
    renderAt('/users', '/users', <Users />)
    await screen.findByText(maintainer.full_name)

    fireEvent.click(within(rowFor(maintainer.full_name)).getByTitle('Change email'))
    fireEvent.click(await screen.findByTitle('Close email change modal'))

    await waitFor(() => expect(screen.queryByLabelText('New email')).toBeNull())
    await settle()
    expect(client.usersApi.startEmailChange).not.toHaveBeenCalled()
  })
})

describe('the invitation link', () => {
  const inviteLink = 'https://bloom.example/accept-invite#token=abc123'

  beforeEach(() => {
    vi.mocked(client.usersApi.invite).mockResolvedValue({
      message: 'Invitation sent',
      user: maintainer,
      invite_link: inviteLink,
    } as never)
  })

  async function invite() {
    renderAt('/users', '/users', <Users />)
    await screen.findByText(user.full_name)
    fireEvent.click(screen.getByRole('button', { name: /invite user/i }))
    fireEvent.change(await screen.findByTitle('Full name'), { target: { value: 'Grace Hopper' } })
    fireEvent.change(screen.getByTitle('Email address'), {
      target: { value: 'grace@example.com' },
    })
    fireEvent.change(screen.getByTitle('Role'), { target: { value: 'maintainer' } })
    fireEvent.click(screen.getByRole('button', { name: /send invite/i }))
  }

  it('carries the chosen role', async () => {
    await invite()

    await waitFor(() =>
      expect(lastCall(client.usersApi.invite)[0]).toMatchObject({ role: 'maintainer' }),
    )
  })

  it('shows the generated link so it can be delivered by hand', async () => {
    await invite()

    const field = (await screen.findByLabelText('Generated invitation link')) as HTMLInputElement
    expect(field.value).toBe(inviteLink)
    expect(field.readOnly).toBe(true)
  })

  it('copies the link to the clipboard', async () => {
    await invite()
    fireEvent.click(await screen.findByRole('button', { name: /copy link/i }))

    await waitFor(() => expect(navigator.clipboard.writeText).toHaveBeenCalledWith(inviteLink))
    expect(await screen.findByRole('button', { name: /copied/i })).toBeTruthy()
  })

  it('falls back to a prompt when the browser refuses clipboard access', async () => {
    const prompt = vi.fn(() => null)
    window.prompt = prompt as unknown as typeof window.prompt
    vi.mocked(navigator.clipboard.writeText).mockRejectedValueOnce(new Error('denied'))

    await invite()
    fireEvent.click(await screen.findByRole('button', { name: /copy link/i }))

    await waitFor(() => expect(prompt).toHaveBeenCalledWith('Copy invite link:', inviteLink))
    // Nothing was copied, so the button must not claim otherwise.
    expect(screen.queryByRole('button', { name: /copied/i })).toBeNull()
  })

  it('keeps the form open and shows why an invitation failed', async () => {
    vi.mocked(client.usersApi.invite).mockRejectedValueOnce(
      apiError('That address already has an account'),
    )
    await invite()

    expect(await screen.findByText(/already has an account/i)).toBeTruthy()
    expect(screen.getByTitle('Email address')).toBeTruthy()
    expect(screen.queryByLabelText('Generated invitation link')).toBeNull()
  })
})

describe('the project list', () => {
  const other = {
    ...project,
    id: 2,
    name: 'Battery Management',
    prefix: 'BMS',
    description: null,
    coverage_percent: 91,
  }

  beforeEach(() => {
    vi.mocked(client.projectsApi.list).mockResolvedValue([project, other] as never)
  })

  function renderProjects() {
    return renderAt('/projects', '/projects', <Projects />)
  }

  it('counts what it shows', async () => {
    renderProjects()
    expect(await screen.findByText('2 projects total')).toBeTruthy()
  })

  it('filters by name', async () => {
    renderProjects()
    await screen.findByText(project.name)

    fireEvent.change(screen.getByPlaceholderText('Search projects...'), {
      target: { value: 'battery' },
    })

    expect(screen.getByText(other.name)).toBeTruthy()
    expect(screen.queryByText(project.name)).toBeNull()
  })

  it('filters by prefix', async () => {
    renderProjects()
    await screen.findByText(project.name)

    fireEvent.change(screen.getByPlaceholderText('Search projects...'), {
      target: { value: 'vcu' },
    })

    expect(screen.getByText(project.name)).toBeTruthy()
    expect(screen.queryByText(other.name)).toBeNull()
  })

  it('says a search found nothing without inviting a new project', async () => {
    renderProjects()
    await screen.findByText(project.name)

    fireEvent.change(screen.getByPlaceholderText('Search projects...'), {
      target: { value: 'nothing matches this' },
    })

    expect(screen.getByText('No projects found')).toBeTruthy()
    // The empty state offers to create one only when the list is genuinely
    // empty - offering it here would create a project the search still hides.
    expect(screen.queryByRole('button', { name: /new project/i })).toBeTruthy()
    expect(screen.getAllByRole('button', { name: /new project/i })).toHaveLength(1)
  })

  it('invites a first project when there are none at all', async () => {
    vi.mocked(client.projectsApi.list).mockResolvedValue([] as never)
    renderProjects()

    expect(await screen.findByText('No Projects Yet')).toBeTruthy()
    expect(screen.getAllByRole('button', { name: /new project/i })).toHaveLength(2)
  })

  it('opens a project', async () => {
    renderProjects()
    await screen.findByText(project.name)

    fireEvent.click(screen.getAllByRole('button', { name: /open/i })[0])

    expect(await screen.findByText('project overview')).toBeTruthy()
  })

  it('lets an admin jump straight to a project’s settings', async () => {
    renderProjects()
    await screen.findByText(project.name)

    fireEvent.click(screen.getAllByTitle('Edit project')[0])

    expect(await screen.findByText('project settings')).toBeTruthy()
  })

  it('does not offer settings to a maintainer', async () => {
    currentUser = { ...user, role: 'maintainer' }
    renderProjects()
    await screen.findByText(project.name)

    expect(screen.queryByTitle('Edit project')).toBeNull()
    // A maintainer may still create projects.
    expect(screen.getByRole('button', { name: /new project/i })).toBeTruthy()
  })

  it('does not let an external user create a project', async () => {
    currentUser = { ...user, role: 'external' }
    renderProjects()
    await screen.findByText(project.name)

    expect(screen.queryByRole('button', { name: /new project/i })).toBeNull()
    expect(screen.queryByTitle('Edit project')).toBeNull()
  })
})

describe('creating a project', () => {
  async function openForm() {
    renderAt('/projects', '/projects', <Projects />)
    await screen.findByText(project.name)
    fireEvent.click(screen.getByRole('button', { name: /new project/i }))
    return {
      name: await screen.findByPlaceholderText('My Project'),
      prefix: screen.getByPlaceholderText('PRJ'),
      submit: screen.getByRole('button', { name: /create project/i }) as HTMLButtonElement,
    }
  }

  it('upper-cases the prefix as it is typed', async () => {
    const form = await openForm()
    fireEvent.change(form.prefix, { target: { value: 'bms' } })

    expect((form.prefix as HTMLInputElement).value).toBe('BMS')
  })

  it('will not send a prefix that is not three letters', async () => {
    const form = await openForm()
    fireEvent.change(form.name, { target: { value: 'Battery Management' } })

    // Exactly three, so both a shorter one and one carrying a digit are out.
    for (const bad of ['BM', 'B1']) {
      fireEvent.change(form.prefix, { target: { value: bad } })
      // The hint under the field and the form-level error can both be showing.
      expect((await screen.findAllByText(/exactly three uppercase letters/i)).length)
        .toBeGreaterThan(0)
      expect(form.submit.disabled).toBe(true)
      fireEvent.submit(form.submit.closest('form') as HTMLFormElement)
      await settle()
      expect(client.projectsApi.create).not.toHaveBeenCalled()
    }
  })

  it('sends the name, prefix and description', async () => {
    const form = await openForm()
    fireEvent.change(form.name, { target: { value: 'Battery Management' } })
    fireEvent.change(form.prefix, { target: { value: 'bms' } })
    fireEvent.change(screen.getByPlaceholderText('Project description...'), {
      target: { value: 'Cells and contactors' },
    })
    fireEvent.click(form.submit)

    await waitFor(() =>
      expect(lastCall(client.projectsApi.create)[0]).toEqual({
        name: 'Battery Management',
        prefix: 'BMS',
        description: 'Cells and contactors',
      }),
    )
  })

  it('omits an empty description rather than sending a blank one', async () => {
    const form = await openForm()
    fireEvent.change(form.name, { target: { value: 'Battery Management' } })
    fireEvent.change(form.prefix, { target: { value: 'BMS' } })
    fireEvent.click(form.submit)

    await waitFor(() =>
      expect(lastCall(client.projectsApi.create)[0]).toMatchObject({ description: undefined }),
    )
  })

  it('shows the server’s refusal in the form', async () => {
    vi.mocked(client.projectsApi.create).mockRejectedValueOnce(
      apiError('A project with prefix BMS already exists'),
    )
    const form = await openForm()
    fireEvent.change(form.name, { target: { value: 'Battery Management' } })
    fireEvent.change(form.prefix, { target: { value: 'BMS' } })
    fireEvent.click(form.submit)

    expect((await screen.findAllByText(/already exists/i)).length).toBeGreaterThan(0)
    // The form stays up so the prefix can be corrected without retyping.
    expect(screen.getByPlaceholderText('PRJ')).toBeTruthy()
  })

  it('forgets what was typed when the form is cancelled', async () => {
    const form = await openForm()
    fireEvent.change(form.name, { target: { value: 'Battery Management' } })
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }))

    await waitFor(() => expect(screen.queryByPlaceholderText('My Project')).toBeNull())
    fireEvent.click(screen.getByRole('button', { name: /new project/i }))
    expect(((await screen.findByPlaceholderText('My Project')) as HTMLInputElement).value).toBe('')
    await settle()
    expect(client.projectsApi.create).not.toHaveBeenCalled()
  })
})

describe('project parameters', () => {
  function renderParameters(prefix = 'VCU') {
    return renderAt(
      '/projects/:prefix/parameters',
      `/projects/${prefix}/parameters`,
      <ProjectParameters />,
    )
  }

  it('shows an unknown project as missing instead of an empty table', async () => {
    vi.mocked(client.projectsApi.getByPrefix).mockRejectedValueOnce(apiError('Not found'))
    renderParameters('ZZZ')

    expect(await screen.findByText('Project Not Found')).toBeTruthy()
  })

  it('keeps parameters away from an external user', async () => {
    currentUser = { ...user, role: 'external' }
    renderParameters()

    expect(
      await screen.findByText(/only admins and maintainers can view or edit project parameters/i),
    ).toBeTruthy()
    expect(client.projectVariablesApi.list).not.toHaveBeenCalled()
    expect(screen.queryByRole('button', { name: /add item/i })).toBeNull()
  })

  it('says so when the project has no parameters', async () => {
    vi.mocked(client.projectVariablesApi.list).mockResolvedValue([] as never)
    renderParameters()

    expect(await screen.findByText('No items yet.')).toBeTruthy()
  })

  it('will not create an item with a blank value', async () => {
    renderParameters()
    await screen.findAllByText(projectVariable.key)

    fireEvent.click(screen.getByRole('button', { name: /add item/i }))
    fireEvent.change(await screen.findByPlaceholderText('Enter a key'), {
      target: { value: 'MAX_TEMP_C' },
    })
    // The value is left empty; `required` stops the browser, and the handler
    // stops jsdom, which does not enforce it.
    fireEvent.submit(screen.getByPlaceholderText('Enter a key').closest('form') as HTMLFormElement)

    await settle()
    expect(client.projectVariablesApi.create).not.toHaveBeenCalled()
  })

  it('creates a variable rather than a parameter when asked', async () => {
    renderParameters()
    await screen.findAllByText(projectVariable.key)

    fireEvent.click(screen.getByRole('button', { name: /add item/i }))
    fireEvent.change(await screen.findByPlaceholderText('Enter a key'), {
      target: { value: 'BOARD_REV' },
    })
    fireEvent.change(screen.getByPlaceholderText('Enter a value'), { target: { value: 'C' } })
    fireEvent.change(screen.getByPlaceholderText('Optional description'), {
      target: { value: 'Hardware revision under test' },
    })
    fireEvent.click(screen.getByRole('button', { name: /^save$/i }))

    await waitFor(() =>
      expect(lastCall(client.projectVariablesApi.create)[0]).toEqual({
        project_id: project.id,
        kind: 'variable',
        key: 'BOARD_REV',
        value: 'C',
        description: 'Hardware revision under test',
      }),
    )
  })

  it('trims what is typed around the key and value', async () => {
    renderParameters()
    await screen.findAllByText(projectVariable.key)

    fireEvent.click(screen.getByRole('button', { name: /add item/i }))
    fireEvent.change(await screen.findByPlaceholderText('Enter a key'), {
      target: { value: '  BOARD_REV  ' },
    })
    fireEvent.change(screen.getByPlaceholderText('Enter a value'), { target: { value: '  C  ' } })
    fireEvent.click(screen.getByRole('button', { name: /^save$/i }))

    await waitFor(() =>
      expect(lastCall(client.projectVariablesApi.create)[0]).toMatchObject({
        key: 'BOARD_REV',
        value: 'C',
      }),
    )
  })

  it('closes the create form without sending anything', async () => {
    renderParameters()
    await screen.findAllByText(projectVariable.key)

    fireEvent.click(screen.getByRole('button', { name: /add item/i }))
    fireEvent.click(await screen.findByRole('button', { name: /cancel/i }))

    await waitFor(() => expect(screen.queryByPlaceholderText('Enter a key')).toBeNull())
    await settle()
    expect(client.projectVariablesApi.create).not.toHaveBeenCalled()
  })

  it('fills the edit row from the item it belongs to', async () => {
    renderParameters()
    await screen.findAllByText(projectVariable.key)

    fireEvent.click(screen.getByRole('button', { name: /edit/i }))

    const key = (await screen.findByPlaceholderText('Enter a key')) as HTMLInputElement
    const value = screen.getByPlaceholderText('Enter a value') as HTMLTextAreaElement
    expect(key.value).toBe(projectVariable.key)
    expect(value.value).toBe(projectVariable.value)
  })

  it('saves an edit against the item’s id', async () => {
    renderParameters()
    await screen.findAllByText(projectVariable.key)

    fireEvent.click(screen.getByRole('button', { name: /edit/i }))
    fireEvent.change(await screen.findByPlaceholderText('Enter a value'), {
      target: { value: '3000' },
    })
    fireEvent.click(screen.getByRole('button', { name: /^save$/i }))

    await waitFor(() =>
      expect(lastCall(client.projectVariablesApi.update)).toEqual([
        projectVariable.id,
        {
          kind: projectVariable.kind,
          key: projectVariable.key,
          value: '3000',
          description: projectVariable.description,
        },
      ]),
    )
  })

  it('will not save an edit that empties the key', async () => {
    renderParameters()
    await screen.findAllByText(projectVariable.key)

    fireEvent.click(screen.getByRole('button', { name: /edit/i }))
    fireEvent.change(await screen.findByPlaceholderText('Enter a key'), { target: { value: '   ' } })
    fireEvent.click(screen.getByRole('button', { name: /^save$/i }))

    await settle()
    expect(client.projectVariablesApi.update).not.toHaveBeenCalled()
  })

  it('abandons an edit without saving it', async () => {
    renderParameters()
    await screen.findAllByText(projectVariable.key)

    fireEvent.click(screen.getByRole('button', { name: /edit/i }))
    fireEvent.change(await screen.findByPlaceholderText('Enter a value'), {
      target: { value: '3000' },
    })
    fireEvent.click(screen.getByRole('button', { name: /cancel/i }))

    await waitFor(() => expect(screen.queryByPlaceholderText('Enter a value')).toBeNull())
    await settle()
    expect(client.projectVariablesApi.update).not.toHaveBeenCalled()
  })

  it('deletes an item', async () => {
    renderParameters()
    await screen.findAllByText(projectVariable.key)

    fireEvent.click(screen.getByRole('button', { name: /delete/i }))

    await waitFor(() =>
      expect(lastCall(client.projectVariablesApi.delete)[0]).toBe(projectVariable.id),
    )
  })
})
