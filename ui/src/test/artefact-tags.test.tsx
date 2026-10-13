import { createQueryClient } from '../lib/queryClient'
// @vitest-environment jsdom
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const auth = vi.hoisted(() => ({ user: { id: 1, role: 'maintainer' } }))

vi.mock('../contexts/AuthContext', () => ({ useAuth: () => ({ user: auth.user }) }))
vi.mock('../components/useToast', () => ({
  useToast: () => ({ saved: vi.fn(), deleted: vi.fn(), failed: vi.fn(), notify: vi.fn() }),
}))
vi.mock('../api/client', () => ({
  artefactTagsApi: {
    get: vi.fn().mockResolvedValue([{ id: 1, name: 'Field', created_at: '' }]),
    set: vi.fn().mockResolvedValue([{ id: 2, name: 'Lab', created_at: '' }]),
  },
  tagsApi: {
    list: vi.fn().mockResolvedValue([
      { id: 1, name: 'Field', created_at: '' },
      { id: 2, name: 'Lab', created_at: '' },
    ]),
  },
}))

const api = await import('../api/client')
const ArtefactTags = (await import('../components/ArtefactTags')).default

function renderTags(canEdit = true, origin?: string) {
  const client = createQueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <ArtefactTags type="requirement" id={9} projectId={7} canEdit={canEdit} origin={origin} />
    </QueryClientProvider>,
  )
}

beforeEach(() => vi.clearAllMocks())
afterEach(cleanup)

describe('document origins', () => {
  it('shows the tags and changes them from the project scope', async () => {
    auth.user = { id: 1, role: 'maintainer' }
    renderTags()
    expect(await screen.findByText('Field')).toBeTruthy()
    fireEvent.click(screen.getByText('Edit origins'))
    await waitFor(() => expect(api.tagsApi.list).toHaveBeenCalledWith(7))
    fireEvent.click(await screen.findByRole('button', { name: 'Field' }))
    fireEvent.click(screen.getByRole('button', { name: 'Lab' }))
    fireEvent.click(screen.getByText('Save origins'))
    await waitFor(() => expect(api.artefactTagsApi.set).toHaveBeenCalledWith('requirement', 9, [2]))
    expect(await screen.findByText('Lab')).toBeTruthy()
  })

  it('retains the built-in origin when there are no custom origins', async () => {
    auth.user = { id: 1, role: 'maintainer' }
    vi.mocked(api.artefactTagsApi.get).mockResolvedValueOnce([])
    vi.mocked(api.tagsApi.list).mockResolvedValueOnce([])
    renderTags(true, 'Internal')
    await waitFor(() => expect(api.tagsApi.list).toHaveBeenCalledWith(7))
    expect(screen.getByText('Internal')).toBeTruthy()
    expect(screen.queryByText('Edit origins')).toBeNull()
    expect(screen.queryByText(/no tags/i)).toBeNull()
    expect(api.artefactTagsApi.set).not.toHaveBeenCalled()
  })

  it('retains the built-in origin if custom-origin loading fails', async () => {
    auth.user = { id: 1, role: 'maintainer' }
    vi.mocked(api.artefactTagsApi.get).mockRejectedValueOnce(new Error('Unavailable'))
    renderTags(false, 'Customer')
    expect(await screen.findByRole('alert')).toHaveProperty('textContent', 'Could not load origins.')
    expect(screen.getByText('Customer')).toBeTruthy()
    expect(screen.queryByText('Edit origins')).toBeNull()
  })

  it('offers no change to an external user or without the edit right', async () => {
    auth.user = { id: 1, role: 'external' }
    renderTags()
    expect(await screen.findByText('Field')).toBeTruthy()
    expect(screen.queryByText('Edit origins')).toBeNull()
    cleanup()
    auth.user = { id: 1, role: 'maintainer' }
    renderTags(false)
    expect(await screen.findByText('Field')).toBeTruthy()
    expect(screen.queryByText('Edit origins')).toBeNull()
  })

  it('cancels a change and keeps editing after a failed save', async () => {
    auth.user = { id: 1, role: 'maintainer' }
    vi.mocked(api.artefactTagsApi.set).mockRejectedValueOnce(new Error('no'))
    renderTags()
    fireEvent.click(await screen.findByText('Edit origins'))
    fireEvent.click(screen.getByText('Cancel'))
    expect(screen.getByText('Edit origins')).toBeTruthy()
    fireEvent.click(screen.getByText('Edit origins'))
    fireEvent.click(screen.getByText('Save origins'))
    await waitFor(() => expect(api.artefactTagsApi.set).toHaveBeenCalled())
    expect(screen.getByText('Save origins')).toBeTruthy()
  })
})
