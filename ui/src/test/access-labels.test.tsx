import { createQueryClient } from '../lib/queryClient'
// @vitest-environment jsdom
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { notificationsApi } from '../api/client'
import { roleLabel } from '../lib/roles'

const auth = vi.hoisted(() => ({
  user: { id: 1, email: 'rita@x.io', full_name: 'Rita Reed', role: 'admin' },
}))

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ user: auth.user, logout: vi.fn() }),
}))
vi.mock('../hooks/useDarkMode', () => ({
  useDarkMode: () => [false, vi.fn()] as const,
}))
vi.mock('../hooks/useProjectPermissions', () => ({
  useProjectPermissions: () => ({ can: () => true, permissions: {} }),
}))
vi.mock('../api/client', () => ({
  APP_VERSION: 'test',
  projectsApi: { list: vi.fn().mockResolvedValue([]) },
  searchApi: { global: vi.fn().mockResolvedValue([]) },
  notificationsApi: {
    unreadCount: vi.fn().mockResolvedValue(0),
    list: vi.fn().mockResolvedValue([]),
    markRead: vi.fn(),
    markAllRead: vi.fn(),
  },
}))

const Layout = (await import('../components/Layout')).default

function renderLayout() {
  const client = createQueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <Layout />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

afterEach(cleanup)

describe('access labels', () => {
  it('names each stored role by its label', () => {
    expect(['admin', 'maintainer', 'external'].map(roleLabel)).toEqual(['Admin', 'Maintainer', 'Viewer'])
  })

  it('calls the administrators sidebar entry Access', () => {
    auth.user = { ...auth.user, role: 'admin' }
    renderLayout()
    const entry = screen.getByRole('link', { name: 'Access' })
    expect(entry.getAttribute('href')).toBe('/access')
    expect(screen.queryByRole('link', { name: 'Groups' })).toBeNull()
  })

  it('shows an external user as Viewer in the user menu', () => {
    auth.user = { ...auth.user, role: 'external' }
    renderLayout()
    fireEvent.click(screen.getByText('RR').closest('button') as HTMLElement)
    expect(screen.getByText('Viewer')).toBeTruthy()
    expect(screen.queryByText(/^external$/i)).toBeNull()
  })
})


it('shows the acting account picture in the notification menu', async () => {
  vi.mocked(notificationsApi.list).mockResolvedValue({
    items: [{ id: 71, event_type: 'assignment', title: 'Review assignment', body: 'Ada assigned you as reviewer.', actor_user_id: 11, actor_name: 'Ada Lovelace', actor_profile_picture_url: 'data:image/png;base64,YWRh', project_id: 1, link_path: null, read_at: null, created_at: '2026-10-10T12:00:00Z' }], total: 1, unread: 1,
  })
  renderLayout()
  fireEvent.click(screen.getByRole('button', { name: 'Notifications' }))
  const image = await screen.findByAltText("Ada Lovelace's profile picture")
  expect(image.getAttribute('src')).toBe('data:image/png;base64,YWRh')
  expect(screen.getByText('Ada assigned you as reviewer.')).toBeTruthy()
})
