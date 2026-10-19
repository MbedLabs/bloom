import { createQueryClient } from '../lib/queryClient'
// @vitest-environment jsdom
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { PRODUCT_IDENTITY, PRODUCT_NAME } from '../brandAssets'

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { id: 1, email: 'rita@x.io', full_name: 'Rita Reed', role: 'admin' }, logout: vi.fn() }),
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

/** Render the application shell with an empty project list. */
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

afterEach(() => {
  cleanup()
  localStorage.removeItem('bloom-sidebar-collapsed')
})

describe('product identity', () => {
  it('names the product Bloom PLM by EmbedLabs', () => {
    expect(PRODUCT_NAME).toBe('Bloom PLM')
    expect(PRODUCT_IDENTITY).toBe('Bloom PLM by EmbedLabs')
  })

  it('shows Bloom PLM and by EmbedLabs in the expanded sidebar', () => {
    renderLayout()
    expect(screen.getByRole('heading', { level: 1, name: 'Bloom PLM' })).toBeTruthy()
    expect(screen.getByText('by EmbedLabs')).toBeTruthy()
    expect(screen.getByAltText('Bloom PLM by EmbedLabs')).toBeTruthy()
    expect(screen.queryByText('Product Lifecycle Management')).toBeNull()
  })

  it('shows only the mark in the collapsed sidebar', () => {
    localStorage.setItem('bloom-sidebar-collapsed', 'true')
    renderLayout()
    expect(screen.getByAltText('Bloom PLM by EmbedLabs')).toBeTruthy()
    expect(screen.queryByRole('heading', { level: 1, name: 'Bloom PLM' })).toBeNull()
    expect(screen.queryByText('by EmbedLabs')).toBeNull()
  })
})
