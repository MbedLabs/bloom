// @vitest-environment jsdom
import '@testing-library/jest-dom/vitest'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { StrictMode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { authApi, companyLogoApi } from '../api/client'
import Settings from '../pages/Settings'

const refreshUser = vi.hoisted(() => vi.fn(async () => undefined))
const account = vi.hoisted(() => ({
  id: 7, email: 'picture@example.com', full_name: 'Picture User', role: 'external',
  is_active: true, has_profile_picture: false, created_at: '', updated_at: '',
}))

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ user: account, refreshUser }),
}))
vi.mock('../api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/client')>()
  return { ...actual, authApi: { ...actual.authApi,
    setProfilePicture: vi.fn(), fetchProfilePicture: vi.fn(), deleteProfilePicture: vi.fn(),
  }, companyLogoApi: { ...actual.companyLogoApi, fetchLogo: vi.fn(), deleteLogo: vi.fn() },
    serviceCredentialsApi: { ...actual.serviceCredentialsApi, list: vi.fn(async () => []) },
  }
})

beforeEach(() => {
  vi.clearAllMocks()
  account.role = 'external'
  account.has_profile_picture = false
  vi.mocked(companyLogoApi.fetchLogo).mockResolvedValue(null)
  window.localStorage.clear()
  window.matchMedia = vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() })) as unknown as typeof window.matchMedia
  URL.createObjectURL = vi.fn(() => 'blob:profile')
  URL.revokeObjectURL = vi.fn()
})
afterEach(() => {
  cleanup()
  vi.restoreAllMocks()
})

describe('own-account profile picture', () => {
  it('uploads the chosen file and displays the saved authenticated image', async () => {
    vi.mocked(authApi.setProfilePicture).mockResolvedValue({ ...account, role: 'external', has_profile_picture: true, updated_at: 'new' })
    vi.mocked(authApi.fetchProfilePicture).mockResolvedValue(new Blob(['png'], { type: 'image/png' }))
    render(<Settings />)
    const button = screen.getByRole('button', { name: 'Upload' })
    expect(button).toBeDisabled()
    const file = new File(['png'], 'profile.png', { type: 'image/png' })
    fireEvent.change(screen.getByLabelText('Profile picture'), { target: { files: [file] } })
    fireEvent.click(button)
    await waitFor(() => expect(authApi.setProfilePicture).toHaveBeenCalledWith(file))
    expect(await screen.findByText('Profile picture updated.')).toBeInTheDocument()
    expect(await screen.findByAltText('Your profile picture')).toHaveAttribute('src', 'data:image/png;base64,cG5n')
    expect(refreshUser).toHaveBeenCalled()
  })

  it('shows a rejected upload without claiming that it was saved', async () => {
    vi.mocked(authApi.setProfilePicture).mockRejectedValue({ isAxiosError: true, response: { data: { detail: 'The picture is invalid or too large.' } } })
    render(<Settings />)
    fireEvent.change(screen.getByLabelText('Profile picture'), { target: { files: [new File(['bad'], 'bad.png', { type: 'image/png' })] } })
    fireEvent.click(screen.getByRole('button', { name: 'Upload' }))
    expect(await screen.findByText('The picture is invalid or too large.')).toBeInTheDocument()
    expect(screen.queryByText('Profile picture updated.')).not.toBeInTheDocument()
    expect(refreshUser).not.toHaveBeenCalled()
  })

  it('removes a saved own picture and returns to initials', async () => {
    account.has_profile_picture = true
    vi.mocked(authApi.fetchProfilePicture).mockResolvedValue(new Blob(['png'], { type: 'image/png' }))
    vi.mocked(authApi.deleteProfilePicture).mockResolvedValue({ ...account, role: 'external', has_profile_picture: false, updated_at: 'removed' })
    render(<Settings />)
    expect(await screen.findByAltText('Your profile picture')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Remove profile picture' }))
    expect(await screen.findByText('Profile picture removed.')).toBeInTheDocument()
    expect(authApi.deleteProfilePicture).toHaveBeenCalledOnce()
    expect(refreshUser).toHaveBeenCalledOnce()
    expect(screen.queryByAltText('Your profile picture')).not.toBeInTheDocument()
    expect(screen.getByText('PU')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Remove profile picture' })).not.toBeInTheDocument()
  })

  it('keeps a saved own picture when removal fails', async () => {
    account.has_profile_picture = true
    vi.mocked(authApi.fetchProfilePicture).mockResolvedValue(new Blob(['png'], { type: 'image/png' }))
    vi.mocked(authApi.deleteProfilePicture).mockRejectedValue({ isAxiosError: true, response: { data: { detail: 'Could not remove the picture.' } } })
    render(<Settings />)
    expect(await screen.findByAltText('Your profile picture')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Remove profile picture' }))
    expect(await screen.findByText('Could not remove the picture.')).toBeInTheDocument()
    expect(screen.getByAltText('Your profile picture')).toBeInTheDocument()
    expect(screen.queryByText('Profile picture removed.')).not.toBeInTheDocument()
    expect(refreshUser).not.toHaveBeenCalled()
  })

  it('has no picture removal control without a saved picture', () => {
    render(<Settings />)
    expect(screen.queryByRole('button', { name: 'Remove profile picture' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Remove company logo' })).not.toBeInTheDocument()
  })

  it('renders the authenticated company preview in the CSP-supported format and removes it', async () => {
    account.role = 'admin'
    vi.mocked(companyLogoApi.fetchLogo).mockResolvedValueOnce(new Blob(['logo'], { type: 'image/png' })).mockResolvedValue(null)
    vi.mocked(companyLogoApi.deleteLogo).mockResolvedValue(undefined)
    render(<Settings />)
    expect(await screen.findByAltText('Company logo')).toHaveAttribute('src', 'data:image/png;base64,bG9nbw==')
    expect(screen.queryByRole('button', { name: /^Remove$/ })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Remove company logo' }))
    expect(await screen.findByText('Logo removed.')).toBeInTheDocument()
    expect(companyLogoApi.deleteLogo).toHaveBeenCalledOnce()
    expect(screen.getByText('No company logo set yet.')).toBeInTheDocument()
    expect(screen.queryByAltText('Company logo')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Remove company logo' })).not.toBeInTheDocument()
  })

  it('keeps the company preview and shows an error after failed removal', async () => {
    account.role = 'admin'
    vi.mocked(companyLogoApi.fetchLogo).mockResolvedValue(new Blob(['logo'], { type: 'image/png' }))
    vi.mocked(companyLogoApi.deleteLogo).mockRejectedValue({ isAxiosError: true, response: { data: { detail: 'Could not remove the logo.' } } })
    render(<Settings />)
    expect(await screen.findByAltText('Company logo')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Remove company logo' }))
    expect(await screen.findByText('Could not remove the logo.')).toBeInTheDocument()
    expect(screen.getByAltText('Company logo')).toBeInTheDocument()
    expect(screen.queryByText('Logo removed.')).not.toBeInTheDocument()
  })

  it('does not restore a removed company logo when an older preview request finishes', async () => {
    account.role = 'admin'
    const logo = new Blob(['logo'], { type: 'image/png' })
    let finishEarlier!: (value: Blob | null) => void
    const earlier = new Promise<Blob | null>((resolve) => { finishEarlier = resolve })
    vi.mocked(companyLogoApi.fetchLogo).mockReturnValueOnce(earlier).mockResolvedValue(logo)
    vi.mocked(companyLogoApi.deleteLogo).mockResolvedValue(undefined)
    vi.spyOn(FileReader.prototype, 'readAsDataURL').mockImplementation(function (this: FileReader) {
      Object.defineProperty(this, 'result', { value: 'data:image/png;base64,bG9nbw==', configurable: true })
      this.onload?.(new ProgressEvent('load') as ProgressEvent<FileReader>)
    })
    render(<StrictMode><Settings /></StrictMode>)
    expect(await screen.findByAltText('Company logo')).toBeInTheDocument()
    expect(companyLogoApi.fetchLogo).toHaveBeenCalledTimes(2)
    fireEvent.click(screen.getByRole('button', { name: 'Remove company logo' }))
    expect(await screen.findByText('Logo removed.')).toBeInTheDocument()
    expect(screen.queryByAltText('Company logo')).not.toBeInTheDocument()
    await act(async () => { finishEarlier(logo) })
    expect(screen.queryByAltText('Company logo')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Remove company logo' })).not.toBeInTheDocument()
  })
})
