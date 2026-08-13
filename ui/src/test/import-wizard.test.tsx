// @vitest-environment jsdom
/**
 * Copying documents from one project into another.
 *
 * The wizard walks five steps - source project, document type, which
 * documents, review, results - and each one narrows what the next can do. Only
 * the ReqIF tab beside it had coverage, so the whole project-to-project path
 * ran untested, including the parts that keep it honest: a project cannot
 * import from itself, changing the document type throws away a selection made
 * under the old one, and the review step is the last place the identifiers
 * about to be minted are shown before anything is written.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ToastProvider } from '../components/Toast'
import { docShell, project, resetApiMocks, user } from './apiFixtures'
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

const client = await import('../api/client')
const ImportWizard = (await import('../pages/ImportWizard')).default

const source = {
  ...project,
  id: 2,
  name: 'Battery Management',
  prefix: 'BMS',
  requirement_count: 12,
  test_case_count: 4,
}
/** Documents as they exist in the *source* project, under its own prefix. */
const first = { ...docShell, id: 11, doc_id: 'BMS-REQ-001', title: 'Pack isolation' }
const second = { ...docShell, id: 12, doc_id: 'BMS-REQ-002', title: 'Cell balancing' }

function envelope(items: unknown[]) {
  return { items, total: items.length, skip: 0, limit: 50 }
}

function renderWizard() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <MemoryRouter initialEntries={['/projects/VCU/import']}>
          <Routes>
            <Route path="/projects/:prefix/import" element={<ImportWizard />} />
            <Route path="/projects/:prefix/docs" element={<div>document registry</div>} />
            <Route path="/projects/:prefix" element={<div>project overview</div>} />
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

/** Walk to the document picker, having chosen the source project and a type. */
async function reachPicker(type: 'Requirements' | 'Test Cases' = 'Requirements') {
  renderWizard()
  fireEvent.click(await screen.findByText(source.name))
  fireEvent.click(await screen.findByText(type))
  await screen.findByText('Select Docs to Import')
  // Step 3 renders before its query settles; wait for the list itself.
  await screen.findByText(first.doc_id)
}

beforeEach(() => {
  vi.clearAllMocks()
  resetApiMocks(client as unknown as Record<string, unknown>, vi)
  vi.mocked(client.projectsApi.list).mockResolvedValue([project, source] as never)
  vi.mocked(client.docsApi.list).mockResolvedValue(envelope([first, second]) as never)
})

afterEach(cleanup)

describe('choosing where to import from', () => {
  it('never offers the project being imported into', async () => {
    renderWizard()

    expect(await screen.findByText(source.name)).toBeTruthy()
    // Importing a project into itself would duplicate every identifier.
    expect(screen.queryByText(project.name)).toBeNull()
  })

  it('shows how much each candidate holds', async () => {
    renderWizard()
    await screen.findByText(source.name)

    expect(screen.getByText(/BMS · 12 REQs · 4 TCs/)).toBeTruthy()
  })

  it('says so when there is nowhere to import from', async () => {
    vi.mocked(client.projectsApi.list).mockResolvedValue([project] as never)
    renderWizard()

    expect(await screen.findByText('No other projects available.')).toBeTruthy()
  })

  it('asks the source project for the chosen type only', async () => {
    await reachPicker('Test Cases')

    await waitFor(() => expect(lastCall(client.docsApi.list)[0]).toBe(source.prefix))
    const [, params] = lastCall(client.docsApi.list) as [string, { type: string[] }]
    expect(params.type).toEqual(['TC'])
  })

  it('does not fetch anything until a type is chosen', async () => {
    renderWizard()
    fireEvent.click(await screen.findByText(source.name))
    await screen.findByText('Select Doc Type')

    // Step 3 is where the list is needed; a project may hold thousands.
    await settle()
    expect(client.docsApi.list).not.toHaveBeenCalled()
  })
})

describe('choosing what to import', () => {
  it('counts the selection against what is available', async () => {
    await reachPicker()
    expect(screen.getByText('0 selected')).toBeTruthy()

    fireEvent.click(screen.getByText(first.doc_id))
    await waitFor(() => expect(screen.getByText('1 selected')).toBeTruthy())
  })

  it('selects and deselects everything at once', async () => {
    await reachPicker()

    fireEvent.click(screen.getByRole('button', { name: 'Select these 2' }))
    await waitFor(() => expect(screen.getByText('2 selected')).toBeTruthy())

    fireEvent.click(screen.getByRole('button', { name: 'Deselect these 2' }))
    await waitFor(() => expect(screen.getByText('0 selected')).toBeTruthy())
  })

  it('un-picks a document that is clicked twice', async () => {
    await reachPicker()

    fireEvent.click(screen.getByText(first.doc_id))
    fireEvent.click(screen.getByText(first.doc_id))

    await waitFor(() => expect(screen.getByText('0 selected')).toBeTruthy())
  })

  it('cannot move on with nothing picked', async () => {
    await reachPicker()

    expect((screen.getByRole('button', { name: /^Review/ }) as HTMLButtonElement).disabled).toBe(
      true,
    )
  })

  it('throws away the selection when the document type changes', async () => {
    await reachPicker()
    fireEvent.click(screen.getByRole('button', { name: 'Select these 2' }))
    await waitFor(() => expect(screen.getByText('2 selected')).toBeTruthy())

    fireEvent.click(screen.getByRole('button', { name: /Back/ }))
    fireEvent.click(await screen.findByText('Test Cases'))

    // The ids picked under REQ mean nothing under TC.
    expect(await screen.findByText('0 selected')).toBeTruthy()
  })

  it('asks for a bounded page, not the whole project', async () => {
    await reachPicker()

    const [, params] = lastCall(client.docsApi.list) as [string, { limit?: number }]
    // A source project may hold thousands; the picker renders a page of them.
    expect(params.limit).toBe(100)
  })

  it('sends the search to the server rather than filtering what it holds', async () => {
    await reachPicker()

    fireEvent.change(screen.getByLabelText('Search source documents'), {
      target: { value: 'isolation' },
    })

    await waitFor(() => {
      const [, params] = lastCall(client.docsApi.list) as [string, { q?: string }]
      expect(params.q).toBe('isolation')
    })
  })

  it('says how many it is not showing', async () => {
    vi.mocked(client.docsApi.list).mockResolvedValue({
      items: [first, second], total: 940, skip: 0, limit: 100,
    } as never)
    await reachPicker()

    expect(await screen.findByText(/938 more not shown/)).toBeTruthy()
  })

  it('keeps a selection made before the search was narrowed', async () => {
    await reachPicker()
    fireEvent.click(screen.getByText(first.doc_id))
    await waitFor(() => expect(screen.getByText('1 selected')).toBeTruthy())

    // The page no longer holds the picked document. Selection is the user's,
    // not the page's, so narrowing the view must not silently drop it.
    vi.mocked(client.docsApi.list).mockResolvedValue(envelope([second]) as never)
    fireEvent.change(screen.getByLabelText('Search source documents'), {
      target: { value: 'balancing' },
    })

    await waitFor(() => expect(screen.queryByText(first.doc_id)).toBeNull())
    expect(screen.getByText('1 selected')).toBeTruthy()
  })

  it('adds the page to the selection rather than replacing it', async () => {
    await reachPicker()
    fireEvent.click(screen.getByText(first.doc_id))
    await waitFor(() => expect(screen.getByText('1 selected')).toBeTruthy())

    vi.mocked(client.docsApi.list).mockResolvedValue(envelope([second]) as never)
    fireEvent.change(screen.getByLabelText('Search source documents'), {
      target: { value: 'balancing' },
    })
    await waitFor(() => expect(screen.queryByText(first.doc_id)).toBeNull())

    // "Select these 1" is about the page on screen. Whatever was ticked on an
    // earlier page is still the user's choice and must survive it.
    fireEvent.click(screen.getByRole('button', { name: 'Select these 1' }))

    await waitFor(() => expect(screen.getByText('2 selected')).toBeTruthy())
  })

  it('deselects only the page, leaving the rest of the selection alone', async () => {
    await reachPicker()
    fireEvent.click(screen.getByText(first.doc_id))
    await waitFor(() => expect(screen.getByText('1 selected')).toBeTruthy())

    vi.mocked(client.docsApi.list).mockResolvedValue(envelope([second]) as never)
    fireEvent.change(screen.getByLabelText('Search source documents'), {
      target: { value: 'balancing' },
    })
    await waitFor(() => expect(screen.queryByText(first.doc_id)).toBeNull())

    fireEvent.click(screen.getByRole('button', { name: 'Select these 1' }))
    await waitFor(() => expect(screen.getByText('2 selected')).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: 'Deselect these 1' }))

    await waitFor(() => expect(screen.getByText('1 selected')).toBeTruthy())
  })

  it('tells a fruitless search apart from an empty project', async () => {
    await reachPicker()
    vi.mocked(client.docsApi.list).mockResolvedValue(envelope([]) as never)

    fireEvent.change(screen.getByLabelText('Search source documents'), {
      target: { value: 'nothing matches this' },
    })

    expect(await screen.findByText('No docs match that search.')).toBeTruthy()
  })

  it('says so when the source project has nothing of that type', async () => {
    vi.mocked(client.docsApi.list).mockResolvedValue(envelope([]) as never)
    renderWizard()
    fireEvent.click(await screen.findByText(source.name))
    fireEvent.click(await screen.findByText('Requirements'))

    expect(await screen.findByText('No docs found in source project.')).toBeTruthy()
  })
})

describe('reviewing and running the import', () => {
  async function reachReview() {
    await reachPicker()
    fireEvent.click(screen.getByText(first.doc_id))
    fireEvent.click(await screen.findByRole('button', { name: /^Review/ }))
    await screen.findByText('Review Import')
  }

  it('names both projects and the shape of the identifiers to be minted', async () => {
    await reachReview()

    expect(screen.getByText(`${source.name} (${source.prefix})`)).toBeTruthy()
    expect(screen.getByText(`${project.name} (${project.prefix})`)).toBeTruthy()
    // Imported documents are renumbered into the target project's scheme.
    expect(screen.getByText(`${project.prefix}-REQ-NNN`)).toBeTruthy()
    expect(screen.getByText('1 docs')).toBeTruthy()
  })

  it('sends the source, the type and the chosen ids', async () => {
    await reachReview()

    fireEvent.click(screen.getByRole('button', { name: /Import 1 Docs/ }))

    await waitFor(() =>
      expect(lastCall(client.importApi.import)).toEqual([
        project.id,
        {
          source_project_id: source.id,
          doc_type: 'REQ',
          doc_ids: [first.id],
          include_links: true,
        },
      ]),
    )
  })

  it('can leave the links behind', async () => {
    await reachReview()

    fireEvent.click(screen.getByLabelText('Include links'))
    fireEvent.click(screen.getByRole('button', { name: /Import 1 Docs/ }))

    await waitFor(() =>
      expect(
        (lastCall(client.importApi.import)[1] as { include_links: boolean }).include_links,
      ).toBe(false),
    )
  })

  it('keeps the selection when stepping back from the review', async () => {
    await reachReview()

    fireEvent.click(screen.getByRole('button', { name: /Back/ }))

    expect(await screen.findByText('1 selected')).toBeTruthy()
  })

  it('reports what was created, and what was skipped', async () => {
    vi.mocked(client.importApi.import).mockResolvedValue({
      imported: 2,
      skipped: 1,
      new_ids: ['VCU-REQ-004', 'VCU-REQ-005'],
      errors: [],
    } as never)
    await reachReview()

    fireEvent.click(screen.getByRole('button', { name: /Import 1 Docs/ }))

    expect(await screen.findByText('Import Complete')).toBeTruthy()
    expect(screen.getByText('2 docs imported successfully')).toBeTruthy()
    expect(screen.getByText('1 skipped')).toBeTruthy()
    expect(screen.getByText(/VCU-REQ-004, VCU-REQ-005/)).toBeTruthy()
  })

  it('says "1 doc" rather than "1 docs"', async () => {
    vi.mocked(client.importApi.import).mockResolvedValue({
      imported: 1,
      skipped: 0,
      new_ids: ['VCU-REQ-004'],
      errors: [],
    } as never)
    await reachReview()

    fireEvent.click(screen.getByRole('button', { name: /Import 1 Docs/ }))

    expect(await screen.findByText('1 doc imported successfully')).toBeTruthy()
  })

  it('lists what went wrong alongside what succeeded', async () => {
    vi.mocked(client.importApi.import).mockResolvedValue({
      imported: 1,
      skipped: 1,
      new_ids: ['VCU-REQ-004'],
      errors: ['BMS-REQ-002: a document with that title already exists'],
    } as never)
    await reachReview()

    fireEvent.click(screen.getByRole('button', { name: /Import 1 Docs/ }))

    // A partial import is the normal case, so both halves have to be shown.
    expect(await screen.findByText(/already exists/)).toBeTruthy()
    expect(screen.getByText('1 doc imported successfully')).toBeTruthy()
  })

  it('leads back to the project when it is done', async () => {
    await reachReview()
    fireEvent.click(screen.getByRole('button', { name: /Import 1 Docs/ }))
    await screen.findByText('Import Complete')

    fireEvent.click(screen.getByRole('button', { name: /back to project/i }))

    expect(await screen.findByText('project overview')).toBeTruthy()
  })
})

describe('the two import routes', () => {
  it('starts on project-to-project and switches to ReqIF', async () => {
    renderWizard()

    expect(await screen.findByText('Select Source Project')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: /from reqif file/i }))
    expect(await screen.findByRole('button', { name: /import reqif/i })).toBeTruthy()
    // The two routes are exclusive; the project picker goes away.
    expect(screen.queryByText('Select Source Project')).toBeNull()
  })

  it('leads to the registry after a ReqIF import', async () => {
    vi.mocked(client.importApi.importReqif).mockResolvedValue({
      imported: 3,
      skipped: 0,
      links_created: 2,
      new_ids: ['VCU-REQ-004'],
      errors: [],
      specifications: [],
    } as never)
    const { container } = renderWizard()
    fireEvent.click(await screen.findByRole('button', { name: /from reqif file/i }))

    const input = container.querySelector('input[type="file"]') as HTMLInputElement
    fireEvent.change(input, {
      target: { files: [new File(['<REQ-IF/>'], 'reqs.reqif', { type: 'application/xml' })] },
    })
    fireEvent.click(screen.getByRole('button', { name: /import reqif/i }))

    await waitFor(() => expect(client.importApi.importReqif).toHaveBeenCalled())
    fireEvent.click(await screen.findByRole('button', { name: /view imported requirements/i }))

    expect(await screen.findByText('document registry')).toBeTruthy()
  })

  it('shows warnings from a ReqIF import that partly succeeded', async () => {
    vi.mocked(client.importApi.importReqif).mockResolvedValue({
      imported: 2,
      skipped: 1,
      links_created: 0,
      new_ids: ['VCU-REQ-004', 'VCU-REQ-005'],
      errors: ['SPEC-OBJECT 7 has no identifier'],
      specifications: [],
    } as never)
    const { container } = renderWizard()
    fireEvent.click(await screen.findByRole('button', { name: /from reqif file/i }))

    const input = container.querySelector('input[type="file"]') as HTMLInputElement
    fireEvent.change(input, {
      target: { files: [new File(['<REQ-IF/>'], 'reqs.reqif', { type: 'application/xml' })] },
    })
    fireEvent.click(screen.getByRole('button', { name: /import reqif/i }))

    expect(await screen.findByText('Warnings')).toBeTruthy()
    expect(screen.getByText(/has no identifier/)).toBeTruthy()
  })
})
