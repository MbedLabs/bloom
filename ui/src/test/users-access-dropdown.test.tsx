import { createQueryClient } from '../lib/queryClient'
// @vitest-environment jsdom

import { ToastProvider } from '../components/Toast'
import '@testing-library/jest-dom/vitest'
import { QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import UsersPage from '../pages/Users'
import { usersApi, type UserAccessSummary } from '../api/client'

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 1, email: 'admin@bloom.example', full_name: 'Bloom Admin', role: 'admin', is_active: true, created_at: '', updated_at: '' },
    refreshUser: vi.fn(),
  }),
}))

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  const person = (id: number, name: string, role: 'admin' | 'maintainer' | 'external') => ({
    id,
    email: `${name.toLowerCase()}@bloom.example`,
    full_name: name,
    role,
    is_active: true,
    created_at: '2026-07-01T12:00:00Z',
    updated_at: '2026-07-01T12:00:00Z',
  })
  return {
    ...actual,
    usersApi: {
      ...actual.usersApi,
      list: vi.fn().mockResolvedValue([person(1, 'Ada', 'admin'), person(2, 'Mia', 'maintainer'), person(3, 'Vic', 'external')]),
      accessSummary: vi.fn(),
    },
  }
})

const summaries: Record<number, UserAccessSummary> = {
  1: { every_project: true, groups: [], projects: [] },
  2: {
    every_project: false,
    groups: ['Authors', 'Reviewers'],
    projects: [
      { project_id: 10, project_name: 'PRJ Alpha', owner: false, groups: ['Authors', 'Reviewers'], direct: false },
      { project_id: 11, project_name: 'PRJ Beta', owner: true, groups: [], direct: false },
      { project_id: 12, project_name: 'PRJ Gamma', owner: false, groups: [], direct: true },
    ],
  },
  3: { every_project: false, groups: [], projects: [] },
}

function renderIt() {
  const queryClient = createQueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <UsersPage />
      </ToastProvider>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  vi.mocked(usersApi.accessSummary).mockImplementation(async (id: number) => summaries[id])
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('access under each user', () => {
  it('starts with every row closed and requests nothing', async () => {
    renderIt()
    await screen.findByText('Vic')
    for (const name of ['Ada', 'Mia', 'Vic']) {
      expect(screen.getByRole('button', { name: `Show access of ${name}` })).toHaveAttribute('aria-expanded', 'false')
    }
    expect(screen.queryByText('Projects')).toBeNull()
    expect(usersApi.accessSummary).not.toHaveBeenCalled()
  })

  it('shows groups and each project with its labels, without permissions, and hides them again', async () => {
    renderIt()
    await screen.findByText('Mia')
    fireEvent.click(screen.getByRole('button', { name: 'Show access of Mia' }))
    expect(await screen.findByText('PRJ Alpha')).toBeInTheDocument()
    expect(screen.getByText(': Authors, Reviewers')).toBeInTheDocument()
    expect(screen.getByText(': Owner')).toBeInTheDocument()
    expect(screen.getByText(': Direct')).toBeInTheDocument()
    expect(screen.getAllByText('Authors')).toHaveLength(1)
    expect(screen.getByRole('button', { name: 'Hide access of Mia' })).toHaveAttribute('aria-expanded', 'true')
    expect(usersApi.accessSummary).toHaveBeenCalledTimes(1)
    expect(usersApi.accessSummary).toHaveBeenCalledWith(2)
    expect(screen.queryByText(/\b(view|create|edit|delete)\b/)).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Hide access of Mia' }))
    expect(screen.queryByText('PRJ Alpha')).toBeNull()
  })

  it('says No groups and No projects for a user without access', async () => {
    renderIt()
    await screen.findByText('Vic')
    fireEvent.click(screen.getByRole('button', { name: 'Show access of Vic' }))
    expect(await screen.findByText('No groups')).toBeInTheDocument()
    expect(screen.getByText('No projects')).toBeInTheDocument()
  })

  it('shows every project for an Admin', async () => {
    renderIt()
    await screen.findByText('Ada')
    fireEvent.click(screen.getByRole('button', { name: 'Show access of Ada' }))
    expect(await screen.findByText('Every project (Admin)')).toBeInTheDocument()
  })

  it('shows an alert when the access cannot load and retries', async () => {
    vi.mocked(usersApi.accessSummary).mockRejectedValueOnce(new Error('down'))
    renderIt()
    await screen.findByText('Mia')
    fireEvent.click(screen.getByRole('button', { name: 'Show access of Mia' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load access.')
    fireEvent.click(screen.getByRole('button', { name: 'Retry' }))
    expect(await screen.findByText('PRJ Alpha')).toBeInTheDocument()
    expect(usersApi.accessSummary).toHaveBeenCalledTimes(2)
  })
})
