// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const policies = [
  {
    id: 1, name: 'Read', description: '', scope: 'project', is_default: true, created_at: '', updated_at: '',
    rules: { REQ: { read: true, write: false, review: false, approve: false, delete: false, all_origins: true, visibility: [], tags: [], actions: ['comment', 'view'] } },
  },
  {
    id: 2, name: 'Field Auditor', description: '', scope: 'project', is_default: false, created_at: '', updated_at: '',
    rules: {
      REQ: { read: true, write: true, review: false, approve: false, delete: false, all_origins: false, visibility: ['customer'], tags: [4], actions: ['comment', 'create', 'edit', 'view'] },
      link: { read: true, write: false, review: false, approve: false, delete: false, all_origins: false, visibility: [], tags: [], actions: ['view'] },
    },
  },
]
const groups = [
  {
    id: 10, name: 'QA Reviewers', description: '', policy_ids: [1, 2],
    created_at: '', updated_at: '',
    members: [{ user_id: 5, email: 'q@x.io', full_name: 'Quinn' }],
    grants: [{ id: 3, project_id: 8, policy_ids: [2] }],
  },
]

const auth = vi.hoisted(() => ({ user: { role: 'admin', application_permissions: {} as Record<string, string[]> } }))
const failed = vi.hoisted(() => vi.fn())
vi.mock('../contexts/AuthContext', () => ({ useAuth: () => auth }))
vi.mock('../api/client', () => ({
  policiesApi: {
    list: vi.fn().mockResolvedValue(policies),
    create: vi.fn().mockResolvedValue(policies[1]),
    update: vi.fn().mockResolvedValue(policies[1]),
    delete: vi.fn().mockResolvedValue(undefined),
    duplicate: vi.fn().mockResolvedValue({ ...policies[0], id: 3, name: 'Read (copy)', is_default: false }),
  },
  groupsApi: {
    list: vi.fn().mockResolvedValue(groups),
    assignmentOptions: vi.fn().mockResolvedValue({ projects: [{ id: 7, name: 'Apollo', prefix: 'APO' }, { id: 8, name: 'Other', prefix: 'OTH' }], users: [
      { id: 5, email: 'q@x.io', full_name: 'Quinn' },
      { id: 6, email: 'dev@x.io', full_name: 'Dev Eloper' },
      { id: 7, email: 'iris@x.io', full_name: 'Iris Reviewer' },
    ] }),
    assign: vi.fn().mockResolvedValue([]),
    create: vi.fn().mockResolvedValue(groups[0]),
    update: vi.fn().mockResolvedValue(groups[0]),
    delete: vi.fn().mockResolvedValue(undefined),
    addMember: vi.fn().mockResolvedValue(groups[0]),
    addMembers: vi.fn().mockResolvedValue(groups[0]),
    removeMember: vi.fn().mockResolvedValue(undefined),
    addGrant: vi.fn(),
    updateGrant: vi.fn(),
    removeGrant: vi.fn(),
  },
  usersApi: {
    list: vi.fn().mockResolvedValue([
      { id: 5, email: 'q@x.io', full_name: 'Quinn' },
      { id: 6, email: 'dev@x.io', full_name: 'Dev Eloper' },
      { id: 7, email: 'iris@x.io', full_name: 'Iris Reviewer' },
      { id: 8, email: 'sam@x.io', full_name: 'Sam Author' },
    ]),
  },
  projectMembersApi: { list: vi.fn().mockResolvedValue([{ id: 3, user_id: 5, policy_group_id: 10, full_name: 'Quinn' }]) },
  projectsApi: { list: vi.fn().mockResolvedValue([{ id: 7, name: 'Apollo', prefix: 'APO' }]) },
  tagsApi: {
    list: vi.fn().mockResolvedValue([{ id: 4, name: 'Field', created_at: '' }]),
    create: vi.fn().mockResolvedValue({ id: 5, name: 'Lab', created_at: '' }),
  },
}))
vi.mock('../components/useToast', () => ({
  useToast: () => ({ saved: vi.fn(), deleted: vi.fn(), failed, notify: vi.fn() }),
}))

const api = await import('../api/client')
const GroupsPage = (await import('../pages/Groups')).default

function renderPage(view: 'groups' | 'policies' = 'groups') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const result = render(<QueryClientProvider client={client}><GroupsPage /></QueryClientProvider>)
  if (view === 'groups') {
    const tab = screen.queryByRole('tab', { name: 'Groups' })
    if (tab) fireEvent.click(tab)
  }
  return result
}

beforeEach(() => {
  vi.clearAllMocks()
  auth.user.role = 'admin'
  auth.user.application_permissions = {}
})
afterEach(cleanup)

describe('Groups and policies administration', () => {
  it('sorts policy names in either direction without changing cached policy data', async () => {
    renderPage('policies')
    await screen.findByTitle('Edit Field Auditor')
    const names = () => within(screen.getByRole('table')).getAllByRole('row').slice(1).map((row) => within(row).getAllByRole('cell')[0].textContent)
    expect(names()[0]).toBe('Field Auditor')
    fireEvent.click(screen.getByRole('columnheader', { name: 'Name' }))
    expect(names()[0]).toContain('Read')
    fireEvent.click(screen.getByRole('columnheader', { name: 'Name' }))
    expect(names()[0]).toBe('Field Auditor')
    expect(policies.map((policy) => policy.name)).toEqual(['Read', 'Field Auditor'])
    expect(api.policiesApi.update).not.toHaveBeenCalled()
  })

  it('sorts group rows by their displayed policy names, independently of policy sorting', async () => {
    vi.mocked(api.groupsApi.list).mockResolvedValueOnce([...groups, { ...groups[0], id: 11, name: 'Authors', policy_ids: [2] }])
    renderPage('groups')
    await screen.findByText('Authors')
    const names = () => within(screen.getByRole('table')).getAllByRole('row').slice(1).map((row) => within(row).getAllByRole('cell')[0].textContent)
    expect(names()).toEqual(['Authors', 'QA Reviewers'])
    fireEvent.click(screen.getByRole('columnheader', { name: 'Name' }))
    expect(names()).toEqual(['QA Reviewers', 'Authors'])
    fireEvent.click(screen.getByRole('columnheader', { name: 'Policies' }))
    expect(names()).toEqual(['Authors', 'QA Reviewers'])
    expect(api.groupsApi.update).not.toHaveBeenCalled()
  })
  it('saves independent customer Review without any other permission', async () => {
    renderPage('policies')
    fireEvent.click(await screen.findByText('New policy'))
    fireEvent.change(await screen.findByTitle('Policy name'), { target: { value: 'Customer reviewers' } })
    fireEvent.click(screen.getByLabelText('Review REQ'))
    for (const permission of ['Read', 'Write', 'Approve', 'Delete']) {
      expect((screen.getByLabelText(`${permission} REQ`) as HTMLInputElement).checked).toBe(false)
    }
    fireEvent.click(screen.getByLabelText('All origins on REQ'))
    fireEvent.click(screen.getByLabelText('Customer on REQ'))
    fireEvent.click(screen.getByText('Save policy'))
    await waitFor(() => expect(api.policiesApi.create).toHaveBeenCalledWith(expect.objectContaining({
      rules: { REQ: { read: false, write: false, review: true, approve: false, delete: false, all_origins: false, visibility: ['customer'], tags: [] } },
    })))
  })

  it('keeps Approve-implied Review on its existing resources', async () => {
    renderPage('policies')
    fireEvent.click(await screen.findByText('New policy'))
    fireEvent.click(screen.getByLabelText('Approve REQ'))
    expect((screen.getByLabelText('Review REQ') as HTMLInputElement).checked).toBe(true)
    expect((screen.getByLabelText('Review REQ') as HTMLInputElement).disabled).toBe(true)
    fireEvent.click(screen.getByLabelText('Approve RPT'))
    expect((screen.getByLabelText('Review RPT') as HTMLInputElement).checked).toBe(false)
    expect((screen.getByLabelText('Review RPT') as HTMLInputElement).disabled).toBe(false)
  })

  it('summarizes a Review-only policy without implicit Read or Approve', async () => {
    vi.mocked(api.policiesApi.list).mockResolvedValueOnce([{
      ...policies[1], name: 'Review only', scope: 'document',
      rules: { STD: { read: false, write: false, review: true, approve: false, delete: false, all_origins: true, visibility: [], tags: [] } },
    }] as never)
    renderPage('policies')
    const row = (await screen.findByTitle('Edit Review only')).closest('tr')!
    expect(within(row).getAllByRole('cell').map(cell => cell.textContent).slice(1, 4)).toEqual(['STD', 'Review', 'All'])
  })

  it('offers Review on all thirteen documents but no project or app resources', async () => {
    renderPage('policies')
    fireEvent.click(await screen.findByText('New policy'))
    for (const resource of ['REQ', 'SPEC', 'TC', 'DES', 'RSK', 'CHG', 'CPT', 'DEF', 'CMP', 'TS', 'PRT', 'RPT', 'STD']) {
      expect((screen.getByLabelText(`Review ${resource}`) as HTMLInputElement).disabled).toBe(false)
    }
    fireEvent.change(screen.getByTitle('Assignment scope'), { target: { value: 'app' } })
    for (const resource of ['baseline', 'parameter', 'link', 'project', 'users', 'access', 'application']) {
      expect((screen.getByLabelText(`Review ${resource}`) as HTMLInputElement).disabled).toBe(true)
    }
  })

  it('switches between Policies and Groups below the Access Management description', async () => {
    renderPage('policies')
    expect(screen.getByRole('heading', { level: 1, name: 'Access Management' })).toBeTruthy()
    expect(screen.getByText('Configure groups of policies and permissions by scope and origin.')).toBeTruthy()
    expect(screen.queryByRole('heading', { name: 'Access' })).toBeNull()
    const groupsTab = screen.getByRole('tab', { name: 'Groups' })
    const policiesTab = screen.getByRole('tab', { name: 'Policies' })
    expect(policiesTab.getAttribute('aria-selected')).toBe('true')
    expect(await screen.findByTitle('View Read')).toBeTruthy()
    expect(screen.queryByText('QA Reviewers')).toBeNull()
    fireEvent.click(groupsTab)
    expect(groupsTab.getAttribute('aria-selected')).toBe('true')
    expect(screen.getByRole('tabpanel', { name: 'Groups' })).toBeTruthy()
    expect(await screen.findByText('QA Reviewers')).toBeTruthy()
    expect(screen.queryByTitle('View Read')).toBeNull()
    fireEvent.click(policiesTab)
    expect(screen.getByRole('tabpanel', { name: 'Policies' })).toBeTruthy()
  })

  it('switches and focuses the views with arrow, Home and End keys', () => {
    renderPage('policies')
    const groupsTab = screen.getByRole('tab', { name: 'Groups' })
    const policiesTab = screen.getByRole('tab', { name: 'Policies' })
    fireEvent.keyDown(policiesTab, { key: 'ArrowRight' })
    expect(document.activeElement).toBe(groupsTab)
    expect(groupsTab.getAttribute('aria-selected')).toBe('true')
    fireEvent.keyDown(groupsTab, { key: 'Home' })
    expect(document.activeElement).toBe(policiesTab)
    fireEvent.keyDown(policiesTab, { key: 'End' })
    expect(document.activeElement).toBe(groupsTab)
    fireEvent.keyDown(groupsTab, { key: 'ArrowLeft' })
    expect(document.activeElement).toBe(policiesTab)
  })

  it('creates a group that owns two policies without choosing a project', async () => {
    renderPage()
    fireEvent.click(await screen.findByText('New group'))
    fireEvent.change(await screen.findByTitle('Group name'), { target: { value: 'Reviewers' } })
    fireEvent.click(screen.getByLabelText('Group policy Read'))
    fireEvent.click(screen.getByLabelText('Group policy Field Auditor'))
    expect(screen.queryByTitle('Grant a project')).toBeNull()
    fireEvent.click(screen.getByText('Save group'))
    await waitFor(() => expect(api.groupsApi.create).toHaveBeenCalledWith({ name: 'Reviewers', description: '', policy_ids: [1, 2] }))
    expect(api.projectsApi.list).not.toHaveBeenCalled()
  })

  it('shows the policy set on the group definition and preserves it when editing', async () => {
    renderPage()
    const row = (await screen.findByText('QA Reviewers')).closest('tr')!
    expect(within(row).getByText('Read, Field Auditor')).toBeTruthy()
    fireEvent.click(within(row).getByTitle('Edit group'))
    expect((await screen.findByLabelText('Group policy Read') as HTMLInputElement).checked).toBe(true)
    expect((screen.getByLabelText('Group policy Field Auditor') as HTMLInputElement).checked).toBe(true)
    fireEvent.click(screen.getByLabelText('Group policy Read'))
    fireEvent.change(screen.getByTitle('Group name'), { target: { value: 'QA Team' } })
    fireEvent.click(screen.getByText('Save group'))
    await waitFor(() => expect(api.groupsApi.update).toHaveBeenCalledWith(10, { name: 'QA Team', description: '', policy_ids: [2] }))
  })

  it('keeps group definitions separate from project people assignments', async () => {
    renderPage()
    await screen.findByText('QA Reviewers')
    expect(screen.queryByTitle('Assign to project')).toBeNull()
    expect(screen.queryByLabelText('Assignment project')).toBeNull()
    expect(api.groupsApi.assignmentOptions).not.toHaveBeenCalled()
    expect(api.groupsApi.assign).not.toHaveBeenCalled()
  })

  it('allows a separately granted Access Manager and keeps denied operations disabled', async () => {
    auth.user.role = 'maintainer'
    auth.user.application_permissions = { access: ['view', 'create', 'edit'] }
    renderPage()
    expect(await screen.findByText('QA Reviewers')).toBeTruthy()
    expect((screen.getByTitle('Edit group') as HTMLButtonElement).disabled).toBe(false)
    expect((screen.getByTitle('Delete group') as HTMLButtonElement).disabled).toBe(true)
    fireEvent.click(screen.getByRole('tab', { name: 'Policies' }))
    expect((await screen.findByTitle('Delete Field Auditor') as HTMLButtonElement).disabled).toBe(true)
  })

  it('shows compact policy columns, no count and custom origin names', async () => {
    renderPage('policies')
    const row = (await screen.findByTitle('Edit Field Auditor')).closest('tr')!
    const table = row.closest('table')!
    expect(within(table).getAllByRole('columnheader').map((header) => header.textContent)).toEqual(['Name', 'Scope', 'Permissions', 'Origins', ''])
    expect(screen.queryByLabelText('2 policies')).toBeNull()
    const cells = within(row).getAllByRole('cell')
    expect(cells[1].textContent).toBe('ProjectREQ, Link')
    expect(within(cells[2]).getByText('REQ: Write')).toBeTruthy()
    expect(within(cells[2]).getByText('Link: Read')).toBeTruthy()
    expect(cells[3].textContent).toBe('Customer, Field')
    for (const permission of ['Read', 'Write', 'Approve', 'Delete']) {
      expect(within(table).queryByRole('columnheader', { name: permission })).toBeNull()
    }
    expect(screen.queryByText('Base role')).toBeNull()
  })

  it('shows Project without enumerating resources for a full-project reading policy', async () => {
    const resources = ['REQ', 'SPEC', 'TC', 'DES', 'RSK', 'CHG', 'CPT', 'DEF', 'CMP', 'TS', 'PRT', 'RPT', 'STD', 'baseline', 'parameter', 'link', 'project']
    vi.mocked(api.policiesApi.list).mockResolvedValueOnce([{
      ...policies[0], name: 'Read Internal', scope: 'project',
      rules: Object.fromEntries(resources.map((resource) => [resource, {
        read: true, write: false, review: false, approve: false, delete: false, all_origins: true, visibility: [], tags: [],
      }])),
    }])
    renderPage('policies')
    const row = (await screen.findByTitle('View Read Internal')).closest('tr')!
    const cells = within(row).getAllByRole('cell')
    expect(cells.map((cell) => cell.textContent).slice(1, 4)).toEqual(['Project', 'Read', 'All'])
  })

  it('uses document abbreviations and consolidates identical permission and origin selections', async () => {
    vi.mocked(api.policiesApi.list).mockResolvedValueOnce([{
      ...policies[0], name: 'Document Authors', scope: 'document',
      rules: {
        REQ: { read: true, write: true, review: false, approve: false, delete: false, all_origins: true, visibility: [], tags: [] },
        TC: { read: true, write: true, review: false, approve: false, delete: false, all_origins: true, visibility: [], tags: [] },
      },
    }])
    renderPage('policies')
    const row = (await screen.findByTitle('Duplicate Document Authors')).closest('tr')!
    const cells = within(row).getAllByRole('cell')
    expect(cells.map((cell) => cell.textContent).slice(1, 4)).toEqual(['REQ, TC', 'Write', 'All'])
    expect(within(row).queryByText('Document', { exact: true })).toBeNull()
    expect(screen.queryByLabelText('1 policy')).toBeNull()
  })

  it('keeps narrower Write origins distinct from broad Read rules in the table', async () => {
    vi.mocked(api.policiesApi.list).mockResolvedValueOnce([{
      ...policies[1], name: 'Scoped Authors', scope: 'document',
      rules: {
        REQ: { read: true, write: false, review: false, approve: false, delete: false, all_origins: true, visibility: [], tags: [] },
        TC: { read: false, write: true, review: false, approve: false, delete: false, all_origins: false, visibility: ['internal', 'customer'], tags: [4] },
      },
    }])
    renderPage('policies')
    const row = (await screen.findByTitle('Edit Scoped Authors')).closest('tr')!
    const cells = within(row).getAllByRole('cell')
    expect(cells[1].textContent).toBe('REQ, TC')
    expect(within(cells[2]).getByText('REQ: Read')).toBeTruthy()
    expect(within(cells[2]).getByText('TC: Write')).toBeTruthy()
    expect(within(cells[3]).getByText('REQ: All')).toBeTruthy()
    expect(within(cells[3]).getByText('TC: Internal, Customer, Field')).toBeTruthy()
  })

  it('shows independent Approve and Delete permissions without adding Read or Write', async () => {
    vi.mocked(api.policiesApi.list).mockResolvedValueOnce([{
      ...policies[1], name: 'Sign off', scope: 'document',
      rules: { REQ: { read: false, write: false, review: true, approve: true, delete: true, all_origins: false, visibility: ['internal'], tags: [] } },
    }])
    renderPage('policies')
    const row = (await screen.findByTitle('Edit Sign off')).closest('tr')!
    const cells = within(row).getAllByRole('cell')
    expect(cells.map((cell) => cell.textContent).slice(1, 4)).toEqual(['REQ', 'Approve, Delete', 'Internal'])
  })

  it('marks Origins NA for project and app resource policies', async () => {
    vi.mocked(api.policiesApi.list).mockResolvedValueOnce([
      {
        ...policies[1], name: 'Project Editor', scope: 'project',
        rules: { project: { read: true, write: true, review: false, approve: false, delete: false, all_origins: false, visibility: [], tags: [] } },
      },
      {
        ...policies[1], id: 3, name: 'App Manager', scope: 'app',
        rules: { users: { read: true, write: true, review: false, approve: false, delete: true, all_origins: false, visibility: [], tags: [] } },
      },
    ])
    renderPage('policies')
    const projectRow = (await screen.findByTitle('Edit Project Editor')).closest('tr')!
    expect(within(projectRow).getAllByRole('cell').map((cell) => cell.textContent).slice(1, 4)).toEqual(['Project', 'Write', 'NA'])
    const appRow = screen.getByTitle('Edit App Manager').closest('tr')!
    expect(within(appRow).getAllByRole('cell').map((cell) => cell.textContent).slice(1, 4)).toEqual(['AppUsers', 'Write, Delete', 'NA'])
  })

  it('keeps an app policy compact while tying supported operations to their resources', async () => {
    vi.mocked(api.policiesApi.list).mockResolvedValueOnce([{
      ...policies[0], name: 'Management Bundle', scope: 'app',
      rules: {
        REQ: { read: true, write: true, review: true, approve: true, delete: true, all_origins: true, visibility: [], tags: [] },
        STD: { read: true, write: true, review: false, approve: false, delete: true, all_origins: true, visibility: [], tags: [] },
        project: { read: true, write: true, review: false, approve: false, delete: false, all_origins: false, visibility: [], tags: [] },
        users: { read: true, write: true, review: false, approve: false, delete: true, all_origins: false, visibility: [], tags: [] },
      },
    }])
    renderPage('policies')
    const row = (await screen.findByTitle('Duplicate Management Bundle')).closest('tr')!
    const cells = within(row).getAllByRole('cell')
    expect(cells[1].textContent).toBe('AppREQ, STD, Project, Users')
    expect(within(cells[2]).getByText('REQ: Write, Approve, Delete')).toBeTruthy()
    expect(within(cells[2]).getByText('STD, Users: Write, Delete')).toBeTruthy()
    expect(within(cells[2]).getByText('Project: Write')).toBeTruthy()
    expect(cells[2].children).toHaveLength(3)
    expect(cells[3].textContent).toBe('All')
  })

  it('saves Approve without enabling Write or Delete', async () => {
    renderPage('policies')
    fireEvent.click(await screen.findByText('New policy'))
    fireEvent.change(await screen.findByTitle('Policy name'), { target: { value: 'Sign off' } })
    fireEvent.click(screen.getByLabelText('Approve REQ'))
    for (const permission of ['Read', 'Write', 'Delete']) {
      expect((screen.getByLabelText(`${permission} REQ`) as HTMLInputElement).checked).toBe(false)
    }
    fireEvent.click(screen.getByText('Save policy'))
    await waitFor(() => expect(api.policiesApi.create).toHaveBeenCalledWith({
      name: 'Sign off', description: '', scope: 'document',
      rules: { REQ: { read: false, write: false, review: true, approve: true, delete: false, all_origins: true, visibility: [], tags: [] } },
    }))
  })

  it('includes Read while Write is selected without selecting Approve or Delete', async () => {
    renderPage('policies')
    fireEvent.click(await screen.findByText('New policy'))
    fireEvent.change(screen.getByTitle('Policy name'), { target: { value: 'TC authors' } })
    fireEvent.click(await screen.findByLabelText('Write TC'))
    const read = screen.getByLabelText('Read TC') as HTMLInputElement
    expect(read.checked).toBe(true)
    expect(read.disabled).toBe(true)
    expect((screen.getByLabelText('Approve TC') as HTMLInputElement).checked).toBe(false)
    expect((screen.getByLabelText('Delete TC') as HTMLInputElement).checked).toBe(false)
    fireEvent.click(screen.getByText('Save policy'))
    await waitFor(() => expect(api.policiesApi.create).toHaveBeenCalledWith(expect.objectContaining({
      rules: { TC: { read: true, write: true, review: false, approve: false, delete: false, all_origins: true, visibility: [], tags: [] } },
    })))
  })

  it('allows Read to be changed after Write is cleared', async () => {
    renderPage('policies')
    fireEvent.click(await screen.findByText('New policy'))
    fireEvent.click(await screen.findByLabelText('Write TC'))
    fireEvent.click(screen.getByLabelText('Write TC'))
    const read = screen.getByLabelText('Read TC') as HTMLInputElement
    expect(read.disabled).toBe(false)
    expect(read.checked).toBe(true)
    fireEvent.click(read)
    expect(read.checked).toBe(false)
  })

  it('shows All for complete application administration', async () => {
    const documents = ['REQ', 'SPEC', 'TC', 'DES', 'CHG', 'CPT', 'DEF', 'TS', 'PRT', 'RPT', 'RSK', 'CMP', 'STD']
    const approvable = new Set(['REQ', 'SPEC', 'TC', 'DES', 'CHG', 'CPT', 'DEF', 'TS', 'PRT', 'RPT'])
    vi.mocked(api.policiesApi.list).mockResolvedValueOnce([{
      ...policies[0], name: 'Application Administration', scope: 'app',
      rules: Object.fromEntries([...documents, 'baseline', 'parameter', 'link', 'project', 'users', 'access', 'application'].map((resource) => [resource, {
        read: true, write: true, review: documents.includes(resource), approve: approvable.has(resource), delete: resource !== 'project', all_origins: documents.includes(resource), visibility: [], tags: [],
      }])),
    }])
    renderPage('policies')
    const row = (await screen.findByTitle('Duplicate Application Administration')).closest('tr')!
    expect(within(row).getAllByRole('cell')[2].textContent).toBe('All')
    expect(within(row).queryByText(/REQ.*Write/)).toBeNull()
  })

  it('inspects a protected policy without duplicating or saving it', async () => {
    renderPage('policies')
    fireEvent.click(await screen.findByTitle('View Read'))
    expect(await screen.findByRole('heading', { name: 'View policy' })).toBeTruthy()
    expect((screen.getByLabelText('Read REQ') as HTMLInputElement).checked).toBe(true)
    expect((screen.getByLabelText('Read REQ') as HTMLInputElement).disabled).toBe(true)
    expect((screen.getByLabelText('All origins on REQ') as HTMLInputElement).checked).toBe(true)
    expect(screen.queryByText('Save policy')).toBeNull()
    expect(api.policiesApi.duplicate).not.toHaveBeenCalled()
    expect(api.policiesApi.create).not.toHaveBeenCalled()
    expect(api.policiesApi.update).not.toHaveBeenCalled()
  })

  it('embeds built-in and custom origins in one selector and saves their selection', async () => {
    renderPage('policies')
    fireEvent.click(await screen.findByText('New policy'))
    fireEvent.change(await screen.findByTitle('Policy name'), { target: { value: 'Site Viewers' } })
    expect(screen.queryByRole('heading', { name: 'Tags' })).toBeNull()
    fireEvent.change(screen.getByTitle('New origin'), { target: { value: 'Lab' } })
    fireEvent.click(screen.getByText('Add origin'))
    await waitFor(() => expect(api.tagsApi.create).toHaveBeenCalledWith('Lab'))
    expect((screen.getByLabelText('Field on REQ') as HTMLInputElement).disabled).toBe(true)
    fireEvent.click(screen.getByLabelText('Read REQ'))
    expect((screen.getByLabelText('All origins on REQ') as HTMLInputElement).checked).toBe(true)
    fireEvent.click(screen.getByLabelText('Customer on REQ'))
    fireEvent.click(screen.getByLabelText('Field on REQ'))
    expect((screen.getByLabelText('All origins on REQ') as HTMLInputElement).checked).toBe(false)
    fireEvent.click(screen.getByText('Save policy'))
    await waitFor(() => expect(api.policiesApi.create).toHaveBeenCalledWith({
      name: 'Site Viewers', description: '', scope: 'document',
      rules: { REQ: { read: true, write: false, review: false, approve: false, delete: false, all_origins: false, visibility: ['customer'], tags: [4] } },
    }))
  })

  it('All origins replaces a selected subset in the outgoing rule', async () => {
    renderPage('policies')
    fireEvent.click(await screen.findByTitle('Edit Field Auditor'))
    fireEvent.click(await screen.findByLabelText('All origins on REQ'))
    expect((screen.getByLabelText('Customer on REQ') as HTMLInputElement).checked).toBe(false)
    expect((screen.getByLabelText('Field on REQ') as HTMLInputElement).checked).toBe(false)
    fireEvent.click(screen.getByText('Save policy'))
    await waitFor(() => expect(api.policiesApi.update).toHaveBeenCalledWith(2, expect.objectContaining({
      rules: expect.objectContaining({ REQ: { read: true, write: true, review: false, approve: false, delete: false, all_origins: true, visibility: [], tags: [] } }),
    })))
  })

  it('requires an origin for an active document rule after All is cleared', async () => {
    renderPage('policies')
    fireEvent.click(await screen.findByText('New policy'))
    fireEvent.click(await screen.findByLabelText('Read SPEC'))
    fireEvent.click(screen.getByLabelText('All origins on SPEC'))
    expect(screen.getByText('Choose at least one origin for SPEC.')).toBeTruthy()
    expect((screen.getByText('Save policy') as HTMLButtonElement).disabled).toBe(true)
  })

  it('limits resources to assignment scope and disables unsupported Approve operations', async () => {
    renderPage('policies')
    fireEvent.click(await screen.findByText('New policy'))
    for (const resource of ['STD', 'RSK', 'CMP']) {
      expect((await screen.findByLabelText(`Approve ${resource}`) as HTMLInputElement).disabled).toBe(true)
    }
    expect(screen.queryByLabelText('Read baseline')).toBeNull()
    fireEvent.change(screen.getByTitle('Assignment scope'), { target: { value: 'project' } })
    for (const resource of ['baseline', 'parameter', 'link', 'project']) {
      expect(screen.getByLabelText(`Read ${resource}`)).toBeTruthy()
      expect((screen.getByLabelText(`Approve ${resource}`) as HTMLInputElement).disabled).toBe(true)
    }
    expect((screen.getByLabelText('Delete project') as HTMLInputElement).disabled).toBe(true)
    fireEvent.change(screen.getByTitle('Assignment scope'), { target: { value: 'app' } })
    for (const resource of ['access', 'users', 'application']) {
      expect(screen.getByLabelText(`Read ${resource}`)).toBeTruthy()
      expect((screen.getByLabelText(`Approve ${resource}`) as HTMLInputElement).disabled).toBe(true)
    }
  })

  it('saves application resources under App scope with independent permissions', async () => {
    renderPage('policies')
    fireEvent.click(await screen.findByText('New policy'))
    fireEvent.change(await screen.findByTitle('Policy name'), { target: { value: 'Management' } })
    fireEvent.change(screen.getByTitle('Assignment scope'), { target: { value: 'app' } })
    fireEvent.click(screen.getByLabelText('Read access'))
    fireEvent.click(screen.getByLabelText('Write users'))
    fireEvent.click(screen.getByLabelText('Delete application'))
    fireEvent.click(screen.getByText('Save policy'))
    await waitFor(() => expect(api.policiesApi.create).toHaveBeenCalledWith({
      name: 'Management', description: '', scope: 'app',
      rules: {
        users: { read: true, write: true, review: false, approve: false, delete: false, all_origins: false, visibility: [], tags: [] },
        access: { read: true, write: false, review: false, approve: false, delete: false, all_origins: false, visibility: [], tags: [] },
        application: { read: false, write: false, review: false, approve: false, delete: true, all_origins: false, visibility: [], tags: [] },
      },
    }))
  })

  it('offers a newly created origin in the same document selector', async () => {
    vi.mocked(api.tagsApi.list)
      .mockResolvedValueOnce([{ id: 4, name: 'Field', created_at: '' }])
      .mockResolvedValueOnce([{ id: 4, name: 'Field', created_at: '' }, { id: 5, name: 'Lab', created_at: '' }])
    renderPage('policies')
    fireEvent.click(await screen.findByText('New policy'))
    fireEvent.change(await screen.findByTitle('Policy name'), { target: { value: 'Lab Viewers' } })
    fireEvent.change(screen.getByTitle('New origin'), { target: { value: 'Lab' } })
    fireEvent.click(screen.getByText('Add origin'))
    const origin = await screen.findByLabelText('Lab on REQ')
    fireEvent.click(screen.getByLabelText('Read REQ'))
    fireEvent.click(origin)
    fireEvent.click(screen.getByText('Save policy'))
    await waitFor(() => expect(api.policiesApi.create).toHaveBeenCalledWith(expect.objectContaining({
      rules: { REQ: { read: true, write: false, review: false, approve: false, delete: false, all_origins: false, visibility: [], tags: [5] } },
    })))
  })

  it('does not submit rules outside a changed assignment scope', async () => {
    renderPage('policies')
    fireEvent.click(await screen.findByTitle('Edit Field Auditor'))
    fireEvent.change(await screen.findByTitle('Assignment scope'), { target: { value: 'document' } })
    fireEvent.click(screen.getByText('Save policy'))
    await waitFor(() => expect(api.policiesApi.update).toHaveBeenCalledWith(2, expect.objectContaining({ scope: 'document' })))
    expect(vi.mocked(api.policiesApi.update).mock.calls[0][1].rules).toEqual({
      REQ: { read: true, write: true, review: false, approve: false, delete: false, all_origins: false, visibility: ['customer'], tags: [4] },
    })
  })

  it('offers View and Duplicate on a shipped policy and edits the copy', async () => {
    renderPage('policies')
    await screen.findByTitle('Duplicate Read')
    expect(screen.queryByTitle('Edit Read')).toBeNull()
    expect(screen.queryByTitle('Delete Read')).toBeNull()
    fireEvent.click(screen.getByTitle('Duplicate Read'))
    await waitFor(() => expect(api.policiesApi.duplicate).toHaveBeenCalledWith(1))
    expect(await screen.findByDisplayValue('Read (copy)')).toBeTruthy()
  })

  it('reports failures to add an origin or duplicate a policy', async () => {
    vi.mocked(api.tagsApi.create).mockRejectedValueOnce(new Error('taken'))
    vi.mocked(api.policiesApi.duplicate).mockRejectedValueOnce(new Error('no'))
    renderPage('policies')
    fireEvent.click(await screen.findByText('New policy'))
    fireEvent.change(await screen.findByTitle('New origin'), { target: { value: 'Lab' } })
    fireEvent.click(screen.getByText('Add origin'))
    await waitFor(() => expect(failed).toHaveBeenCalledWith('Adding the origin', expect.any(Error)))
    fireEvent.click(screen.getByTitle('Close'))
    fireEvent.click(await screen.findByTitle('Duplicate Read'))
    await waitFor(() => expect(failed).toHaveBeenCalledWith('Duplicating the policy', expect.any(Error)))
  })

  it('drops a rule once every independent permission is unticked and omits derived actions', async () => {
    renderPage('policies')
    fireEvent.click(await screen.findByTitle('Edit Field Auditor'))
    fireEvent.click(await screen.findByLabelText('Read link'))
    fireEvent.click(screen.getByText('Save policy'))
    await waitFor(() => expect(api.policiesApi.update).toHaveBeenCalled())
    expect(vi.mocked(api.policiesApi.update).mock.calls[0][1].rules).toEqual({
      REQ: { read: true, write: true, review: false, approve: false, delete: false, all_origins: false, visibility: ['customer'], tags: [4] },
    })
  })

  it('does not load administrator controls for a non-administrator', () => {
    auth.user.role = 'external'
    renderPage()
    expect(screen.queryByText('New policy')).toBeNull()
    expect(api.policiesApi.list).not.toHaveBeenCalled()
    expect(api.groupsApi.list).not.toHaveBeenCalled()
    expect(api.tagsApi.list).not.toHaveBeenCalled()
  })

  it('deletes a non-default policy', async () => {
    renderPage('policies')
    fireEvent.click(await screen.findByTitle('Delete Field Auditor'))
    await waitFor(() => expect(api.policiesApi.delete).toHaveBeenCalledWith(2))
  })

  it('deletes a group', async () => {
    renderPage()
    fireEvent.click(await screen.findByTitle('Delete group'))
    await waitFor(() => expect(api.groupsApi.delete).toHaveBeenCalledWith(10))
  })
})
