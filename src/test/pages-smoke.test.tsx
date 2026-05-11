import { describe, expect, it, vi, beforeEach } from 'vitest'
import type { ReactNode } from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'

import App from '../App'

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: {
      id: 1,
      email: 'tester@example.com',
      full_name: 'Tester',
      role: 'admin',
      is_active: true,
      created_at: '',
      updated_at: '',
    },
    isAuthenticated: true,
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
  }),
}))

vi.mock('../components/ProtectedRoute', () => ({
  default: ({ children }: { children: ReactNode }) => <>{children}</>,
}))

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return {
    ...actual,
    dashboardApi: {
      ...actual.dashboardApi,
      getStats: vi.fn().mockResolvedValue({}),
    },
    projectsApi: {
      ...actual.projectsApi,
      list: vi.fn().mockResolvedValue([]),
    },
    docsApi: {
      ...actual.docsApi,
      list: vi.fn().mockResolvedValue([]),
    },
    usersApi: {
      ...actual.usersApi,
      list: vi.fn().mockResolvedValue([]),
    },
  }
})

function renderAt(path: string) {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })

  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe('route smoke (Bloom)', () => {
  it('shows Settings headings at /settings', async () => {
    renderAt('/settings')
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /^Appearance$/ })).toBeInTheDocument()
    })
    expect(screen.getByRole('heading', { name: /PLM Integration Token Management/i })).toBeInTheDocument()
  })

  it('documents registry shows Requirements title when type=requirements', async () => {
    renderAt('/projects/DEMO/docs?type=requirements')
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Requirements' })).toBeInTheDocument()
    })
  })

  it('shows dashboard headline at / after stats resolve', async () => {
    renderAt('/')
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Bloom Dashboard/i })).toBeInTheDocument()
    })
  })
})
