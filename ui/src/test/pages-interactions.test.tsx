// @vitest-environment jsdom
/**
 * The things a user does on each screen, driven through the real components.
 *
 * Rendering a page proves it mounts; these prove it *works* - that typing in
 * the registry search reaches the API as a query, that creating a defect sends
 * the form, that deleting asks first and then deletes, and that a failed save
 * says so instead of failing silently. Every assertion is on a call the page
 * makes or on text the user would read.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { settle } from './settle'

import { ToastProvider } from '../components/Toast'
import {
  RESPONSES,
  defect,
  docShell,
  project,
  requirement,
  testCase,
  testSuite,
  user,
} from './apiFixtures'

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  const mocked: Record<string, unknown> = { ...actual }
  for (const [groupName, group] of Object.entries(actual)) {
    if (!groupName.endsWith('Api') || typeof group !== 'object' || group === null) continue
    const replacement: Record<string, unknown> = {}
    for (const [method, value] of Object.entries(group)) {
      if (typeof value !== 'function') {
        replacement[method] = value
        continue
      }
      const key = `${groupName}.${method}`
      replacement[method] = vi.fn(async () => {
        if (!(key in RESPONSES)) throw new Error(`no fixture for ${key}`)
        return RESPONSES[key]
      })
    }
    mocked[groupName] = replacement
  }
  return mocked
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

vi.mock('../components/editor/DocEditor', () => ({
  default: () => <div data-testid="doc-editor" />,
}))

vi.mock('../components/ProjectDocTopology', () => ({
  default: () => <div data-testid="doc-topology" />,
}))

const client = await import('../api/client')
const Documents = (await import('../pages/Documents')).default
const Defects = (await import('../pages/Defects')).default
const Users = (await import('../pages/Users')).default
const Baselines = (await import('../pages/Baselines')).default
const ProjectParameters = (await import('../pages/ProjectParameters')).default
const TraceabilityMatrix = (await import('../pages/TraceabilityMatrix')).default
const ProjectEdit = (await import('../pages/ProjectEdit')).default
const SuiteDetail = (await import('../pages/SuiteDetail')).default
const CampaignDetail = (await import('../pages/CampaignDetail')).default
const Settings = (await import('../pages/Settings')).default
const RequirementDetail = (await import('../pages/RequirementDetail')).default
const TestCaseDetail = (await import('../pages/TestCaseDetail')).default
const DocumentDetail = (await import('../pages/DocumentDetail')).default
const DocCreate = (await import('../pages/DocCreate')).default
const ArtefactDetail = (await import('../pages/ArtefactDetail')).default
const TestCampaigns = (await import('../pages/TestCampaigns')).default
const ImportWizard = (await import('../pages/ImportWizard')).default

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
          </Routes>
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  window.sessionStorage.clear()
  window.localStorage.clear()
  window.confirm = () => true
  window.matchMedia = ((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia
})

// vitest runs without `globals`, so Testing Library never registers its own
// cleanup; without this the previous test's DOM stays mounted and every query
// finds two of everything.
afterEach(cleanup)

/** The arguments of the most recent call to a mocked endpoint. */
function lastCall(fn: unknown): unknown[] {
  const mock = vi.mocked(fn as (...args: unknown[]) => unknown)
  expect(mock.mock.calls.length).toBeGreaterThan(0)
  return mock.mock.calls[mock.mock.calls.length - 1]
}

describe('the document registry', () => {
  it('sends the search term to the server rather than filtering what it holds', async () => {
    renderAt('/projects/:prefix/docs', '/projects/VCU/docs', <Documents />)
    await screen.findAllByText('VCU-REQ-001')

    fireEvent.change(screen.getByPlaceholderText(/search/i), { target: { value: 'brownout' } })

    // The registry no longer holds the project - it holds one page of it - so
    // a search it answers locally is a search over the wrong set.
    await waitFor(() => {
      const [, params] = lastCall(client.docsApi.list) as [string, { q?: string }]
      expect(params.q).toBe('brownout')
    })
  })

  it('asks the server again when a document type is picked', async () => {
    renderAt('/projects/:prefix/docs', '/projects/VCU/docs', <Documents />)
    await screen.findAllByText('VCU-REQ-001')

    fireEvent.click(screen.getAllByRole('button', { name: /^Filters/ })[0])
    // The kind chips are labelled with the type code the API expects.
    fireEvent.click(await screen.findByRole('button', { name: 'TC' }))

    await waitFor(() => {
      const [, params] = lastCall(client.docsApi.list) as [string, { type?: string[] }]
      expect(params.type).toContain('TC')
    })
  })

  it('carries the priority, reviewer and link filters to the server', async () => {
    renderAt('/projects/:prefix/docs', '/projects/VCU/docs', <Documents />)
    await screen.findAllByText('VCU-REQ-001')
    fireEvent.click(screen.getAllByRole('button', { name: /^Filters/ })[0])

    fireEvent.change(await screen.findByLabelText(/Priority/i), { target: { value: 'Low' } })
    fireEvent.change(screen.getByLabelText(/Reviewer/i), { target: { value: 'assigned' } })
    fireEvent.change(screen.getByLabelText(/Links/i), { target: { value: 'suspect' } })

    await waitFor(() => {
      const [, params] = lastCall(client.docsApi.list) as [
        string,
        { priority?: string; reviewer?: string; links?: string },
      ]
      expect(params).toMatchObject({
        priority: 'Low',
        reviewer: 'assigned',
        links: 'suspect',
      })
    })
  })

  it('keeps the filters in the URL so a filtered view can be shared', async () => {
    renderAt('/projects/:prefix/docs', '/projects/VCU/docs', <Documents />)
    await screen.findAllByText('VCU-REQ-001')

    fireEvent.change(screen.getByPlaceholderText(/search/i), { target: { value: 'boot' } })

    // The registry reads its state back out of the query string.
    await waitFor(() =>
      expect((screen.getByPlaceholderText(/search/i) as HTMLInputElement).value).toBe('boot'),
    )
  })

  it('asks the server to sort by the column whose header is clicked', async () => {
    renderAt('/projects/:prefix/docs', '/projects/VCU/docs', <Documents />)
    await screen.findAllByText('VCU-REQ-001')

    fireEvent.click(screen.getByText('Name / Title').closest('th') as HTMLElement)

    await waitFor(() => {
      const [, params] = lastCall(client.docsApi.list) as [string, { sort?: string; dir?: string }]
      // Text columns open ascending; the ordering itself is the server's.
      expect(params).toMatchObject({ sort: 'title', dir: 'asc' })
    })
  })

  it('clears every filter at once', async () => {
    renderAt('/projects/:prefix/docs', '/projects/VCU/docs', <Documents />)
    await screen.findAllByText('VCU-REQ-001')

    fireEvent.change(screen.getByPlaceholderText(/search/i), { target: { value: 'nothing' } })
    await waitFor(() => {
      const [, params] = lastCall(client.docsApi.list) as [string, { q?: string }]
      expect(params.q).toBe('nothing')
    })

    fireEvent.click(await screen.findByRole('button', { name: /clear/i }))

    await waitFor(() => {
      const [, params] = lastCall(client.docsApi.list) as [string, { q?: string }]
      expect(params.q).toBeUndefined()
    })
  })

  it('scopes the request to the project in the URL', async () => {
    renderAt('/projects/:prefix/docs', '/projects/VCU/docs', <Documents />)
    await screen.findAllByText('VCU-REQ-001')
    expect(lastCall(client.docsApi.list)[0]).toBe('VCU')
  })
})

describe('raising a defect', () => {
  it('sends the form and reports success', async () => {
    renderAt('/projects/:prefix/defects', '/projects/VCU/defects', <Defects />)
    await screen.findAllByText(defect.title)

    fireEvent.click(screen.getByRole('button', { name: /new defect/i }))
    fireEvent.change(await screen.findByTitle('Title'), { target: { value: 'Fan runs constantly' } })
    fireEvent.click(screen.getByRole('button', { name: /^create defect$/i }))

    await waitFor(() => {
      const [payload] = lastCall(client.defectsApi.create) as [{ title: string; project_id: number }]
      expect(payload.title).toBe('Fan runs constantly')
      expect(payload.project_id).toBe(project.id)
    })
  })

  it('says so when the server rejects it', async () => {
    vi.mocked(client.defectsApi.create).mockRejectedValueOnce(
      Object.assign(new Error('Request failed'), {
        isAxiosError: true,
        response: { data: { detail: 'A defect with that title already exists' } },
      }),
    )
    renderAt('/projects/:prefix/defects', '/projects/VCU/defects', <Defects />)
    await screen.findAllByText(defect.title)

    fireEvent.click(screen.getByRole('button', { name: /new defect/i }))
    fireEvent.change(await screen.findByTitle('Title'), { target: { value: 'Duplicate' } })
    fireEvent.click(screen.getByRole('button', { name: /^create defect$/i }))

    expect((await screen.findAllByText(/already exists/i)).length).toBeGreaterThan(0)
  })

  it('filters the list without going back to the server', async () => {
    renderAt('/projects/:prefix/defects', '/projects/VCU/defects', <Defects />)
    await screen.findAllByText(defect.title)

    fireEvent.change(screen.getByPlaceholderText(/search id, title, status/i), { target: { value: 'nothing matches' } })

    await waitFor(() => expect(screen.queryAllByText(defect.title)).toHaveLength(0))
  })
})

describe('inviting a user', () => {
  it('sends the invitation', async () => {
    renderAt('/users', '/users', <Users />)
    await screen.findByText(user.full_name)

    fireEvent.click(screen.getByRole('button', { name: /invite user/i }))
    fireEvent.change(await screen.findByTitle('Full name'), { target: { value: 'Grace Hopper' } })
    fireEvent.change(screen.getByTitle('Email address'), { target: { value: 'grace@example.com' } })
    fireEvent.click(screen.getByRole('button', { name: /send invite/i }))

    await waitFor(() => {
      const [payload] = lastCall(client.usersApi.invite) as [{ email: string; full_name: string }]
      expect(payload).toMatchObject({ email: 'grace@example.com', full_name: 'Grace Hopper' })
    })
  })
})

describe('project parameters', () => {
  it('creates a parameter', async () => {
    renderAt('/projects/:prefix/parameters', '/projects/VCU/parameters', <ProjectParameters />)
    await screen.findAllByText('BOOT_BUDGET_MS')

    fireEvent.click(screen.getByRole('button', { name: /add item/i }))
    fireEvent.change(await screen.findByPlaceholderText('Enter a key'), {
      target: { value: 'MAX_TEMP_C' },
    })
    fireEvent.change(screen.getByPlaceholderText('Enter a value'), { target: { value: '85' } })
    fireEvent.click(screen.getByRole('button', { name: /^save$/i }))

    await waitFor(() => {
      const [payload] = lastCall(client.projectVariablesApi.create) as [
        { key: string; value: string; project_id: number },
      ]
      expect(payload).toMatchObject({ key: 'MAX_TEMP_C', value: '85', project_id: project.id })
    })
  })
})

describe('baselines', () => {
  it('creates one for the project', async () => {
    renderAt('/projects/:prefix/baselines', '/projects/VCU/baselines', <Baselines />)
    await screen.findAllByText(/Release 1\.0/i)

    fireEvent.click(screen.getAllByRole('button', { name: /new baseline/i })[0])
    expect(await screen.findByRole('heading', { name: 'Create Baseline' })).toBeTruthy()
    // The project field is fixed by the route, so the name is the first input
    // the form leaves editable.
    const editable = screen
      .getAllByRole('textbox')
      .filter((field) => !(field as HTMLInputElement).disabled)
    fireEvent.change(editable[0], { target: { value: 'Release 2.0' } })
    fireEvent.click(screen.getByRole('button', { name: 'Create Baseline' }))

    await waitFor(() => {
      const [payload] = lastCall(client.baselinesApi.create) as [{ name: string }]
      expect(payload.name).toBe('Release 2.0')
    })
  })
})

describe('the traceability matrix', () => {
  it('re-requests when a coverage filter is chosen', async () => {
    renderAt('/projects/:prefix/traceability', '/projects/VCU/traceability', <TraceabilityMatrix />)
    await screen.findAllByText(/VCU-REQ-001/i)

    const filters = screen.getAllByRole('combobox')
    fireEvent.change(filters[0], { target: { value: 'Uncovered' } })

    await waitFor(() => {
      const [, params] = lastCall(client.traceabilityApi.getMatrix) as [
        number,
        { coverage_filter?: string },
      ]
      expect(params.coverage_filter).toBe('Uncovered')
    })
  })

  it('shows the coverage figures the gap report returns', async () => {
    renderAt('/projects/:prefix/traceability', '/projects/VCU/traceability', <TraceabilityMatrix />)
    const heading = await screen.findAllByText(/33\.3/)
    expect(heading.length).toBeGreaterThan(0)
  })
})

describe('the registry table', () => {
  it('links each row to the document it represents', async () => {
    renderAt('/projects/:prefix/docs', '/projects/VCU/docs', <Documents />)
    const cells = await screen.findAllByText('VCU-REQ-001')
    const link = cells.map((cell) => cell.closest('a')).find(Boolean)
    expect(link?.getAttribute('href')).toContain('/projects/VCU/docs/requirements/VCU-REQ-001')
  })

  it('shows the last execution for test cases only', async () => {
    renderAt('/projects/:prefix/docs', '/projects/VCU/docs', <Documents />)
    await screen.findByText('VCU-TC-001')

    const table = screen.getByRole('table')
    // Both fixtures carry an execution status; only the test-case row shows it.
    expect(within(table).getAllByText('Passed')).toHaveLength(1)
  })

  it('links the execution to Bud only once a Bud URL is configured', async () => {
    renderAt('/projects/:prefix/docs', '/projects/VCU/docs', <Documents />)
    await screen.findByText('VCU-TC-001')
    // Nothing is configured, so the run is named but not linked.
    expect(screen.getByText('Bud run #77').closest('a')).toBeNull()
    cleanup()

    ;(window as Window & { runtimeConfig?: { BUD_APP_URL?: string } }).runtimeConfig = {
      BUD_APP_URL: 'https://bud.example.com/api/',
    }
    renderAt('/projects/:prefix/docs', '/projects/VCU/docs', <Documents />)
    await screen.findByText('VCU-TC-001')

    expect(screen.getByText('Bud run #77').closest('a')?.getAttribute('href')).toBe(
      'https://bud.example.com/runs/77',
    )
    delete (window as Window & { runtimeConfig?: unknown }).runtimeConfig
  })
})


describe('creating a document', () => {
  it('shows the identifier the server would actually assign', async () => {
    renderAt('/projects/:prefix/docs/new', '/projects/VCU/docs/new?type=REQ', <DocCreate />)

    // Not a hardcoded "-001": the create screen asks for the next free one.
    expect(await screen.findByText(/VCU-REQ-004/)).toBeTruthy()
    expect(lastCall(client.docsApi.nextDocId)).toEqual(['VCU', 'REQ'])
  })

  it('will not save an untitled document', async () => {
    renderAt('/projects/:prefix/docs/new', '/projects/VCU/docs/new?type=REQ', <DocCreate />)
    await screen.findByText(/VCU-REQ-004/)

    const save = screen.getByRole('button', { name: /^save$/i }) as HTMLButtonElement
    expect(save.disabled).toBe(true)

    fireEvent.change(screen.getByPlaceholderText('Untitled'), {
      target: { value: 'The system shall boot' },
    })
    expect((screen.getByRole('button', { name: /^save$/i }) as HTMLButtonElement).disabled).toBe(
      false,
    )
  })

  it('sends the title and the project it belongs to', async () => {
    renderAt('/projects/:prefix/docs/new', '/projects/VCU/docs/new?type=REQ', <DocCreate />)
    await screen.findByText(/VCU-REQ-004/)

    fireEvent.change(screen.getByPlaceholderText('Untitled'), {
      target: { value: 'The system shall boot' },
    })
    fireEvent.click(screen.getByRole('button', { name: /^save$/i }))

    await waitFor(() => {
      const [payload] = lastCall(client.requirementsApi.create) as [
        { title: string; project_id: number },
      ]
      expect(payload.title).toBe('The system shall boot')
      expect(payload.project_id).toBe(project.id)
    })
  })

  it('reports the reason the server gives for refusing a save', async () => {
    vi.mocked(client.requirementsApi.create).mockRejectedValueOnce(
      Object.assign(new Error('Request failed'), {
        isAxiosError: true,
        response: { data: { detail: 'A requirement with that title already exists' } },
      }),
    )
    renderAt('/projects/:prefix/docs/new', '/projects/VCU/docs/new?type=REQ', <DocCreate />)
    await screen.findByText(/VCU-REQ-004/)

    fireEvent.change(screen.getByPlaceholderText('Untitled'), { target: { value: 'Duplicate' } })
    fireEvent.click(screen.getByRole('button', { name: /^save$/i }))

    expect((await screen.findAllByText(/already exists/i)).length).toBeGreaterThan(0)
  })

  it('shows the metadata sidebar, and lets it be put away', async () => {
    renderAt('/projects/:prefix/docs/new', '/projects/VCU/docs/new?type=REQ', <DocCreate />)
    await screen.findByText(/VCU-REQ-004/)

    expect(screen.getByTitle('Select status')).toBeTruthy()

    fireEvent.click(screen.getByTitle('Hide metadata'))
    await waitFor(() => expect(screen.queryByTitle('Select status')).toBeNull())

    fireEvent.click(screen.getByTitle('Show metadata'))
    expect(await screen.findByTitle('Select status')).toBeTruthy()
  })

  it('sends the metadata alongside the title', async () => {
    renderAt('/projects/:prefix/docs/new', '/projects/VCU/docs/new?type=REQ', <DocCreate />)
    await screen.findByText(/VCU-REQ-004/)

    fireEvent.change(screen.getByPlaceholderText('Untitled'), { target: { value: 'A requirement' } })
    fireEvent.change(screen.getByTitle('Select status'), { target: { value: 'Approved' } })
    fireEvent.change(screen.getByPlaceholderText(/brief description/i), {
      target: { value: 'Why it exists.' },
    })
    fireEvent.click(screen.getByRole('button', { name: /^save$/i }))

    await waitFor(() => {
      const [payload] = lastCall(client.requirementsApi.create) as [Record<string, unknown>]
      expect(payload.status).toBe('Approved')
      expect(payload.description).toBe('Why it exists.')
    })
  })

  it('creates a test case through the test-case endpoint, not the generic one', async () => {
    renderAt('/projects/:prefix/docs/new', '/projects/VCU/docs/new?type=TC', <DocCreate />)
    await screen.findByPlaceholderText('Untitled')

    fireEvent.change(screen.getByPlaceholderText('Untitled'), { target: { value: 'Cold boot' } })
    fireEvent.click(screen.getByRole('button', { name: /^save$/i }))

    await waitFor(() => expect(client.testCasesApi.create).toHaveBeenCalled())
    await settle()
    expect(client.documentsApi.create).not.toHaveBeenCalled()
  })
})

describe('editing an existing document', () => {
  function renderEdit() {
    return renderAt(
      '/projects/:prefix/docs/:kind/:docId/edit',
      '/projects/VCU/docs/requirements/VCU-REQ-001/edit',
      <DocCreate editMode />,
    )
  }

  it('loads the document the URL names', async () => {
    renderEdit()
    await waitFor(() => expect(client.docsApi.get).toHaveBeenCalled())
    const [prefix, kind, docId] = lastCall(client.docsApi.get) as [string, string, string]
    expect(prefix).toBe('VCU')
    expect(kind).toBe('requirements')
    expect(docId).toBe('VCU-REQ-001')

    const title = (await screen.findByPlaceholderText('Untitled')) as HTMLInputElement
    await waitFor(() => expect(title.value).toBe(docShell.title))
  })

  it('never asks for a new identifier when editing', async () => {
    renderEdit()
    await screen.findByPlaceholderText('Untitled')
    // The document already has one; asking would show a misleading number.
    expect(client.docsApi.nextDocId).not.toHaveBeenCalled()
  })

  it('updates rather than creating', async () => {
    renderEdit()
    const title = (await screen.findByPlaceholderText('Untitled')) as HTMLInputElement
    await waitFor(() => expect(title.value).toBe(docShell.title))

    fireEvent.change(title, { target: { value: 'The system shall boot in 3 seconds' } })
    fireEvent.click(screen.getByRole('button', { name: /^save$/i }))

    await waitFor(() => expect(client.requirementsApi.update).toHaveBeenCalled())
    const [id, payload] = lastCall(client.requirementsApi.update) as [number, { title?: string }]
    expect(id).toBe(docShell.id)
    expect(payload.title).toBe('The system shall boot in 3 seconds')
    await settle()
    expect(client.requirementsApi.create).not.toHaveBeenCalled()
  })

  it('asks before deleting, and deletes when told to', async () => {
    renderEdit()
    await screen.findByPlaceholderText('Untitled')

    window.confirm = () => false
    fireEvent.click(await screen.findByRole('button', { name: /^delete$/i }))
    await settle()
    expect(client.requirementsApi.delete).not.toHaveBeenCalled()

    window.confirm = () => true
    fireEvent.click(screen.getByRole('button', { name: /^delete$/i }))
    await waitFor(() => expect(client.requirementsApi.delete).toHaveBeenCalledWith(docShell.id))
  })

  it('offers no delete on a document that does not exist yet', async () => {
    renderAt('/projects/:prefix/docs/new', '/projects/VCU/docs/new?type=REQ', <DocCreate />)
    await screen.findByText(/VCU-REQ-004/)

    expect(screen.queryByRole('button', { name: /^delete$/i })).toBeNull()
  })
})

describe('a defect in detail', () => {
  function renderDefect() {
    return renderAt(
      '/projects/:prefix/defects/:itemId',
      '/projects/VCU/defects/51',
      <ArtefactDetail kind="defect" />,
    )
  }

  it('edits in place rather than opening the document editor', async () => {
    renderDefect()
    await screen.findAllByText(defect.title)

    fireEvent.click(screen.getByRole('button', { name: /edit/i }))

    // The defect's own fields, not the generic editor that would drop them.
    expect(await screen.findByTitle('Defect title')).toBeTruthy()
    expect(screen.getByTitle('Defect description')).toBeTruthy()
    expect(screen.queryByTestId('doc-editor')).toBeNull()
  })

  it('saves the edited fields', async () => {
    renderDefect()
    await screen.findAllByText(defect.title)

    fireEvent.click(screen.getByRole('button', { name: /edit/i }))
    fireEvent.change(await screen.findByTitle('Defect title'), {
      target: { value: 'Screen flickers on cold wake' },
    })
    fireEvent.click(screen.getByRole('button', { name: /save changes/i }))

    await waitFor(() => {
      const [id, payload] = lastCall(client.defectsApi.update) as [number, { title?: string }]
      expect(id).toBe(defect.id)
      expect(payload.title).toBe('Screen flickers on cold wake')
    })
  })

  it('asks before deleting, then deletes', async () => {
    renderDefect()
    await screen.findAllByText(defect.title)

    fireEvent.click(screen.getByRole('button', { name: /^delete$/i }))
    // Nothing is destroyed by the first click.
    await settle()
    expect(client.defectsApi.delete).not.toHaveBeenCalled()

    fireEvent.click(await screen.findByRole('button', { name: /confirm|yes|delete/i }))
    await waitFor(() => expect(client.defectsApi.delete).toHaveBeenCalledWith(defect.id))
  })

  it('shows comments and activity on their own tabs', async () => {
    renderDefect()
    await screen.findAllByText(defect.title)

    fireEvent.click(screen.getByRole('button', { name: /comments/i }))
    expect(await screen.findByText(/looks right to me/i)).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: /activity/i }))
    expect(await screen.findByText(/moved this from Draft to Approved/)).toBeTruthy()
  })

  it('moves the defect through its workflow', async () => {
    renderDefect()
    await screen.findAllByText(defect.title)

    // An open defect can only be triaged, rejected or marked a duplicate -
    // the screen offers exactly the transitions the workflow allows.
    expect(screen.queryByRole('button', { name: 'Move to Resolved' })).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Move to Triaged' }))

    await waitFor(() => {
      const [type, id, status] = lastCall(client.artefactsApi.transition) as [
        string,
        number,
        string,
      ]
      expect(type).toBe('defect')
      expect(id).toBe(defect.id)
      expect(status).toBe('Triaged')
    })
  })
})

describe('campaigns', () => {
  it('lists the campaigns of the project', async () => {
    renderAt('/projects/:prefix/campaigns', '/projects/VCU/campaigns', <TestCampaigns />)
    expect(await screen.findAllByText(/Release candidate sweep/)).toBeTruthy()
    expect(lastCall(client.campaignsApi.list)[0]).toBe(project.id)
  })

  it('scopes a new campaign from the suites that were picked', async () => {
    renderAt('/projects/:prefix/campaigns', '/projects/VCU/campaigns', <TestCampaigns />)
    await screen.findAllByText(/Release candidate sweep/)

    fireEvent.click(screen.getByRole('button', { name: /new campaign/i }))
    fireEvent.change(await screen.findByPlaceholderText('Campaign name'), {
      target: { value: 'Smoke sweep' },
    })
    fireEvent.click(screen.getByRole('checkbox'))
    fireEvent.click(screen.getByRole('button', { name: /^create campaign$/i }))

    await waitFor(() => {
      const [payload] = lastCall(client.campaignsApi.create) as [
        { name: string; project_id: number; suite_ids?: number[] },
      ]
      expect(payload.name).toBe('Smoke sweep')
      expect(payload.project_id).toBe(project.id)
      expect(payload.suite_ids).toEqual([testSuite.id])
    })
  })

  it('refuses to create a campaign with no suite behind it', async () => {
    renderAt('/projects/:prefix/campaigns', '/projects/VCU/campaigns', <TestCampaigns />)
    await screen.findAllByText(/Release candidate sweep/)

    fireEvent.click(screen.getByRole('button', { name: /new campaign/i }))
    const name = await screen.findByPlaceholderText('Campaign name')
    fireEvent.change(name, { target: { value: 'Unscoped' } })
    fireEvent.submit(name.closest('form') as HTMLFormElement)

    // A campaign's items are copied from its suites, so it cannot have none.
    expect(await screen.findByText(/select at least one suite/i)).toBeTruthy()
    await settle()
    expect(client.campaignsApi.create).not.toHaveBeenCalled()
  })

  it('narrows the list to a search term', async () => {
    renderAt('/projects/:prefix/campaigns', '/projects/VCU/campaigns', <TestCampaigns />)
    await screen.findAllByText(/Release candidate sweep/)

    fireEvent.change(screen.getByPlaceholderText('Search campaigns...'), {
      target: { value: 'nothing matches' },
    })

    await waitFor(() => expect(screen.queryByText('Release candidate sweep')).toBeNull())
  })
})

describe('importing requirements', () => {
  /** Opens the wizard on its ReqIF tab; it starts on project-to-project. */
  async function renderImport() {
    const rendered = renderAt('/projects/:prefix/import', '/projects/VCU/import', <ImportWizard />)
    fireEvent.click(await screen.findByRole('button', { name: /from reqif file/i }))
    return rendered
  }

  it('will not import until a file is chosen', async () => {
    await renderImport()
    const importButton = (await screen.findByRole('button', {
      name: /import reqif/i,
    })) as HTMLButtonElement

    expect(importButton.disabled).toBe(true)
    expect(screen.getByText(/choose a reqif file/i)).toBeTruthy()
  })

  it('names the file that was chosen and sends it to the project', async () => {
    const { container } = await renderImport()
    await screen.findByRole('button', { name: /import reqif/i })

    const file = new File(['<REQ-IF/>'], 'requirements.reqif', { type: 'application/xml' })
    const input = container.querySelector('input[type="file"]') as HTMLInputElement
    fireEvent.change(input, { target: { files: [file] } })

    expect(await screen.findByText('requirements.reqif')).toBeTruthy()
    fireEvent.click(screen.getByRole('button', { name: /import reqif/i }))

    await waitFor(() => expect(client.importApi.importReqif).toHaveBeenCalled())
    const [projectId, sent] = lastCall(client.importApi.importReqif) as [number, File]
    expect(projectId).toBe(project.id)
    expect(sent.name).toBe('requirements.reqif')
  })

  it('reports the reason an import was rejected', async () => {
    vi.mocked(client.importApi.importReqif).mockRejectedValueOnce(
      Object.assign(new Error('Request failed'), {
        isAxiosError: true,
        response: { data: { detail: 'The archive contains more than one .reqif member' } },
      }),
    )
    const { container } = await renderImport()
    await screen.findByRole('button', { name: /import reqif/i })

    const input = container.querySelector('input[type="file"]') as HTMLInputElement
    fireEvent.change(input, {
      target: { files: [new File(['x'], 'bad.reqifz', { type: 'application/zip' })] },
    })
    fireEvent.click(screen.getByRole('button', { name: /import reqif/i }))

    expect(await screen.findByText(/more than one \.reqif member/i)).toBeTruthy()
  })
})

describe('a test suite in detail', () => {
  function renderSuite() {
    return renderAt('/projects/:prefix/suites/:suiteId', '/projects/VCU/suites/41', <SuiteDetail />)
  }

  it('shows the suite the URL names', async () => {
    renderSuite()
    expect(await screen.findAllByText(/Smoke suite/)).toBeTruthy()
    expect(lastCall(client.testSuitesApi.get)[0]).toBe(testSuite.id)
  })

  it('renames the suite', async () => {
    renderSuite()
    await screen.findAllByText(/Smoke suite/)

    fireEvent.click(screen.getByRole('button', { name: /edit/i }))
    const nameField = (await screen.findAllByRole('textbox'))[0]
    fireEvent.change(nameField, { target: { value: 'Nightly smoke suite' } })
    fireEvent.click(screen.getByRole('button', { name: /^save$/i }))

    await waitFor(() => {
      const [id, payload] = lastCall(client.testSuitesApi.update) as [number, { name?: string }]
      expect(id).toBe(testSuite.id)
      expect(payload.name).toBe('Nightly smoke suite')
    })
  })

  it('asks before deleting the suite', async () => {
    renderSuite()
    await screen.findAllByText(/Smoke suite/)

    fireEvent.click(screen.getByRole('button', { name: /^delete$/i }))
    await settle()
    expect(client.testSuitesApi.delete).not.toHaveBeenCalled()

    const confirms = await screen.findAllByRole('button', { name: /^delete$/i })
    fireEvent.click(confirms[confirms.length - 1])

    await waitFor(() => expect(client.testSuitesApi.delete).toHaveBeenCalled())
  })

  it('adds a test case to the suite', async () => {
    renderSuite()
    await screen.findAllByText(/Smoke suite/)

    fireEvent.click(screen.getByRole('button', { name: /add test case/i }))
    const candidate = await screen.findByText('VCU-TC-001')
    fireEvent.click(candidate.closest('button') as HTMLElement)

    await waitFor(() => expect(client.testSuitesApi.addItem).toHaveBeenCalled())
    const [suiteId, testCaseId] = lastCall(client.testSuitesApi.addItem) as [number, number]
    expect(suiteId).toBe(testSuite.id)
    expect(testCaseId).toBe(testCase.id)
  })

  it('scopes a campaign from the suite', async () => {
    renderSuite()
    await screen.findAllByText(/Smoke suite/)

    fireEvent.click(screen.getByRole('button', { name: /create campaign scope/i }))

    await waitFor(() => {
      const [payload] = lastCall(client.campaignsApi.create) as [{ suite_ids?: number[] }]
      // A campaign's items are copied from the suite it was scoped from.
      expect(payload.suite_ids).toContain(testSuite.id)
    })
  })
})


describe('project settings', () => {
  function renderProjectEdit() {
    return renderAt('/projects/:prefix/edit', '/projects/VCU/edit', <ProjectEdit />)
  }

  it('loads the project by its prefix and saves a rename', async () => {
    renderProjectEdit()
    const name = (await screen.findByTitle('Project name')) as HTMLInputElement
    expect(name.value).toBe(project.name)

    fireEvent.change(name, { target: { value: 'Vehicle Control Unit II' } })
    fireEvent.click(screen.getByRole('button', { name: /save project/i }))

    await waitFor(() => {
      const [id, payload] = lastCall(client.projectsApi.update) as [number, { name?: string }]
      expect(id).toBe(project.id)
      expect(payload.name).toBe('Vehicle Control Unit II')
    })
  })

  it('will not save an invalid prefix', async () => {
    renderProjectEdit()
    const prefix = (await screen.findByTitle('Project prefix')) as HTMLInputElement

    // A prefix is exactly three letters; anything else cannot be saved.
    fireEvent.change(prefix, { target: { value: 'TOOLONG' } })

    await waitFor(() =>
      expect(
        (screen.getByRole('button', { name: /save project/i }) as HTMLButtonElement).disabled,
      ).toBe(true),
    )
  })

  it('lists the project members', async () => {
    renderProjectEdit()
    expect(await screen.findByText(/Ext Ernal/)).toBeTruthy()
  })

  it('will not add a member until a user is picked', async () => {
    renderProjectEdit()
    await screen.findByText(/Ext Ernal/)

    expect((screen.getByRole('button', { name: /add member/i }) as HTMLButtonElement).disabled).toBe(
      true,
    )
    expect(client.projectMembersApi.create).not.toHaveBeenCalled()
  })

  it('never offers an administrator as a project member', async () => {
    renderProjectEdit()
    await screen.findByText(/Ext Ernal/)

    // An administrator already reaches every project; the only user the
    // fixture returns is one, so there is nobody left to add.
    const picker = screen.getByTitle('Select user to add') as HTMLSelectElement
    expect(Array.from(picker.options).map((option) => option.textContent)).toEqual([
      'Select a user',
    ])
  })

  it('offers document visibility only for an external member', async () => {
    renderProjectEdit()
    await screen.findByText(/Ext Ernal/)
    const pickers = () => screen.queryAllByText(/external document visibility/i).length
    // The existing member is external, so one picker is always on screen; the
    // add form contributes a second while its role is external.
    expect(pickers()).toBe(2)

    fireEvent.change(screen.getByTitle('Project role'), { target: { value: 'maintainer' } })
    // A maintainer sees every document, so there is nothing to pick.
    await waitFor(() => expect(pickers()).toBe(1))

    fireEvent.change(screen.getByTitle('Project role'), { target: { value: 'external' } })
    await waitFor(() => expect(pickers()).toBe(2))
  })

  it('removes a member', async () => {
    renderProjectEdit()
    await screen.findByText(/Ext Ernal/)

    const remove = screen
      .getAllByRole('button')
      .find((button) => /remove/i.test(button.textContent ?? '') || /remove/i.test(button.getAttribute('title') ?? ''))
    expect(remove).toBeTruthy()
    fireEvent.click(remove as HTMLElement)

    await waitFor(() => expect(client.projectMembersApi.remove).toHaveBeenCalled())
  })

  it('makes deleting the project require typing its name', async () => {
    renderProjectEdit()
    await screen.findByTitle('Project name')

    const openDelete = screen
      .getAllByRole('button')
      .find((button) => /delete/i.test(button.textContent ?? ''))
    expect(openDelete).toBeTruthy()
    fireEvent.click(openDelete as HTMLElement)

    // Two buttons read "Delete project": the one that opens the dialog and the
    // one inside it. The second stays out of reach until the phrase matches.
    const deleteButtons = await screen.findAllByRole('button', { name: /delete project/i })
    const confirm = deleteButtons[deleteButtons.length - 1] as HTMLButtonElement
    expect(confirm.disabled).toBe(true)

    fireEvent.click(confirm)
    await settle()
    expect(client.projectsApi.delete).not.toHaveBeenCalled()
  })
})


describe('a campaign in detail', () => {
  function renderCampaign() {
    return renderAt(
      '/projects/:prefix/campaigns/:campaignId',
      '/projects/VCU/campaigns/31',
      <CampaignDetail />,
    )
  }

  it('loads the campaign the URL names', async () => {
    renderCampaign()
    expect(await screen.findAllByText(/Release candidate sweep/)).toBeTruthy()
    expect(lastCall(client.campaignsApi.get)[0]).toBe(31)
  })

  it('links the campaign to the Bud run that executed it', async () => {
    renderCampaign()
    await screen.findAllByText(/Release candidate sweep/)
    // Bud's URL is not configured here, so the run is named but not linked.
    expect(screen.getAllByText(/Bud run #77|77/).length).toBeGreaterThan(0)
  })

  it('changes the campaign status', async () => {
    renderCampaign()
    await screen.findAllByText(/Release candidate sweep/)

    fireEvent.click(screen.getByRole('button', { name: /edit/i }))
    fireEvent.change(await screen.findByLabelText(/status/i), { target: { value: 'Completed' } })
    fireEvent.click(screen.getByRole('button', { name: /^save$/i }))

    await waitFor(() => {
      const [id, payload] = lastCall(client.campaignsApi.update) as [number, { status?: string }]
      expect(id).toBe(31)
      expect(payload.status).toBe('Completed')
    })
  })

  it('asks before deleting the campaign', async () => {
    renderCampaign()
    await screen.findAllByText(/Release candidate sweep/)

    fireEvent.click(screen.getByRole('button', { name: /^delete$/i }))
    await settle()
    expect(client.campaignsApi.delete).not.toHaveBeenCalled()

    const confirms = await screen.findAllByRole('button', { name: /^delete$/i })
    fireEvent.click(confirms[confirms.length - 1])

    await waitFor(() => expect(client.campaignsApi.delete).toHaveBeenCalled())
  })
})

describe('account settings', () => {
  function renderSettings() {
    return renderAt('/settings', '/settings', <Settings />)
  }

  it('shows the credentials that let Bud submit results', async () => {
    renderSettings()
    // Only the prefix is ever shown; the token itself is returned once, at
    // creation, and never again.
    expect(await screen.findByText(/blm_sync_abcd/)).toBeTruthy()
    expect(document.body.textContent).not.toContain('blm_sync_secret')
  })

  it('creates a credential and shows the token exactly once', async () => {
    renderSettings()
    await screen.findByText(/blm_sync_abcd/)

    fireEvent.click(screen.getByRole('button', { name: /create credential/i }))

    await waitFor(() => expect(client.serviceCredentialsApi.create).toHaveBeenCalled())
    expect(await screen.findByText(/blm_sync_secret/)).toBeTruthy()
  })

  it('rotates a credential', async () => {
    renderSettings()
    await screen.findByText(/blm_sync_abcd/)

    fireEvent.click(screen.getByRole('button', { name: /^rotate$/i }))

    await waitFor(() => expect(client.serviceCredentialsApi.rotate).toHaveBeenCalledWith(151))
  })

  it('revokes a credential', async () => {
    renderSettings()
    await screen.findByText(/blm_sync_abcd/)

    fireEvent.click(screen.getByRole('button', { name: /^revoke$/i }))

    await waitFor(() => expect(client.serviceCredentialsApi.revoke).toHaveBeenCalled())
    expect(vi.mocked(client.serviceCredentialsApi.revoke).mock.calls[0][0]).toBe(151)
  })
})


describe('a requirement in detail', () => {
  function renderRequirement() {
    return renderAt(
      '/projects/:prefix/docs/:kind/:docId',
      '/projects/VCU/docs/requirements/VCU-REQ-001',
      <RequirementDetail resolvedId={requirement.id} />,
    )
  }

  it('shows the requirement and its metadata', async () => {
    renderRequirement()
    expect(await screen.findAllByText(new RegExp(requirement.title))).toBeTruthy()
    expect(lastCall(client.requirementsApi.get)[0]).toBe(requirement.id)
  })

  it('records the review against the named reviewer', async () => {
    renderRequirement()
    await screen.findAllByText(new RegExp(requirement.title))

    fireEvent.click(screen.getByRole('button', { name: /mark reviewed/i }))

    await waitFor(() => expect(client.requirementsApi.setReviewed).toHaveBeenCalled())
    const [id, reviewerId] = lastCall(client.requirementsApi.setReviewed) as [number, number]
    expect(id).toBe(requirement.id)
    expect(reviewerId).toBe(requirement.reviewer_id)
  })

  it('records the approval against the named approver', async () => {
    renderRequirement()
    await screen.findAllByText(new RegExp(requirement.title))

    fireEvent.click(screen.getByRole('button', { name: /mark approved/i }))

    await waitFor(() => expect(client.requirementsApi.setApproved).toHaveBeenCalled())
    const [id, approverId] = lastCall(client.requirementsApi.setApproved) as [number, number]
    expect(id).toBe(requirement.id)
    expect(approverId).toBe(requirement.approver_id)
  })

  it('cannot be signed off when nobody is named to do it', async () => {
    vi.mocked(client.requirementsApi.get).mockResolvedValue({
      ...requirement,
      reviewer_id: null,
      approver_id: null,
    } as Awaited<ReturnType<typeof client.requirementsApi.get>>)
    renderRequirement()
    await screen.findAllByText(new RegExp(requirement.title))

    expect(
      (screen.getByRole('button', { name: /mark reviewed/i }) as HTMLButtonElement).disabled,
    ).toBe(true)
    expect(
      (screen.getByRole('button', { name: /mark approved/i }) as HTMLButtonElement).disabled,
    ).toBe(true)
  })

  it('asks before deleting', async () => {
    renderRequirement()
    await screen.findAllByText(new RegExp(requirement.title))

    fireEvent.click(screen.getByRole('button', { name: /^delete$/i }))
    await settle()
    expect(client.requirementsApi.delete).not.toHaveBeenCalled()

    const confirms = await screen.findAllByRole('button', { name: /delete/i })
    fireEvent.click(confirms[confirms.length - 1])
    await waitFor(() => expect(client.requirementsApi.delete).toHaveBeenCalledWith(requirement.id))
  })
})


describe('a test case in detail', () => {
  function renderTestCase() {
    return renderAt(
      '/projects/:prefix/docs/:kind/:docId',
      '/projects/VCU/docs/test-cases/VCU-TC-001',
      <TestCaseDetail resolvedId={testCase.id} />,
    )
  }

  it('shows the procedure as a step table, not prose', async () => {
    renderTestCase()
    await screen.findAllByText(new RegExp(testCase.title))

    // The steps come back as structured rows and are rendered as such.
    expect(await screen.findByText('Power on the controller')).toBeTruthy()
    expect(screen.getByText('It reaches ready within 2s')).toBeTruthy()
  })

  it('shows the steps read-only', async () => {
    renderTestCase()
    await screen.findByText('Power on the controller')

    // Editing happens on the edit screen; the detail page never offers it.
    expect(screen.queryByTitle('Add row')).toBeNull()
    expect(screen.queryByTitle('Row actions')).toBeNull()
  })

  it('records review and approval against the named people', async () => {
    renderTestCase()
    await screen.findAllByText(new RegExp(testCase.title))

    fireEvent.click(screen.getByRole('button', { name: /mark reviewed/i }))
    await waitFor(() => expect(client.testCasesApi.setReviewed).toHaveBeenCalled())
    expect(lastCall(client.testCasesApi.setReviewed)).toEqual([testCase.id, testCase.reviewer_id])

    fireEvent.click(screen.getByRole('button', { name: /mark approved/i }))
    await waitFor(() => expect(client.testCasesApi.setApproved).toHaveBeenCalled())
    expect(lastCall(client.testCasesApi.setApproved)).toEqual([testCase.id, testCase.approver_id])
  })

  it('asks before deleting', async () => {
    renderTestCase()
    await screen.findAllByText(new RegExp(testCase.title))

    fireEvent.click(screen.getByRole('button', { name: /^delete$/i }))
    await settle()
    expect(client.testCasesApi.delete).not.toHaveBeenCalled()

    const confirms = await screen.findAllByRole('button', { name: /delete/i })
    fireEvent.click(confirms[confirms.length - 1])
    await waitFor(() => expect(client.testCasesApi.delete).toHaveBeenCalledWith(testCase.id))
  })
})

describe('a controlled document in detail', () => {
  function renderDocument() {
    return renderAt(
      '/projects/:prefix/docs/:kind/:docId',
      '/projects/VCU/docs/reports/VCU-RPT-001',
      <DocumentDetail resolvedId={docShell.id} />,
    )
  }

  it('loads the document and shows its metadata', async () => {
    renderDocument()
    expect(await screen.findAllByText(new RegExp(docShell.title))).toBeTruthy()
    expect(lastCall(client.documentsApi.get)[0]).toBe(docShell.id)
  })

  it('asks before deleting', async () => {
    renderDocument()
    await screen.findAllByText(new RegExp(docShell.title))

    fireEvent.click(screen.getByRole('button', { name: /^delete$/i }))
    await settle()
    expect(client.documentsApi.delete).not.toHaveBeenCalled()

    const confirms = await screen.findAllByRole('button', { name: /delete/i })
    fireEvent.click(confirms[confirms.length - 1])
    await waitFor(() => expect(client.documentsApi.delete).toHaveBeenCalledWith(docShell.id))
  })
})
