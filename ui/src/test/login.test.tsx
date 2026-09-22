// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import Login from '../pages/Login'
import { setupApi } from '../api/client'

const login = vi.fn()
const navigate = vi.fn()

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ login }),
}))

vi.mock('react-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('react-router')>()
  return { ...actual, useNavigate: () => navigate }
})

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return {
    ...actual,
    setupApi: {
      ...actual.setupApi,
      getStatus: vi.fn().mockResolvedValue({ setup_required: false }),
    },
  }
})

const renderLogin = () =>
  render(
    <MemoryRouter>
      <Login />
    </MemoryRouter>,
  )

beforeEach(() => {
  login.mockReset()
  navigate.mockReset()
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('Login', () => {
  it('signs in and navigates home on success', async () => {
    login.mockResolvedValue(undefined)
    renderLogin()

    fireEvent.change(screen.getByPlaceholderText('you@company.com'), {
      target: { value: 'admin@bloom.example' },
    })
    fireEvent.change(screen.getByPlaceholderText('Enter your password'), {
      target: { value: 'secret-password' },
    })
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() =>
      expect(login).toHaveBeenCalledWith('admin@bloom.example', 'secret-password'),
    )
    await waitFor(() => expect(navigate).toHaveBeenCalledWith('/', { replace: true }))
  })

  it('shows an error message when sign in fails', async () => {
    login.mockRejectedValue(new Error('bad creds'))
    renderLogin()

    fireEvent.change(screen.getByPlaceholderText('you@company.com'), {
      target: { value: 'admin@bloom.example' },
    })
    fireEvent.change(screen.getByPlaceholderText('Enter your password'), {
      target: { value: 'wrong' },
    })
    fireEvent.click(screen.getByRole('button', { name: /sign in/i }))

    expect(await screen.findByText('bad creds')).toBeInTheDocument()
    expect(navigate).not.toHaveBeenCalledWith('/', { replace: true })
  })

  it('stays on the form when the setup status check fails', async () => {
    vi.mocked(setupApi.getStatus).mockRejectedValueOnce(new Error('offline'))
    renderLogin()

    expect(await screen.findByRole('button', { name: /sign in/i })).toBeInTheDocument()
    expect(navigate).not.toHaveBeenCalled()
  })
})
