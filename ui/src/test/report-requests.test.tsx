// @vitest-environment jsdom
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import Action from '../components/ReportRequestAction'

const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }))
vi.mock('../api/client', () => ({ api: mock, extractApiErrorMessage: (_error: unknown, fallback: string) => fallback }))
vi.mock('../components/useToast', () => ({ useToast: () => ({ saved: vi.fn(), failed: vi.fn() }) }))
const source = { source_kind: 'test-case' as const, source_id: 2, run_id: 41 }
const row = { id: 4, status: 'pending', reason: null, project_prefix: 'PRJ', doc_id: null }
function show() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(<MemoryRouter><QueryClientProvider client={client}><Action source={source} /></QueryClientProvider></MemoryRouter>)
}
beforeEach(() => { vi.clearAllMocks(); mock.get.mockResolvedValue({ data: null }); mock.post.mockResolvedValue({ data: row }) })
afterEach(cleanup)

it('sends a source-bound request and shows pending without a second action', async () => {
  show()
  fireEvent.click(await screen.findByRole('button', { name: 'Request report' }))
  expect(await screen.findByText('Report requested · Pending')).toBeTruthy()
  expect(mock.post).toHaveBeenCalledWith('/report-requests', source)
  expect(screen.queryByRole('button')).toBeNull()
})
it('blocks a repeated click while the request is being recorded', async () => {
  let finish!: (data: unknown) => void
  mock.post.mockImplementationOnce(() => new Promise(resolve => { finish = resolve }))
  show()
  fireEvent.click(await screen.findByRole('button', { name: 'Request report' }))
  const busy = await screen.findByRole('button', { name: 'Requesting…' })
  expect((busy as HTMLButtonElement).disabled).toBe(true)
  fireEvent.click(busy)
  expect(mock.post).toHaveBeenCalledTimes(1)
  finish({ data: row })
  expect(await screen.findByText('Report requested · Pending')).toBeTruthy()
})
it('links a delivered report using the project document route', async () => {
  mock.get.mockResolvedValue({ data: { ...row, status: 'delivered', doc_id: 'PRJ-RPT-001' } })
  show()
  expect((await screen.findByRole('link', { name: 'View report' })).getAttribute('href')).toBe('/projects/PRJ/docs/reports/PRJ-RPT-001')
})
it('does not invent a link when the delivered document is not visible', async () => {
  mock.get.mockResolvedValue({ data: { ...row, status: 'delivered' } })
  show()
  await screen.findByText('Report delivered')
  expect(screen.queryByRole('link')).toBeNull()
})
it('shows the refusal reason and allows a new request', async () => {
  mock.get.mockResolvedValue({ data: { ...row, status: 'refused', reason: 'Evidence incomplete' } })
  show()
  expect(await screen.findByText('Report refused: Evidence incomplete')).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: 'Request again' }))
  expect(await screen.findByText('Report requested · Pending')).toBeTruthy()
})
it('shows load errors without offering an unverified request action', async () => {
  mock.get.mockRejectedValue(new Error('offline'))
  show()
  expect((await screen.findByRole('alert')).textContent).toBe('Could not load the report request')
  expect(screen.queryByRole('button')).toBeNull()
})
it('keeps the request action available after a submission error', async () => {
  mock.post.mockRejectedValueOnce(new Error('offline'))
  show()
  fireEvent.click(await screen.findByRole('button', { name: 'Request report' }))
  expect((await screen.findByRole('alert')).textContent).toBe('Could not load the report request')
  await waitFor(() => expect((screen.getByRole('button') as HTMLButtonElement).disabled).toBe(false))
})

it('does not restore a previous account request after the session changes', async () => {
  const identity = await import('../lib/tokenStorage')
  const who = vi.spyOn(identity, 'getSessionUserId').mockReturnValue(1)
  let finish!: (data: unknown) => void
  mock.post.mockImplementationOnce(() => new Promise(resolve => { finish = resolve }))
  show()
  fireEvent.click(await screen.findByRole('button', { name: 'Request report' }))
  await screen.findByRole('button', { name: 'Requesting…' })
  who.mockReturnValue(2)
  finish({ data: row })
  await waitFor(() => expect(screen.queryByText('Report requested · Pending')).toBeNull())
  await waitFor(() => expect(screen.getByRole('button', { name: 'Request report' })).toBeTruthy())
  who.mockRestore()
})
