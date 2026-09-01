// @vitest-environment jsdom
/**
 * Every endpoint the frontend can call, and the request it actually issues.
 *
 * `api/client.ts` is the whole surface between the app and the backend: ~140
 * one-line wrappers, most of which build their path with a template literal.
 * Nothing checked them, so a wrong variable name in a template silently
 * produced `/requirements/undefined` and only failed in the browser, on the
 * screen that happened to call it.
 *
 * The table below names every method, the arguments a caller passes and the
 * request that must come out. A completeness check walks the exported API
 * objects and fails if a method is missing from it, so a new endpoint cannot be
 * added without a row here.
 */
import axios, { type InternalAxiosRequestConfig } from 'axios'
import { beforeEach, describe, expect, it, vi } from 'vitest'

interface Recorded {
  method: string
  url: string
  data: unknown
  params: unknown
}

const requests: Recorded[] = []
let nextResponse: { status: number; data: unknown; headers: Record<string, string> } = {
  status: 200,
  data: {},
  headers: {},
}

// Installed before the client module is imported: `axios.create()` copies the
// adapter out of the defaults at creation time, so the instance the client
// builds picks this up and no request ever leaves the process.
axios.defaults.adapter = async (config: InternalAxiosRequestConfig) => {
  requests.push({
    method: (config.method ?? '').toLowerCase(),
    url: config.url ?? '',
    data: config.data,
    params: config.params,
  })
  return {
    data: nextResponse.data,
    status: nextResponse.status,
    statusText: 'OK',
    headers: nextResponse.headers,
    config,
    request: {},
  }
}

const client = await import('../api/client')

/** A response body carrying every field the unwrapping methods reach into. */
const BODY = {
  id: 1,
  items: [],
  total: 0,
  next_id: 'VCU-REQ-007',
  unread: 3,
  access_token: 'new-access-token',
  user: { id: 1, email: 'u@example.com' },
}

/**
 * `[method path, arguments, expected request]` for every endpoint.
 *
 * The expected URL is the path as the client writes it — axios appends
 * `params` to it later, so query strings appear here only where the client
 * builds them into the path itself.
 */
const CALLS: Array<[string, unknown[], string, string]> = [
  ['authApi.login', ['u@example.com', 'pw'], 'post', '/auth/login'],
  ['authApi.refresh', [], 'post', '/auth/refresh'],
  ['authApi.logout', [], 'post', '/auth/logout'],
  ['authApi.getMe', [], 'get', '/auth/me'],
  ['authApi.updateMe', [{ full_name: 'New Name' }], 'put', '/auth/me'],
  ['authApi.requestEmailChange', ['pw', 'new@example.com'], 'post', '/auth/me/email'],
  ['authApi.cancelEmailChange', [], 'delete', '/auth/me/email'],
  ['authApi.confirmEmailChange', ['tok'], 'post', '/auth/confirm-email-change'],
  ['authApi.changePassword', ['old', 'new'], 'put', '/auth/me/password'],
  ['authApi.getInviteInfo', ['tok'], 'post', '/auth/invite-info'],
  ['authApi.acceptInvite', ['tok', 'pw'], 'post', '/auth/accept-invite'],
  ['authApi.verifyEmail', ['tok'], 'post', '/auth/verify-email'],
  ['authApi.forgotPassword', ['u@example.com'], 'post', '/auth/forgot-password'],
  ['authApi.resetPassword', ['tok', 'pw'], 'post', '/auth/reset-password'],

  ['setupApi.getStatus', [], 'get', '/setup/status'],
  ['setupApi.createFirstAdmin', ['u@example.com', 'pw', 'Owner'], 'post', '/setup'],

  ['serviceCredentialsApi.list', [], 'get', '/service-credentials'],
  ['serviceCredentialsApi.create', [], 'post', '/service-credentials'],
  ['serviceCredentialsApi.rotate', [7], 'post', '/service-credentials/7/rotate'],
  ['serviceCredentialsApi.revoke', [7], 'delete', '/service-credentials/7'],

  ['usersApi.list', [], 'get', '/users'],
  ['usersApi.listMentionable', [5], 'get', '/users/mentionable'],
  ['usersApi.get', [3], 'get', '/users/3'],
  [
    'usersApi.create',
    [{ email: 'u@example.com', full_name: 'U', password: 'pw' }],
    'post',
    '/users',
  ],
  ['usersApi.invite', [{ email: 'u@example.com', full_name: 'U' }], 'post', '/users/invite'],
  ['usersApi.update', [3, { full_name: 'U' }], 'patch', '/users/3'],
  ['usersApi.startEmailChange', [3, 'new@example.com'], 'post', '/users/3/email'],
  ['usersApi.approveEmailChange', [3], 'post', '/users/3/email/approve'],
  ['usersApi.rejectEmailChange', [3], 'delete', '/users/3/email'],
  ['usersApi.delete', [3], 'delete', '/users/3'],

  ['dashboardApi.getStats', [], 'get', '/dashboard/stats'],

  ['projectsApi.list', [], 'get', '/projects'],
  ['projectsApi.get', [5], 'get', '/projects/5'],
  ['projectsApi.getByPrefix', ['VCU'], 'get', '/projects/by-prefix/VCU'],
  ['projectsApi.create', [{ name: 'P', prefix: 'VCU' }], 'post', '/projects'],
  ['projectsApi.update', [5, { name: 'P2' }], 'patch', '/projects/5'],
  ['projectsApi.delete', [5], 'delete', '/projects/5'],

  ['projectMembersApi.list', [5], 'get', '/projects/5/members'],
  [
    'projectMembersApi.create',
    [5, { user_id: 3, role: 'maintainer' }],
    'post',
    '/projects/5/members',
  ],
  ['projectMembersApi.update', [5, 9, { role: 'external' }], 'patch', '/projects/5/members/9'],
  ['projectMembersApi.remove', [5, 9], 'delete', '/projects/5/members/9'],

  ['attachmentsApi.list', [7], 'get', '/documents/7/attachments'],
  ['attachmentsApi.upload', [7, new File(['x'], 'r.pdf')], 'post', '/documents/7/attachments'],
  ['attachmentsApi.download', [3, 'r.pdf'], 'get', '/attachments/3/download'],
  ['attachmentsApi.remove', [3], 'delete', '/attachments/3'],

  ['docsApi.nextDocId', ['VCU', 'REQ'], 'get', '/projects/VCU/next-doc-id/REQ'],
  ['docsApi.list', ['VCU'], 'get', '/projects/VCU/docs'],
  ['docsApi.typeSummary', ['VCU'], 'get', '/projects/VCU/doc-type-summary'],
  ['docsApi.get', ['VCU', 'REQ', 'VCU-REQ-001'], 'get', '/projects/VCU/docs/requirements/VCU-REQ-001'],

  ['requirementsApi.list', [5], 'get', '/requirements'],
  ['requirementsApi.get', [11], 'get', '/requirements/11'],
  ['requirementsApi.create', [{ project_id: 5, title: 'R' }], 'post', '/requirements'],
  ['requirementsApi.update', [11, { title: 'R2' }], 'patch', '/requirements/11'],
  ['requirementsApi.setReviewed', [11, 3], 'patch', '/requirements/11'],
  ['requirementsApi.setApproved', [11, 3], 'patch', '/requirements/11'],
  ['requirementsApi.delete', [11], 'delete', '/requirements/11'],
  ['requirementsApi.linkTestRun', [11, 42], 'post', '/requirements/11/link-testrun'],
  ['requirementsApi.getTestRuns', [11], 'get', '/requirements/11/test-runs'],

  ['testCasesApi.list', [5], 'get', '/test-cases'],
  ['testCasesApi.get', [12], 'get', '/test-cases/12'],
  ['testCasesApi.create', [{ project_id: 5, title: 'TC' }], 'post', '/test-cases'],
  ['testCasesApi.update', [12, { title: 'TC2' }], 'patch', '/test-cases/12'],
  ['testCasesApi.setReviewed', [12, 3], 'patch', '/test-cases/12'],
  ['testCasesApi.setApproved', [12, 3], 'patch', '/test-cases/12'],
  ['testCasesApi.delete', [12], 'delete', '/test-cases/12'],

  ['traceabilityApi.getMatrix', [5], 'get', '/traceability?project_id=5'],
  ['traceabilityApi.getImpactAnalysis', [11], 'get', '/traceability/impact/11'],
  ['traceabilityApi.getCoverageGaps', [5], 'get', '/traceability/coverage-gaps/5'],

  ['documentsApi.list', [5], 'get', '/projects/5/documents'],
  ['documentsApi.get', [13], 'get', '/documents/13'],
  ['documentsApi.create', [{ project_id: 5, title: 'D' }], 'post', '/projects/5/documents'],
  ['documentsApi.update', [13, { title: 'D2' }], 'patch', '/documents/13'],
  ['documentsApi.delete', [13], 'delete', '/documents/13'],
  ['documentsApi.addSection', [13, { title: 'S' }], 'post', '/documents/13/sections'],
  ['documentsApi.updateSection', [21, { title: 'S2' }], 'patch', '/document-sections/21'],
  ['documentsApi.deleteSection', [21], 'delete', '/document-sections/21'],
  ['documentsApi.reorderSections', [13, [{ id: 21, order: 1 }]], 'post', '/documents/13/sections/reorder'],

  ['projectVariablesApi.list', [5], 'get', '/project-variables'],
  [
    'projectVariablesApi.create',
    [{ project_id: 5, kind: 'parameter', key: 'k', value: 'v' }],
    'post',
    '/project-variables',
  ],
  ['projectVariablesApi.update', [31, { value: 'v2' }], 'patch', '/project-variables/31'],
  ['projectVariablesApi.delete', [31], 'delete', '/project-variables/31'],

  ['campaignsApi.list', [5], 'get', '/campaigns?project_id=5'],
  ['campaignsApi.get', [41], 'get', '/campaigns/41'],
  ['campaignsApi.create', [{ project_id: 5, name: 'C' }], 'post', '/campaigns'],
  ['campaignsApi.update', [41, { name: 'C2' }], 'patch', '/campaigns/41'],
  ['campaignsApi.delete', [41], 'delete', '/campaigns/41'],
  ['campaignsApi.addItem', [41, 12], 'post', '/campaigns/41/items?test_case_id=12'],
  ['campaignsApi.updateItem', [41, 51, { comment: 'c' }], 'patch', '/campaigns/41/items/51'],
  ['campaignsApi.removeItem', [41, 51], 'delete', '/campaigns/41/items/51'],
  ['campaignsApi.scopeLinks', [41], 'get', '/campaigns/41/scope-links'],
  ['campaignsApi.listConfigurations', [5], 'get', '/campaigns/configurations?project_id=5'],
  [
    'campaignsApi.createConfiguration',
    [{ project_id: 5, name: 'Cfg' }],
    'post',
    '/campaigns/configurations',
  ],

  ['testSuitesApi.list', [5], 'get', '/test-suites'],
  ['testSuitesApi.get', [61], 'get', '/test-suites/61'],
  ['testSuitesApi.create', [{ project_id: 5, name: 'S' }], 'post', '/test-suites'],
  ['testSuitesApi.update', [61, { name: 'S2' }], 'patch', '/test-suites/61'],
  ['testSuitesApi.delete', [61], 'delete', '/test-suites/61'],
  ['testSuitesApi.addItem', [61, 12], 'post', '/test-suites/61/items?test_case_id=12'],
  ['testSuitesApi.removeItem', [61, 71], 'delete', '/test-suites/61/items/71'],

  ['linksApi.list', [{ project_id: 5 }], 'get', '/links'],
  [
    'linksApi.create',
    [{ project_id: 5, source_type: 'TC', source_id: 12, target_type: 'REQ', target_id: 11, role: 'verifies' }],
    'post',
    '/links',
  ],
  ['linksApi.delete', [81], 'delete', '/links/81'],

  ['designsApi.list', [5], 'get', '/designs'],
  ['designsApi.get', [91], 'get', '/designs/91'],
  ['designsApi.create', [{ project_id: 5, title: 'D' }], 'post', '/designs'],
  ['designsApi.update', [91, { title: 'D2' }], 'patch', '/designs/91'],
  ['designsApi.delete', [91], 'delete', '/designs/91'],

  ['risksApi.list', [5], 'get', '/risks'],
  ['risksApi.get', [101], 'get', '/risks/101'],
  ['risksApi.create', [{ project_id: 5, title: 'R' }], 'post', '/risks'],
  ['risksApi.update', [101, { title: 'R2' }], 'patch', '/risks/101'],
  ['risksApi.delete', [101], 'delete', '/risks/101'],

  ['changesApi.list', [5], 'get', '/changes'],
  ['changesApi.get', [111], 'get', '/changes/111'],
  ['changesApi.create', [{ project_id: 5, title: 'C' }], 'post', '/changes'],
  ['changesApi.update', [111, { title: 'C2' }], 'patch', '/changes/111'],
  ['changesApi.delete', [111], 'delete', '/changes/111'],

  ['defectsApi.list', [5], 'get', '/defects'],
  ['defectsApi.get', [121], 'get', '/defects/121'],
  ['defectsApi.create', [{ project_id: 5, title: 'D' }], 'post', '/defects'],
  ['defectsApi.update', [121, { title: 'D2' }], 'patch', '/defects/121'],
  ['defectsApi.delete', [121], 'delete', '/defects/121'],

  ['integrationsApi.listSettings', [5], 'get', '/integrations/settings'],
  [
    'integrationsApi.createSetting',
    [{ project_id: 5, tracker: 'github' }],
    'post',
    '/integrations/settings',
  ],
  ['integrationsApi.updateSetting', [131, { base_url: 'x' }], 'patch', '/integrations/settings/131'],
  ['integrationsApi.deleteSetting', [131], 'delete', '/integrations/settings/131'],
  ['integrationsApi.listSyncEvents', [121], 'get', '/integrations/sync-events'],
  ['integrationsApi.refreshExternal', [121], 'post', '/defects/121/refresh-external'],

  ['baselinesApi.list', [5], 'get', '/baselines'],
  ['baselinesApi.get', [141], 'get', '/baselines/141'],
  ['baselinesApi.create', [{ project_id: 5, name: 'B' }], 'post', '/baselines'],
  ['baselinesApi.update', [141, { name: 'B2' }], 'patch', '/baselines/141'],
  ['baselinesApi.delete', [141], 'delete', '/baselines/141'],

  ['testConceptsApi.list', [5], 'get', '/test-concepts'],
  ['testConceptsApi.get', [151], 'get', '/test-concepts/151'],
  ['testConceptsApi.create', [{ project_id: 5, name: 'TCO' }], 'post', '/test-concepts'],
  ['testConceptsApi.update', [151, { name: 'TCO2' }], 'patch', '/test-concepts/151'],
  ['testConceptsApi.delete', [151], 'delete', '/test-concepts/151'],

  ['importApi.import', [5, { requirements: [] }], 'post', '/projects/5/import'],
  [
    'importApi.importReqif',
    [5, new File(['<xml/>'], 'spec.reqif')],
    'post',
    '/projects/5/import/reqif',
  ],

  ['exportApi.download', [5, 'requirements'], 'get', '/projects/5/export/requirements'],

  ['notificationsApi.list', [], 'get', '/notifications'],
  ['notificationsApi.unreadCount', [], 'get', '/notifications/unread-count'],
  ['notificationsApi.markRead', [161], 'post', '/notifications/161/read'],
  ['notificationsApi.markAllRead', [], 'post', '/notifications/read-all'],

  ['searchApi.global', ['boot'], 'get', '/search'],

  ['artefactsApi.listComments', ['requirement', 11], 'get', '/artefacts/requirement/11/comments'],
  ['artefactsApi.createComment', ['requirement', 11, 'hi'], 'post', '/artefacts/requirement/11/comments'],
  ['artefactsApi.listActivity', ['requirement', 11], 'get', '/artefacts/requirement/11/activity'],
  ['artefactsApi.getRelated', ['requirement', 11], 'get', '/artefacts/requirement/11/related'],
  ['artefactsApi.transition', ['requirement', 11, 'Approved'], 'post', '/artefacts/requirement/11/transition'],
]

type ApiGroup = Record<string, (...args: unknown[]) => Promise<unknown>>

function resolve(name: string): (...args: unknown[]) => Promise<unknown> {
  const [group, method] = name.split('.')
  const groups = client as unknown as Record<string, ApiGroup>
  return groups[group][method]
}

beforeEach(() => {
  requests.length = 0
  nextResponse = { status: 200, data: BODY, headers: {} }
  localStorage.clear()
})

describe('api client request contract', () => {
  it.each(CALLS)('%s issues the right request', async (name, args, method, url) => {
    // The download helper reaches for browser APIs jsdom does not implement.
    vi.stubGlobal('URL', Object.assign(URL, {
      createObjectURL: () => 'blob:stub',
      revokeObjectURL: () => {},
    }))
    const clickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, 'click')
      .mockImplementation(() => {})

    await resolve(name)(...args)

    expect(requests).toHaveLength(1)
    expect(requests[0].method).toBe(method)
    expect(requests[0].url).toBe(url)
    // A template literal that names the wrong variable fails here rather than
    // in the browser.
    expect(requests[0].url).not.toMatch(/undefined|NaN|\[object Object\]/)

    clickSpy.mockRestore()
    vi.unstubAllGlobals()
  })

  it('covers every exported endpoint', () => {
    const listed = new Set(CALLS.map(([name]) => name))
    const missing: string[] = []
    for (const [groupName, group] of Object.entries(client)) {
      if (!groupName.endsWith('Api') || typeof group !== 'object' || group === null) continue
      for (const [method, value] of Object.entries(group)) {
        if (typeof value !== 'function') continue
        if (!listed.has(`${groupName}.${method}`)) missing.push(`${groupName}.${method}`)
      }
    }
    expect(missing).toEqual([])
  })
})

describe('responses are unwrapped', () => {
  it('returns the body, not the axios envelope', async () => {
    nextResponse = { status: 200, data: { id: 5, name: 'Project' }, headers: {} }
    await expect(client.projectsApi.get(5)).resolves.toEqual({ id: 5, name: 'Project' })
  })

  it('nextDocId returns the identifier itself', async () => {
    nextResponse = { status: 200, data: { next_id: 'VCU-REQ-007' }, headers: {} }
    await expect(client.docsApi.nextDocId('VCU', 'REQ')).resolves.toBe('VCU-REQ-007')
  })

  it('unreadCount returns the count itself', async () => {
    nextResponse = { status: 200, data: { unread: 4 }, headers: {} }
    await expect(client.notificationsApi.unreadCount()).resolves.toBe(4)
  })
})

describe('query parameters', () => {
  it('scopes a requirement list to its project', async () => {
    await client.requirementsApi.list(5, { skip: 10, limit: 20 })
    expect(requests[0].params).toEqual({ project_id: 5, skip: 10, limit: 20 })
  })

  it('builds the document registry filter into the path', async () => {
    await client.docsApi.list('VCU', {
      type: ['requirements', 'test-cases'],
      status: ['Approved', 'Released'],
      q: 'boot',
      priority: 'High',
      reviewer: 'unassigned',
      links: 'suspect',
      createdFrom: '2026-01-01',
      createdTo: '2026-06-30',
      updatedFrom: '2026-02-01',
      updatedTo: '2026-07-31',
      sort: 'doc_id',
      dir: 'asc',
      relatedTo: 'VCU-REQ-001',
      role: 'verifies',
      direction: 'incoming',
      includeLinkCounts: true,
      skip: 0,
      limit: 50,
    })
    const url = requests[0].url
    expect(url).toContain('type=requirements&type=test-cases')
    // Every filter the registry offers has to reach the server, or the screen
    // silently shows an unfiltered page of a filtered set.
    expect(url).toContain('status=Approved&status=Released')
    expect(url).toContain('q=boot')
    expect(url).toContain('priority=High')
    expect(url).toContain('reviewer=unassigned')
    expect(url).toContain('links=suspect')
    expect(url).toContain('created_from=2026-01-01')
    expect(url).toContain('created_to=2026-06-30')
    expect(url).toContain('updated_from=2026-02-01')
    expect(url).toContain('updated_to=2026-07-31')
    expect(url).toContain('sort=doc_id')
    expect(url).toContain('dir=asc')
    expect(url).toContain('related_to=VCU-REQ-001')
    expect(url).toContain('role=verifies')
    expect(url).toContain('direction=incoming')
    expect(url).toContain('include_link_counts=true')
    expect(url).toContain('skip=0')
    expect(url).toContain('limit=50')
  })

  it('asks for the type summary rather than every document', async () => {
    nextResponse = { status: 200, data: { types: [], total: 0 }, headers: {} }
    await client.docsApi.typeSummary('VCU')
    expect(requests[0].url).toBe('/projects/VCU/doc-type-summary')
  })

  it('omits the registry query string when there is nothing to filter', async () => {
    await client.docsApi.list('VCU')
    expect(requests[0].url).toBe('/projects/VCU/docs')
  })

  it('carries traceability filters', async () => {
    await client.traceabilityApi.getMatrix(5, {
      coverage_filter: 'Uncovered',
      priority_filter: 'High',
      sort_by: 'req_id',
    })
    expect(requests[0].url).toBe(
      '/traceability?project_id=5&coverage_filter=Uncovered&priority_filter=High&sort_by=req_id',
    )
  })

  it('adds impact depth only when asked', async () => {
    await client.traceabilityApi.getImpactAnalysis(11, 3)
    expect(requests[0].url).toBe('/traceability/impact/11?depth=3')
  })

  it('filters campaigns by status', async () => {
    await client.campaignsApi.list(5, 'Running', { skip: 5, limit: 10 })
    expect(requests[0].url).toBe('/campaigns?project_id=5&status=Running&skip=5&limit=10')
  })

  it('asks for unread notifications only when requested', async () => {
    await client.notificationsApi.list({ unreadOnly: true, limit: 5 })
    expect(requests[0].params).toEqual({ unread_only: true, limit: 5 })
    requests.length = 0
    await client.notificationsApi.list()
    expect(requests[0].params).toEqual({})
  })

  it('scopes a search to a project', async () => {
    await client.searchApi.global('boot', { projectId: 5, limit: 10 })
    expect(requests[0].params).toEqual({ q: 'boot', project_id: 5, limit: 10 })
  })

  it('sends the reviewer and approver as the fields the backend expects', async () => {
    await client.requirementsApi.setReviewed(11, 3)
    const reviewed = JSON.parse(requests[0].data as string)
    expect(reviewed.reviewed_by_id).toBe(3)
    expect(Date.parse(reviewed.reviewed_at)).not.toBeNaN()

    requests.length = 0
    await client.testCasesApi.setApproved(12, 4)
    const approved = JSON.parse(requests[0].data as string)
    expect(approved.approved_by_id).toBe(4)
    expect(Date.parse(approved.approved_at)).not.toBeNaN()
  })
})

describe('resolving a document kind', () => {
  it('accepts a type code and converts it to the registry slug', async () => {
    await client.docsApi.get('VCU', 'TC', 'VCU-TC-001')
    expect(requests[0].url).toBe('/projects/VCU/docs/test-cases/VCU-TC-001')
  })

  it('passes an already-slugged kind through unchanged', async () => {
    await client.docsApi.get('VCU', 'test-cases', 'VCU-TC-001')
    expect(requests[0].url).toBe('/projects/VCU/docs/test-cases/VCU-TC-001')
  })
})
