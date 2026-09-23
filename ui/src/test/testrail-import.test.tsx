// @vitest-environment jsdom
/**
 * Migrating test cases from a TestRail export.
 *
 * XML goes straight to the import. CSV first asks the server which columns it
 * recognised, lets the user repoint any field, and sends that mapping with the
 * import. The title column is the one field an import cannot do without.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AxiosError, AxiosHeaders } from 'axios'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ToastProvider } from '../components/Toast'
import { resetApiMocks } from './apiFixtures'

vi.mock('../api/client', async (importOriginal) => {
  const { mockApiModule: build } = await import('./apiFixtures')
  return build(await importOriginal<Record<string, unknown>>(), vi)
})

const client = await import('../api/client')
const TestRailImport = (await import('../components/TestRailImport')).default

const result = {
  created: 2,
  updated: 1,
  skipped: 1,
  suites_created: ['VCU-TS-001'],
  links_created: 3,
  new_ids: ['VCU-TC-004', 'VCU-TC-005'],
  errors: ['case C9: missing title'],
}

function renderImport() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
      <MemoryRouter initialEntries={['/projects/VCU/import']}>
        <Routes>
          <Route path="/projects/:prefix/import" element={<TestRailImport projectId={1} prefix="VCU" />} />
          <Route path="/projects/:prefix/docs" element={<div>document registry</div>} />
        </Routes>
      </MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
}

function pick(name: string) {
  fireEvent.change(screen.getByLabelText('TestRail export file'), {
    target: { files: [new File(['x'], name)] },
  })
}

beforeEach(() => {
  resetApiMocks(client as unknown as Record<string, unknown>, vi)
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('TestRail import', () => {
  it('imports an XML suite without a column mapping and reports the outcome', async () => {
    vi.mocked(client.importApi.importTestRail).mockResolvedValue(result)
    renderImport()
    const button = screen.getByRole('button', { name: /Import from TestRail/ })
    expect((button as HTMLButtonElement).disabled).toBe(true)

    pick('suite.xml')
    fireEvent.click(button)

    await screen.findByText(/2 created ·/)
    expect(screen.getByText('TestRail import: 2 created, 1 updated')).toBeTruthy()
    const call = vi.mocked(client.importApi.importTestRail).mock.calls[0]
    expect([call[0], (call[1] as File).name, call[2], call[3]]).toEqual([1, 'suite.xml', 'xml', undefined])
    expect(client.importApi.testRailColumns).not.toHaveBeenCalled()
    expect(screen.getByText(/1 skipped/)).toBeTruthy()
    expect(screen.getByText(/1 suite\(s\) created/)).toBeTruthy()
    expect(screen.getByText('New IDs: VCU-TC-004, VCU-TC-005')).toBeTruthy()
    expect(screen.getByText('case C9: missing title')).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: 'View test cases' }))
    await screen.findByText('document registry')
  })

  it('maps CSV columns, requires a title, and sends the mapping', async () => {
    vi.mocked(client.importApi.testRailColumns).mockResolvedValue({
      columns: ['Name', 'Do', 'Expect'],
      detected: {},
    })
    vi.mocked(client.importApi.importTestRail).mockResolvedValue({ ...result, skipped: 0, errors: [], new_ids: [] })
    renderImport()
    fireEvent.click(screen.getByRole('button', { name: 'CSV' }))
    pick('cases.csv')

    await screen.findByText('Choose the column that holds the title.')
    expect(screen.getByText('Found 3 columns')).toBeTruthy()
    const button = screen.getByRole('button', { name: /Import from TestRail/ }) as HTMLButtonElement
    expect(button.disabled).toBe(true)

    fireEvent.change(screen.getByLabelText('Title'), { target: { value: 'Name' } })
    fireEvent.change(screen.getByLabelText('Steps (text template)'), { target: { value: 'Do' } })
    fireEvent.change(screen.getByLabelText('Expected result (text template)'), { target: { value: 'Expect' } })
    expect(screen.queryByText('Choose the column that holds the title.')).toBeNull()
    fireEvent.click(button)

    await waitFor(() => expect(client.importApi.importTestRail).toHaveBeenCalled())
    const call = vi.mocked(client.importApi.importTestRail).mock.calls[0]
    expect(call[2]).toBe('csv')
    expect(call[3]).toEqual({ title: 'Name', steps: 'Do', expected: 'Expect' })
    await screen.findByText(/2 created ·/)
    expect(screen.queryByText(/skipped/)).toBeNull()
  })

  it('shows the server message when the columns or the import fail', async () => {
    vi.mocked(client.importApi.testRailColumns).mockRejectedValue(
      new AxiosError('Unprocessable', '422', undefined, undefined, {
        status: 422,
        statusText: 'Unprocessable Entity',
        data: { detail: 'The file is empty.' },
        headers: {},
        config: { headers: new AxiosHeaders() },
      }),
    )
    vi.mocked(client.importApi.importTestRail).mockRejectedValue({})
    renderImport()
    fireEvent.click(screen.getByRole('button', { name: 'CSV' }))
    pick('empty.csv')
    await screen.findByText('The file is empty.')

    fireEvent.click(screen.getByRole('button', { name: 'XML' }))
    pick('broken.xml')
    fireEvent.click(screen.getByRole('button', { name: /Import from TestRail/ }))
    await screen.findByText('Importing from TestRail failed')
  })

  it('falls back to a generic message when reading the columns fails without detail', async () => {
    vi.mocked(client.importApi.testRailColumns).mockRejectedValue({})
    renderImport()
    fireEvent.click(screen.getByRole('button', { name: 'CSV' }))
    pick('cases.csv')
    await screen.findByText('Reading the columns failed')
  })
})
