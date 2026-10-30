import { createQueryClient } from '../lib/queryClient'
// @vitest-environment jsdom
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const request = { id: 7, requester_name: 'Reviewer', requester_email: 'reviewer@example.com', resource_ref: 'PRJ-REQ-001' }
const saved = vi.hoisted(() => vi.fn())
const failed = vi.hoisted(() => vi.fn())
vi.mock('../api/client', () => ({ accessRequestsApi: { list: vi.fn(), decide: vi.fn() } }))
vi.mock('../components/useToast', () => ({ useToast: () => ({ saved, failed }) }))
const api = await import('../api/client')
const Panel = (await import('../components/AccessRequestsPanel')).default

function renderPanel(projectPrefix?: string, showEmpty = true) {
  const client = createQueryClient({ defaultOptions: { queries: { retry: false } } })
  const invalidate = vi.spyOn(client, 'invalidateQueries')
  render(<QueryClientProvider client={client}><Panel projectPrefix={projectPrefix} showEmpty={showEmpty} /></QueryClientProvider>)
  return invalidate
}
beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(api.accessRequestsApi.list).mockResolvedValue([request] as never)
  vi.mocked(api.accessRequestsApi.decide).mockResolvedValue(request as never)
})
afterEach(cleanup)

describe('Access request decisions', () => {
  it('names the resource by the label the API resolved', async () => {
    vi.mocked(api.accessRequestsApi.list).mockResolvedValue([
      { ...request, resource_type: 'requirement', resource_ref: '4711', resource_label: 'PRJ-REQ-0005', project_prefix: 'PRJ' },
    ] as never)
    renderPanel()
    expect(await screen.findByText(/asks for PRJ-REQ-0005 in project PRJ/)).toBeTruthy()
    expect(screen.queryByText(/asks for 4711/)).toBeNull()
  })

  it.each(['granted', 'refused'] as const)('records %s and refreshes the global and project panels', async (decision) => {
    const invalidate = renderPanel()
    fireEvent.click(await screen.findByRole('button', { name: decision === 'granted' ? 'Mark granted' : 'Refuse' }))
    await waitFor(() => expect(api.accessRequestsApi.decide).toHaveBeenCalledWith(7, decision))
    await waitFor(() => expect(invalidate).toHaveBeenCalledWith({ queryKey: ['access-requests'] }))
    expect(saved).toHaveBeenCalledWith('Access request')
  })

  it('keeps the project filter on the existing project panel', async () => {
    renderPanel('PRJ')
    await screen.findByRole('button', { name: 'Mark granted' })
    expect(api.accessRequestsApi.list).toHaveBeenCalledWith({ status: 'pending', project_prefix: 'PRJ' })
  })

  it('shows a global empty state while keeping empty project panels hidden', async () => {
    vi.mocked(api.accessRequestsApi.list).mockResolvedValue([])
    renderPanel()
    expect(await screen.findByText('No pending requests.')).toBeTruthy()
    cleanup()
    renderPanel('PRJ', false)
    await waitFor(() => expect(screen.queryByText('Loading requests…')).toBeNull())
    expect(screen.queryByText('Access requests')).toBeNull()
  })

  it('reports load and decision errors without recording success', async () => {
    vi.mocked(api.accessRequestsApi.list).mockRejectedValueOnce(new Error('offline'))
    renderPanel()
    expect((await screen.findByRole('alert')).textContent).toContain('Could not load access requests.')
    cleanup()
    vi.mocked(api.accessRequestsApi.decide).mockRejectedValueOnce(new Error('already answered'))
    renderPanel()
    fireEvent.click(await screen.findByRole('button', { name: 'Refuse' }))
    await waitFor(() => expect(failed).toHaveBeenCalledWith('Answering the access request', expect.any(Error)))
    expect(saved).not.toHaveBeenCalled()
  })

  it('blocks repeated clicks while a decision is pending', async () => {
    let finish!: (value: never) => void
    vi.mocked(api.accessRequestsApi.decide).mockImplementationOnce(() => new Promise((resolve) => { finish = resolve }))
    renderPanel()
    const button = await screen.findByRole('button', { name: 'Mark granted' })
    fireEvent.click(button)
    await waitFor(() => expect((button as HTMLButtonElement).disabled).toBe(true))
    expect((screen.getByRole('button', { name: 'Refuse' }) as HTMLButtonElement).disabled).toBe(true)
    fireEvent.click(button)
    expect(api.accessRequestsApi.decide).toHaveBeenCalledTimes(1)
    finish(request as never)
    await waitFor(() => expect((button as HTMLButtonElement).disabled).toBe(false))
  })
})
