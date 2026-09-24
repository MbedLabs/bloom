// @vitest-environment jsdom
/**
 * Importing a Markdown document from the Import Wizard.
 *
 * A parameter name that already exists stops the import. The wizard lists each
 * colliding name with the project's value and the file's value, and imports only once
 * every name has an action: keep the project's value, or import the file's value under
 * a new name.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ToastProvider } from '../components/Toast'
import { project, resetApiMocks, user } from './apiFixtures'

vi.mock('../api/client', async (importOriginal) => {
  const { mockApiModule: build } = await import('./apiFixtures')
  return build(await importOriginal<Record<string, unknown>>(), vi)
})

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ user, isLoading: false, isAuthenticated: true, login: vi.fn(), logout: vi.fn(), refreshUser: vi.fn() }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
}))

const client = await import('../api/client')
const ImportWizard = (await import('../pages/ImportWizard')).default

const imported = {
  doc_type: 'REQ',
  parameters_created: 2,
  parameter_collisions: ['BOOT_MS'],
  parameters_renamed: { LIMIT: 'LIMIT_V2' },
  artefacts_created: 2,
  artefacts_skipped: 0,
  sections: [{ type_code: 'REQ', title: 'Fast boot' }],
}

function renderWizard() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <MemoryRouter initialEntries={['/projects/VCU/import']}>
          <Routes>
            <Route path="/projects/:prefix/import" element={<ImportWizard />} />
          </Routes>
        </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
}

async function chooseMarkdown() {
  renderWizard()
  fireEvent.click(await screen.findByText('From Markdown file'))
  const input = document.querySelector('input[accept=".md,.markdown,text/markdown"]') as HTMLInputElement
  fireEvent.change(input, { target: { files: [new File(['## [REQ] Fast boot'], 'spec.md')] } })
}

beforeEach(() => {
  vi.clearAllMocks()
  resetApiMocks(client as unknown as Record<string, unknown>, vi)
  vi.mocked(client.projectsApi.list).mockResolvedValue([project] as never)
})

afterEach(cleanup)

describe('Markdown import', () => {
  it('imports straight away when no name collides', async () => {
    vi.mocked(client.importApi.importMarkdown).mockResolvedValue({ ...imported, parameter_collisions: [], parameters_renamed: {} })
    await chooseMarkdown()
    fireEvent.click(screen.getByRole('button', { name: 'Import Markdown' }))
    expect(await screen.findByText(/2 artefacts created/)).toBeTruthy()
    expect(vi.mocked(client.importApi.importMarkdown).mock.calls[0][3]).toBeUndefined()
    expect(screen.queryByText(/Kept the project/)).toBeNull()
  })

  it('stops on a collision and imports with the chosen action for each name', async () => {
    vi.mocked(client.importApi.importMarkdown)
      .mockRejectedValueOnce({
        response: {
          status: 409,
          data: {
            detail: {
              collisions: [
                { name: 'BOOT_MS', existing_value: 'old', imported_value: '500' },
                { name: 'LIMIT', existing_value: '9', imported_value: '5' },
              ],
            },
          },
        },
      })
      .mockResolvedValueOnce(imported)
    await chooseMarkdown()
    fireEvent.click(screen.getByRole('button', { name: 'Import Markdown' }))

    expect(await screen.findByText(/These parameter names already exist/)).toBeTruthy()
    expect(screen.getByText('old')).toBeTruthy()
    expect(screen.getByText('500')).toBeTruthy()
    const go = screen.getByRole('button', { name: 'Import with these choices' }) as HTMLButtonElement
    expect(go.disabled).toBe(true)

    fireEvent.click(screen.getAllByLabelText("Use the project's value")[0])
    expect(go.disabled).toBe(true)
    fireEvent.click(screen.getAllByLabelText("Import the file's value as a new parameter")[1])
    const rename = screen.getByLabelText('New name for LIMIT') as HTMLInputElement
    expect(rename.value).toBe('LIMIT_2')
    fireEvent.change(rename, { target: { value: '' } })
    expect(go.disabled).toBe(true)
    fireEvent.change(rename, { target: { value: 'LIMIT_V2' } })
    expect(go.disabled).toBe(false)
    fireEvent.click(go)

    await waitFor(() => expect(client.importApi.importMarkdown).toHaveBeenCalledTimes(2))
    expect(vi.mocked(client.importApi.importMarkdown).mock.calls[1][3]).toEqual({
      BOOT_MS: { action: 'existing' },
      LIMIT: { action: 'rename', to: 'LIMIT_V2' },
    })
    expect(await screen.findByText("Kept the project's value: BOOT_MS")).toBeTruthy()
    expect(screen.getByText(/Imported under a new name:\s*LIMIT as LIMIT_V2/)).toBeTruthy()
    expect(screen.queryByText(/These parameter names already exist/)).toBeNull()
  })

  it('shows any other refusal as a message', async () => {
    vi.mocked(client.importApi.importMarkdown).mockRejectedValueOnce({
      response: { status: 422, data: { detail: "The new name 'X' for Y is already taken." } },
    })
    await chooseMarkdown()
    fireEvent.click(screen.getByRole('button', { name: 'Import Markdown' }))
    expect(await screen.findByText("The new name 'X' for Y is already taken.")).toBeTruthy()

    vi.mocked(client.importApi.importMarkdown).mockRejectedValueOnce({})
    fireEvent.click(screen.getByRole('button', { name: 'Import Markdown' }))
    expect(await screen.findByText('Import failed. Check the file and try again.')).toBeTruthy()
  })
})
