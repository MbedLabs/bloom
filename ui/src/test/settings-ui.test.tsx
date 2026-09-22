// @vitest-environment jsdom

import '@testing-library/jest-dom/vitest'
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import Settings from '../pages/Settings'
import { companyLogoApi } from '../api/client'

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: {
      id: 1,
      email: 'admin@bloom.example',
      full_name: 'Bloom Admin',
      role: 'admin',
      is_active: true,
      created_at: '',
      updated_at: '',
    },
    refreshUser: vi.fn(),
  }),
}))

vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return {
    ...actual,
    serviceCredentialsApi: {
      ...actual.serviceCredentialsApi,
      list: vi.fn().mockResolvedValue([]),
    },
    companyLogoApi: {
      fetchLogo: vi.fn(),
      setLogo: vi.fn(),
      deleteLogo: vi.fn(),
    },
  }
})

const logoSection = (): HTMLElement =>
  screen.getByRole('heading', { name: 'Company logo' }).closest('.bg-card') as HTMLElement

beforeEach(() => {
  const storage = {
    getItem: vi.fn(() => null),
    setItem: vi.fn(),
    removeItem: vi.fn(),
    clear: vi.fn(),
    key: vi.fn(() => null),
    length: 0,
  }
  vi.stubGlobal('localStorage', storage)
  Object.defineProperty(window, 'localStorage', {
    value: storage,
    writable: true,
    configurable: true,
  })
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    configurable: true,
    value: vi.fn((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: (): void => undefined,
      removeListener: (): void => undefined,
      addEventListener: (): void => undefined,
      removeEventListener: (): void => undefined,
      dispatchEvent: (): boolean => false,
    })),
  })
  URL.createObjectURL = vi.fn(() => 'blob:mock')
  URL.revokeObjectURL = vi.fn()
  vi.mocked(companyLogoApi.fetchLogo).mockResolvedValue(null)
  vi.mocked(companyLogoApi.setLogo).mockResolvedValue({ content_type: 'image/png', size: 3 })
  vi.mocked(companyLogoApi.deleteLogo).mockResolvedValue(undefined)
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('Settings', () => {
  it('keeps the historical PLM integration section name', () => {
    render(<Settings />)

    expect(
      screen.getByRole('heading', { name: 'PLM Integration Token Management' }),
    ).toBeInTheDocument()
    expect(screen.queryByText('Bud Result-Sync Credentials')).not.toBeInTheDocument()
  })

  it('shows the stored company logo preview to an administrator', async () => {
    vi.mocked(companyLogoApi.fetchLogo).mockResolvedValue(new Blob(['x'], { type: 'image/png' }))
    render(<Settings />)

    expect(await within(logoSection()).findByAltText('Company logo')).toBeInTheDocument()
    expect(companyLogoApi.fetchLogo).toHaveBeenCalled()
  })

  it('uploads a selected company logo', async () => {
    render(<Settings />)
    const section = logoSection()
    const file = new File(['logo'], 'logo.png', { type: 'image/png' })
    fireEvent.change(section.querySelector('input[type="file"]') as HTMLInputElement, {
      target: { files: [file] },
    })
    fireEvent.click(within(section).getByRole('button', { name: 'Upload logo' }))

    expect(await within(section).findByText('Logo updated.')).toBeInTheDocument()
    expect(companyLogoApi.setLogo).toHaveBeenCalledWith(file)
  })

  it('removes the company logo', async () => {
    render(<Settings />)
    const section = logoSection()
    fireEvent.click(within(section).getByRole('button', { name: 'Remove' }))

    expect(await within(section).findByText('Logo removed.')).toBeInTheDocument()
    expect(companyLogoApi.deleteLogo).toHaveBeenCalled()
  })

  it('reports an error when the logo upload fails', async () => {
    vi.mocked(companyLogoApi.setLogo).mockRejectedValue(new Error('nope'))
    render(<Settings />)
    const section = logoSection()
    const file = new File(['logo'], 'logo.png', { type: 'image/png' })
    fireEvent.change(section.querySelector('input[type="file"]') as HTMLInputElement, {
      target: { files: [file] },
    })
    fireEvent.click(within(section).getByRole('button', { name: 'Upload logo' }))

    const status = await within(section).findByRole('status')
    expect(status).not.toHaveTextContent('Logo updated.')
    expect(companyLogoApi.setLogo).toHaveBeenCalled()
  })

  it('reports an error when removing the logo fails', async () => {
    vi.mocked(companyLogoApi.deleteLogo).mockRejectedValue(new Error('nope'))
    render(<Settings />)
    const section = logoSection()
    fireEvent.click(within(section).getByRole('button', { name: 'Remove' }))

    const status = await within(section).findByRole('status')
    expect(status).not.toHaveTextContent('Logo removed.')
    expect(companyLogoApi.deleteLogo).toHaveBeenCalled()
  })
})
