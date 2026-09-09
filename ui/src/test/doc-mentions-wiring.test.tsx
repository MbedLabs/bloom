// @vitest-environment jsdom
/**
 * Which list each mention trigger is fed.
 *
 * There are two triggers and they are not interchangeable: `{{` addresses a
 * project parameter or variable, `@` addresses a person. The editor keeps them
 * apart correctly, but it is handed both lists by the page, and a list built
 * wrongly there is invisible from inside the editor - the trigger simply says
 * "No results" for anything it was not given. That is what these pin.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ToastProvider } from '../components/Toast'
import { projectVariable, resetApiMocks, user } from './apiFixtures'

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

type Suggestion = { id: number; label: string; hint?: string; docType?: string }
type EditorProps = {
  mentionItems?: Suggestion[]
  userMentionItems?: Suggestion[]
  artefactSearch?: (query: string) => Promise<Suggestion[]>
  artefactHref?: (docType: string, id: number) => string
}

/** The props the page last handed the editor. */
let lastEditorProps: EditorProps = {}

vi.mock('../components/editor/DocEditor', () => ({
  default: (props: EditorProps) => {
    lastEditorProps = props
    return <div data-testid="doc-editor" />
  },
}))

const client = await import('../api/client')
const DocCreate = (await import('../pages/DocCreate')).default

/** A parameter and a variable, the two kinds `{{` has to reach. */
const parameter = { ...projectVariable, id: 301, kind: 'parameter' as const, key: 'BOOT_BUDGET_MS' }
const variable = { ...projectVariable, id: 302, kind: 'variable' as const, key: 'BOARD_REV' }
const person = { ...user, id: 7, full_name: 'Grace Hopper', role: 'maintainer' as const }

function renderCreate(type = 'requirements') {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <MemoryRouter initialEntries={[`/projects/VCU/docs/requirements/new?type=${type}`]}>
          <Routes>
            <Route path="/projects/:prefix/docs/:kind/new" element={<DocCreate />} />
          </Routes>
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
}

/** The labels offered under one trigger. */
function labels(list: Suggestion[] | undefined): string[] {
  return (list ?? []).map((item) => item.label).sort()
}

beforeEach(() => {
  vi.clearAllMocks()
  resetApiMocks(client as unknown as Record<string, unknown>, vi)
  lastEditorProps = {}
  vi.mocked(client.projectVariablesApi.list).mockResolvedValue([parameter, variable] as never)
  // `@` reads the project's people, not the admin-only directory.
  vi.mocked(client.usersApi.listMentionable).mockResolvedValue([user, person] as never)
})

afterEach(cleanup)

describe('what each mention trigger offers', () => {
  it('offers both parameters and variables under {{', async () => {
    renderCreate()
    await screen.findByTestId('doc-editor')

    // Both kinds are managed on the same Parameters & Variables screen and both
    // are written the same way in a document; filtering to one kind made the
    // other unreachable from the editor.
    await waitFor(() =>
      expect(labels(lastEditorProps.mentionItems)).toEqual(['BOARD_REV', 'BOOT_BUDGET_MS']),
    )
  })

  it('offers people, and only people, under @', async () => {
    renderCreate()
    await screen.findByTestId('doc-editor')

    await waitFor(() =>
      expect(labels(lastEditorProps.userMentionItems)).toEqual([user.full_name, person.full_name].sort()),
    )
  })

  it('keeps the two lists apart', async () => {
    renderCreate()
    await screen.findByTestId('doc-editor')
    await waitFor(() => expect(lastEditorProps.mentionItems?.length).toBe(2))

    // No person may be reached with `{{`, and no parameter with `@`.
    expect(labels(lastEditorProps.mentionItems)).not.toContain(person.full_name)
    expect(labels(lastEditorProps.userMentionItems)).not.toContain(parameter.key)
  })

  it('addresses a parameter by its key, not its value', async () => {
    renderCreate()
    await screen.findByTestId('doc-editor')
    await waitFor(() => expect(lastEditorProps.mentionItems?.length).toBe(2))

    // The label is what ends up between the braces, so it has to be the name
    // the parameter is looked up by.
    expect(lastEditorProps.mentionItems).toContainEqual(
      expect.objectContaining({ id: parameter.id, label: parameter.key }),
    )
    expect(labels(lastEditorProps.mentionItems)).not.toContain(parameter.value)
  })

  it('offers the value as a hint, so the picker says what is being pinned', async () => {
    renderCreate()
    await screen.findByTestId('doc-editor')
    await waitFor(() => expect(lastEditorProps.mentionItems?.length).toBe(2))

    // The value travels beside the key for the picker to show. It has to stay
    // out of the label, or it would be what gets written into the document.
    const offered = lastEditorProps.mentionItems?.find((item) => item.id === parameter.id)
    expect(offered?.hint).toBe(parameter.value)
    expect(offered?.label).toBe(parameter.key)
  })

  it('offers nothing rather than breaking when the project has no parameters', async () => {
    vi.mocked(client.projectVariablesApi.list).mockResolvedValue([] as never)
    renderCreate()
    await screen.findByTestId('doc-editor')

    await waitFor(() => expect(lastEditorProps.mentionItems).toEqual([]))
  })
})

describe('what # offers', () => {
  const found = [
    { id: 42, type: 'REQ', doc_id: 'VCU-REQ-0042', title: 'Brake pressure' },
    { id: 7, type: 'DES', doc_id: 'VCU-DES-0007', title: 'Hydraulic loop' },
  ]

  async function searchFrom(type: string) {
    renderCreate(type)
    await screen.findByTestId('doc-editor')
    await waitFor(() => expect(lastEditorProps.artefactSearch).toBeTypeOf('function'))
    return lastEditorProps.artefactSearch as (q: string) => Promise<Suggestion[]>
  }

  it('addresses an artefact by its public id, with the title as the hint', async () => {
    vi.mocked(client.searchApi.global).mockResolvedValue({
      query: 'brake',
      total: 2,
      items: found,
    } as never)

    const offered = await (await searchFrom('requirements'))('brake')

    expect(offered).toEqual([
      { id: 42, label: 'VCU-REQ-0042', hint: 'Brake pressure', docType: 'REQ' },
      { id: 7, label: 'VCU-DES-0007', hint: 'Hydraulic loop', docType: 'DES' },
    ])
  })

  it('queries the server rather than filtering a list it was handed', async () => {
    vi.mocked(client.searchApi.global).mockResolvedValue({
      query: 'brake',
      total: 0,
      items: [],
    } as never)

    await (await searchFrom('requirements'))('brake')

    expect(client.searchApi.global).toHaveBeenCalledWith(
      'brake',
      expect.objectContaining({ limit: 20 }),
    )
  })

  it('offers a requirement inside a specification, which no link rule permits', async () => {
    vi.mocked(client.searchApi.global).mockResolvedValue({
      query: 'brake',
      total: 1,
      items: [found[0]],
    } as never)

    const offered = await (await searchFrom('specifications'))('brake')

    expect(offered.map((item) => item.label)).toEqual(['VCU-REQ-0042'])
  })

  it('falls back to type and id when an artefact has no public id yet', async () => {
    vi.mocked(client.searchApi.global).mockResolvedValue({
      query: 'brake',
      total: 1,
      items: [{ id: 42, type: 'REQ', doc_id: null, title: 'Brake pressure' }],
    } as never)

    const offered = await (await searchFrom('requirements'))('brake')

    expect(offered[0].label).toBe('REQ 42')
  })

  it('drops anything that is not a linkable kind', async () => {
    vi.mocked(client.searchApi.global).mockResolvedValue({
      query: 'brake',
      total: 2,
      items: [found[0], { id: 3, type: 'NOPE', doc_id: 'VCU-XXX-003', title: 'Unknown' }],
    } as never)

    const offered = await (await searchFrom('requirements'))('brake')

    expect(offered.map((item) => item.label)).toEqual(['VCU-REQ-0042'])
  })

  it('gives a test case no picker at all, because a container hosts no tags', async () => {
    renderCreate('test-cases')

    await screen.findByPlaceholderText('Untitled')
    expect(screen.queryByTestId('doc-editor')).toBeNull()
  })

  it('links a tag to the artefact page for its kind', async () => {
    renderCreate('requirements')
    await screen.findByTestId('doc-editor')
    await waitFor(() => expect(lastEditorProps.artefactHref).toBeTypeOf('function'))

    const href = lastEditorProps.artefactHref as (docType: string, id: number) => string
    expect(href('REQ', 42)).toContain('/projects/VCU/')
    expect(href('REQ', 42)).toContain('42')
  })
})
