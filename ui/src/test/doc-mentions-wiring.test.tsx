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

type Suggestion = { id: number; label: string; hint?: string }
type EditorProps = { mentionItems?: Suggestion[]; userMentionItems?: Suggestion[] }

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

function renderCreate() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <MemoryRouter initialEntries={['/projects/VCU/docs/requirements/new']}>
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
