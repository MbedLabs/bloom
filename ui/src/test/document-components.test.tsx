// @vitest-environment jsdom
/**
 * The two panels that hang off a document: its links and its tracker.
 *
 * Relationships are the point of a PLM tool - a requirement is only as good as
 * what verifies it - and the tracker panel is the one place a project's GitHub
 * or GitLab credentials are entered. Neither had meaningful coverage, so the
 * rules they enforce (a document cannot link to itself; a new integration
 * cannot be created without a token; only an administrator may touch either)
 * were unchecked.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { settle } from './settle'

import { ToastProvider } from '../components/Toast'
import type { User } from '../api/client'
import {
  attachment,
  docShell,
  integrationSetting,
  link,
  resetApiMocks,
  testCaseDocShell,
  user,
} from './apiFixtures'

let currentUser: User = user

vi.mock('../api/client', async (importOriginal) => {
  const { mockApiModule: build } = await import('./apiFixtures')
  return build(await importOriginal<Record<string, unknown>>(), vi)
})

vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: currentUser,
    isLoading: false,
    isAuthenticated: true,
    login: vi.fn(),
    logout: vi.fn(),
    refreshUser: vi.fn(),
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => children,
}))

const client = await import('../api/client')
const DocumentAttachmentsPanel = (await import('../components/DocumentAttachmentsPanel')).default
const { DocumentLinksPanel } = await import('../components/DocumentLinksPanel')
const IntegrationSettingsPanel = (await import('../components/IntegrationSettingsPanel')).default

function renderPanel(element: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <MemoryRouter>{element}</MemoryRouter>
      </ToastProvider>
    </QueryClientProvider>,
  )
}

function linksPanel() {
  return renderPanel(
    <DocumentLinksPanel
      projectId={1}
      projectPrefix="VCU"
      sourceType="TC"
      sourceId={21}
      sourceDocId="VCU-TC-001"
    />,
  )
}

/** The arguments of the most recent call to a mocked endpoint. */
function lastCall(fn: unknown): unknown[] {
  const mock = vi.mocked(fn as (...args: unknown[]) => unknown)
  expect(mock.mock.calls.length).toBeGreaterThan(0)
  return mock.mock.calls[mock.mock.calls.length - 1]
}

beforeEach(() => {
  vi.clearAllMocks()
  // An override installed with `mockResolvedValue` outlives `clearAllMocks`,
  // so without this one test's stubbing leaks into every test after it.
  resetApiMocks(client as unknown as Record<string, unknown>, vi)
  currentUser = user
  window.confirm = () => true
})

afterEach(cleanup)

describe('the files attached to a document', () => {
  function attachmentsPanel() {
    return renderPanel(<DocumentAttachmentsPanel documentId={11} />)
  }

  it('shows the files and their source', async () => {
    attachmentsPanel()

    expect(await screen.findByText(attachment.original_filename)).toBeTruthy()
    expect(screen.getByText('1.5 KB · from Bud run 77')).toBeTruthy()
    expect(client.attachmentsApi.list).toHaveBeenCalledWith(11)
  })

  it('lets an editor attach and remove a file', async () => {
    attachmentsPanel()
    await screen.findByText(attachment.original_filename)

    const file = new File(['new report'], 'new-report.pdf', { type: 'application/pdf' })
    fireEvent.change(screen.getByLabelText('Attach a file'), { target: { files: [file] } })
    await waitFor(() => expect(client.attachmentsApi.upload).toHaveBeenCalledWith(11, file))

    fireEvent.click(screen.getByTitle('Remove attachment'))
    await waitFor(() => expect(client.attachmentsApi.remove).toHaveBeenCalledWith(attachment.id))
  })

  it('downloads using the name returned by the service', async () => {
    const url = 'blob:verification-report'
    const createObjectURL = vi.fn(() => url)
    const revokeObjectURL = vi.fn()
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined)
    vi.stubGlobal('URL', { ...URL, createObjectURL, revokeObjectURL })

    attachmentsPanel()
    fireEvent.click(await screen.findByTitle('Download'))

    await waitFor(() => expect(client.attachmentsApi.download).toHaveBeenCalledWith(
      attachment.id,
      attachment.original_filename,
    ))
    await waitFor(() => expect(click).toHaveBeenCalled())
    expect(createObjectURL).toHaveBeenCalled()
    expect(revokeObjectURL).toHaveBeenCalledWith(url)

    click.mockRestore()
    vi.unstubAllGlobals()
  })

  it('keeps attachments read-only for an external user', async () => {
    currentUser = { ...user, role: 'external' as const }
    attachmentsPanel()

    expect(await screen.findByText(attachment.original_filename)).toBeTruthy()
    expect(screen.queryByRole('button', { name: /attach file/i })).toBeNull()
    expect(screen.queryByTitle('Remove attachment')).toBeNull()
    expect(screen.getByTitle('Download')).toBeTruthy()
  })

  it('states plainly when no files are attached', async () => {
    vi.mocked(client.attachmentsApi.list).mockResolvedValue([])
    attachmentsPanel()

    expect(await screen.findByText('Nothing attached yet.')).toBeTruthy()
  })
})

describe('the links of a document', () => {
  it('shows the relationships the document already has', async () => {
    linksPanel()
    expect(await screen.findByText('Linked Documents')).toBeTruthy()
    await waitFor(() => expect(client.linksApi.list).toHaveBeenCalled())
    // The fixture links this test case to a requirement, as verifying it.
    await waitFor(() => expect(screen.queryByText('No links yet.')).toBeNull())
  })

  it('says plainly when there are none', async () => {
    vi.mocked(client.linksApi.list).mockResolvedValue([])
    linksPanel()
    expect(await screen.findByText('No links yet.')).toBeTruthy()
  })

  it('scopes the lookup to the project the document belongs to', async () => {
    linksPanel()
    await screen.findByText('Linked Documents')
    await waitFor(() => {
      const [params] = lastCall(client.linksApi.list) as [{ project_id: number }]
      expect(params.project_id).toBe(1)
    })
  })

  it('offers linking only to someone who may edit', async () => {
    linksPanel()
    expect(await screen.findByRole('button', { name: /link artefact/i })).toBeTruthy()
    cleanup()

    currentUser = { ...user, role: 'external' as const }
    linksPanel()
    await screen.findByText('Linked Documents')
    expect(screen.queryByRole('button', { name: /link artefact/i })).toBeNull()
  })

  it('never offers the document itself as a link target', async () => {
    vi.mocked(client.docsApi.list).mockResolvedValue({
      items: [docShell, testCaseDocShell],
      total: 2,
      skip: 0,
      limit: 50,
    } as Awaited<ReturnType<typeof client.docsApi.list>>)
    linksPanel()

    fireEvent.click(await screen.findByRole('button', { name: /link artefact/i }))
    await screen.findByTitle(/filter targets/i)

    // The source is VCU-TC-001; only the requirement may be picked.
    expect(await screen.findByText(/VCU-REQ-001/)).toBeTruthy()
    expect(screen.queryByText('VCU-TC-001')).toBeNull()
  })

  it('asks for the linked documents by key, never for the project', async () => {
    linksPanel()
    await screen.findByText('Linked Documents')

    await waitFor(() => expect(client.docsApi.list).toHaveBeenCalled())
    const calls = vi.mocked(client.docsApi.list).mock.calls
    // The fixture links VCU-TC-001 to requirement 11; that is the one label
    // this panel needs, and the only document it may ask for. Reading the
    // whole registry to find one title is what this replaced.
    for (const [, params] of calls as [string, { keys?: string[]; type?: string[] }][]) {
      expect(params?.keys ?? params?.type).toBeTruthy()
    }
    const keyed = (calls as [string, { keys?: string[] }][]).find(([, p]) => p?.keys)
    expect(keyed?.[1].keys).toEqual(['REQ:11'])
  })

  it('labels a link with the document it points at', async () => {
    linksPanel()
    await screen.findByText('Linked Documents')

    // Without the label the chip falls back to a bare row id, which tells a
    // reader nothing about what the document is linked to.
    expect(await screen.findByText('VCU-REQ-001')).toBeTruthy()
  })

  it('asks for nothing at all when the document has no links', async () => {
    vi.mocked(client.linksApi.list).mockResolvedValue([])
    linksPanel()
    await screen.findByText('No links yet.')

    await settle()
    expect(client.docsApi.list).not.toHaveBeenCalled()
  })

  it('offers the kinds the project holds, without reading its documents', async () => {
    linksPanel()
    fireEvent.click(await screen.findByRole('button', { name: /link artefact/i }))

    // One row per type answers "which kinds can I link to", which the picker
    // used to work out by folding every document in the project.
    await waitFor(() => expect(client.docsApi.typeSummary).toHaveBeenCalledWith('VCU'))
  })

  it('searches for link targets on the server, a page at a time', async () => {
    linksPanel()
    fireEvent.click(await screen.findByRole('button', { name: /link artefact/i }))
    await screen.findByTitle(/filter targets/i)

    fireEvent.change(screen.getByTitle(/filter targets/i), { target: { value: 'boot' } })

    await waitFor(() => {
      const [, params] = lastCall(client.docsApi.list) as [
        string,
        { q?: string; limit?: number; type?: string[] },
      ]
      expect(params.q).toBe('boot')
      expect(params.limit).toBe(50)
      expect(params.type).toEqual(['REQ'])
    })
  })

  it('says when the picker is showing only part of what matches', async () => {
    vi.mocked(client.docsApi.list).mockResolvedValue({
      items: [docShell], total: 612, skip: 0, limit: 50,
    } as Awaited<ReturnType<typeof client.docsApi.list>>)
    linksPanel()

    fireEvent.click(await screen.findByRole('button', { name: /link artefact/i }))

    expect(await screen.findByText(/611 more match/)).toBeTruthy()
  })

  it('removes a relationship', async () => {
    linksPanel()
    await screen.findByText('Linked Documents')
    await waitFor(() => expect(screen.queryByText('No links yet.')).toBeNull())

    fireEvent.click((await screen.findAllByTitle('Remove link'))[0])

    // react-query hands the mutation a context object alongside the id.
    await waitFor(() => expect(client.linksApi.delete).toHaveBeenCalled())
    expect(vi.mocked(client.linksApi.delete).mock.calls[0][0]).toBe(link.id)
  })
})

describe('the external tracker of a project', () => {
  function trackerPanel() {
    return renderPanel(<IntegrationSettingsPanel projectId={1} />)
  }

  it('reports what is configured', async () => {
    trackerPanel()
    // A token is on file, so the field offers to replace it rather than to set
    // one - that is the only way the panel reveals a credential exists.
    expect(await screen.findByText(/replace token/i)).toBeTruthy()
    expect((screen.getByLabelText('GitHub') as HTMLInputElement).checked).toBe(true)
  })

  it('is read-only for anyone but an administrator', async () => {
    currentUser = { ...user, role: 'maintainer' as const }
    trackerPanel()

    expect(await screen.findByText(/is configured for this project/i)).toBeTruthy()
    expect(screen.queryByRole('button', { name: /save integration/i })).toBeNull()
  })

  it('refuses to create an integration with no token', async () => {
    vi.mocked(client.integrationsApi.listSettings).mockResolvedValue([])
    trackerPanel()
    await screen.findByRole('button', { name: /save integration/i })

    fireEvent.click(screen.getByLabelText('GitHub'))
    fireEvent.click(screen.getByRole('button', { name: /save integration/i }))

    // Without a credential the integration could never authenticate.
    expect(await screen.findByText(/enter an api token/i)).toBeTruthy()
    await settle()
    expect(client.integrationsApi.createSetting).not.toHaveBeenCalled()
  })

  it('creates the integration once a token is supplied', async () => {
    vi.mocked(client.integrationsApi.listSettings).mockResolvedValue([])
    trackerPanel()
    await screen.findByRole('button', { name: /save integration/i })

    fireEvent.click(screen.getByLabelText('GitHub'))
    fireEvent.change(await screen.findByPlaceholderText(/ghp_/), {
      target: { value: 'ghp_a-real-looking-token' },
    })
    fireEvent.click(screen.getByRole('button', { name: /save integration/i }))

    await waitFor(() => expect(client.integrationsApi.createSetting).toHaveBeenCalled())
    const [payload] = lastCall(client.integrationsApi.createSetting) as [
      { tracker: string; project_id: number },
    ]
    expect(payload.tracker).toBe('github')
    expect(payload.project_id).toBe(1)
  })

  it('asks for a base URL for a self-hosted GitLab', async () => {
    vi.mocked(client.integrationsApi.listSettings).mockResolvedValue([])
    trackerPanel()
    await screen.findByRole('button', { name: /save integration/i })

    fireEvent.click(screen.getByLabelText('GitLab'))

    expect(await screen.findByPlaceholderText('https://gitlab.example.com')).toBeTruthy()
  })

  it('never shows the stored token back', async () => {
    trackerPanel()
    await screen.findByText(/replace token/i)

    // The API returns only `has_token`; the secret itself is encrypted at rest
    // and never travels back, so the field starts empty.
    const tokenField = screen.getByPlaceholderText(/ghp_/) as HTMLInputElement
    expect(tokenField.value).toBe('')
  })

  it('has nothing to save until something is changed', async () => {
    trackerPanel()
    const save = (await screen.findByRole('button', {
      name: /save integration/i,
    })) as HTMLButtonElement

    expect(save.disabled).toBe(true)
    fireEvent.change(screen.getByPlaceholderText(/shared secret/i), {
      target: { value: 'a-new-secret' },
    })
    await waitFor(() => expect(save.disabled).toBe(false))
  })

  it('keeps the stored token when the field is left empty', async () => {
    trackerPanel()
    await screen.findByText(/replace token/i)

    fireEvent.change(screen.getByPlaceholderText(/shared secret/i), {
      target: { value: 'a-new-secret' },
    })
    fireEvent.click(screen.getByRole('button', { name: /save integration/i }))

    await waitFor(() => expect(client.integrationsApi.updateSetting).toHaveBeenCalled())
    const [id, payload] = lastCall(client.integrationsApi.updateSetting) as [
      number,
      Record<string, unknown>,
    ]
    expect(id).toBe(integrationSetting.id)
    expect(payload.webhook_secret).toBe('a-new-secret')
    // Omitting the key is what tells the server to leave the credential alone;
    // sending an empty string would wipe it.
    expect('token' in payload).toBe(false)
  })

  it('replaces the token when a new one is typed', async () => {
    trackerPanel()
    await screen.findByText(/replace token/i)

    fireEvent.change(screen.getByPlaceholderText(/ghp_/), { target: { value: 'ghp_replacement' } })
    fireEvent.click(screen.getByRole('button', { name: /save integration/i }))

    await waitFor(() =>
      expect((lastCall(client.integrationsApi.updateSetting)[1] as { token?: string }).token).toBe(
        'ghp_replacement',
      ),
    )
  })

  it('turns an integration off without removing it', async () => {
    trackerPanel()
    await screen.findByText(/replace token/i)

    fireEvent.click(screen.getByLabelText('Enabled'))
    fireEvent.click(screen.getByRole('button', { name: /save integration/i }))

    await waitFor(() =>
      expect(
        (lastCall(client.integrationsApi.updateSetting)[1] as { enabled: boolean }).enabled,
      ).toBe(false),
    )
    await settle()
    expect(client.integrationsApi.deleteSetting).not.toHaveBeenCalled()
  })

  it('never sends a base URL for GitHub, which has only one', async () => {
    trackerPanel()
    await screen.findByText(/replace token/i)

    expect(screen.queryByPlaceholderText('https://gitlab.example.com')).toBeNull()
    fireEvent.change(screen.getByPlaceholderText(/ghp_/), { target: { value: 'ghp_x' } })
    fireEvent.click(screen.getByRole('button', { name: /save integration/i }))

    await waitFor(() =>
      expect(
        (lastCall(client.integrationsApi.updateSetting)[1] as { base_url?: string }).base_url,
      ).toBeUndefined(),
    )
  })

  it('asks before removing a tracker that holds credentials', async () => {
    const asked: string[] = []
    window.confirm = (message?: string) => {
      asked.push(message ?? '')
      return true
    }
    trackerPanel()
    await screen.findByText(/replace token/i)

    fireEvent.click(screen.getByLabelText('None'))
    fireEvent.click(screen.getByRole('button', { name: /save integration/i }))

    await waitFor(() => expect(client.integrationsApi.deleteSetting).toHaveBeenCalled())
    expect(vi.mocked(client.integrationsApi.deleteSetting).mock.calls[0][0]).toBe(
      integrationSetting.id,
    )
    expect(asked.join(' ')).toMatch(/remove all external tracker configuration/i)
  })

  it('leaves the tracker alone when that question is declined', async () => {
    window.confirm = () => false
    trackerPanel()
    await screen.findByText(/replace token/i)

    fireEvent.click(screen.getByLabelText('None'))
    fireEvent.click(screen.getByRole('button', { name: /save integration/i }))

    await waitFor(() => expect(client.integrationsApi.deleteSetting).not.toHaveBeenCalled())
    // Backing out is not a failure, so nothing is reported as one.
    expect(screen.queryByText(/failed to save integration/i)).toBeNull()
  })

  it('does not ask when the tracker being dropped holds nothing', async () => {
    let asked = false
    window.confirm = () => {
      asked = true
      return true
    }
    vi.mocked(client.integrationsApi.listSettings).mockResolvedValue([
      { ...integrationSetting, has_token: false, has_webhook_secret: false, base_url: null },
    ] as never)
    trackerPanel()
    await screen.findByRole('button', { name: /save integration/i })

    fireEvent.click(screen.getByLabelText('None'))
    fireEvent.click(screen.getByRole('button', { name: /save integration/i }))

    await waitFor(() => expect(client.integrationsApi.deleteSetting).toHaveBeenCalled())
    expect(asked).toBe(false)
  })

  it('removes the old tracker when switching to the other one', async () => {
    trackerPanel()
    await screen.findByText(/replace token/i)

    fireEvent.click(screen.getByLabelText('GitLab'))
    fireEvent.change(await screen.findByPlaceholderText('https://gitlab.example.com'), {
      target: { value: 'https://gitlab.example.com' },
    })
    fireEvent.change(screen.getByPlaceholderText(/glpat-/), { target: { value: 'glpat-token' } })
    fireEvent.click(screen.getByRole('button', { name: /save integration/i }))

    // At most one tracker per project, so the GitHub row goes before the
    // GitLab one is created.
    await waitFor(() => expect(client.integrationsApi.createSetting).toHaveBeenCalled())
    expect(vi.mocked(client.integrationsApi.deleteSetting).mock.calls[0][0]).toBe(
      integrationSetting.id,
    )
    const [payload] = lastCall(client.integrationsApi.createSetting) as [Record<string, unknown>]
    expect(payload).toMatchObject({
      tracker: 'gitlab',
      base_url: 'https://gitlab.example.com',
      token: 'glpat-token',
    })
  })

  it('keeps the old tracker when the swap is declined', async () => {
    window.confirm = () => false
    trackerPanel()
    await screen.findByText(/replace token/i)

    fireEvent.click(screen.getByLabelText('GitLab'))
    fireEvent.change(await screen.findByPlaceholderText(/glpat-/), {
      target: { value: 'glpat-token' },
    })
    fireEvent.click(screen.getByRole('button', { name: /save integration/i }))

    await waitFor(() => expect(client.integrationsApi.deleteSetting).not.toHaveBeenCalled())
    await settle()
    expect(client.integrationsApi.createSetting).not.toHaveBeenCalled()
  })

  it('clears the form when the tracker is set back to none', async () => {
    trackerPanel()
    await screen.findByText(/replace token/i)

    fireEvent.click(screen.getByLabelText('None'))

    // No tracker means no credentials to enter.
    await waitFor(() => expect(screen.queryByPlaceholderText(/ghp_/)).toBeNull())
    expect(screen.queryByText(/inbound webhook/i)).toBeNull()
  })

  it('names the webhook the tracker should call', async () => {
    trackerPanel()
    await screen.findByText(/replace token/i)

    expect(screen.getByText('/api/integrations/github/webhook')).toBeTruthy()

    fireEvent.click(screen.getByLabelText('GitLab'))
    expect(await screen.findByText('/api/integrations/gitlab/webhook')).toBeTruthy()
  })

  it('reports a refusal from the server', async () => {
    vi.mocked(client.integrationsApi.updateSetting).mockRejectedValueOnce(
      Object.assign(new Error('Request failed'), {
        isAxiosError: true,
        response: { data: { detail: 'That token was rejected by GitHub' } },
      }),
    )
    trackerPanel()
    await screen.findByText(/replace token/i)

    fireEvent.change(screen.getByPlaceholderText(/ghp_/), { target: { value: 'ghp_wrong' } })
    fireEvent.click(screen.getByRole('button', { name: /save integration/i }))

    expect((await screen.findAllByText(/rejected by github/i)).length).toBeGreaterThan(0)
  })
})
