/**
 * Canned API responses in the shapes the backend really returns.
 *
 * Page tests mount a route and let its queries resolve against these, so what
 * is asserted is the page rendering real-shaped data rather than a spinner. The
 * shapes are the exported interfaces in `api/client.ts`; a page that reads a
 * field nothing here supplies fails loudly instead of silently rendering blank.
 */

const NOW = '2026-03-01T10:00:00Z'

function timestamps() {
  return { created_at: NOW, updated_at: NOW }
}

export const project = {
  id: 1,
  name: 'Vehicle Control Unit',
  prefix: 'VCU',
  description: 'The primary controller',
  status: 'Active',
  requirement_count: 3,
  test_case_count: 2,
  campaign_count: 1,
  design_count: 1,
  risk_count: 1,
  change_count: 1,
  test_concept_count: 1,
  test_suite_count: 1,
  defect_count: 1,
  coverage_percent: 33.3,
  uncovered_requirement_count: 2,
  ...timestamps(),
}

export const user = {
  id: 1,
  email: 'ada@example.com',
  full_name: 'Ada Lovelace',
  role: 'admin' as const,
  is_active: true,
  pending_email: null,
  email_change_status: null,
  email_change_requested_at: null,
  ...timestamps(),
}

export const requirement = {
  id: 11,
  project_id: 1,
  req_id: 'VCU-REQ-001',
  title: 'The system shall boot within 2 seconds',
  description: 'Cold start to ready state.',
  content_json: null,
  content_html: null,
  status: 'Approved',
  visibility: 'internal' as const,
  priority: 'High',
  req_type: 'Functional',
  req_origin: 'Customer',
  parent_id: null,
  // A reviewer and approver are named but neither has signed off yet, which is
  // what makes the "mark reviewed" and "mark approved" actions available.
  reviewer_id: 1,
  approver_id: 1,
  reviewed_by_id: null,
  reviewed_at: null,
  approved_by_id: null,
  approved_at: null,
  ...timestamps(),
}

export const testCase = {
  id: 21,
  project_id: 1,
  tc_id: 'VCU-TC-001',
  title: 'Cold boot timing',
  description: 'Measure time to ready.',
  content_json: null,
  content_html: null,
  preconditions: 'Battery connected',
  // The step table is the test case; these are the rows the detail page shows.
  steps: [
    {
      id: 'row-1',
      row_type: 'step',
      label: 'Step',
      description: 'Power on the controller',
      expected_result: 'It reaches ready within 2s',
      indent_level: 0,
      collapsed: false,
    },
  ],
  expected_results: 'Ready within 2s',
  status: 'Approved',
  visibility: 'internal' as const,
  priority: 'High',
  test_type: 'Functional',
  automation_status: 'Manual',
  // Named but not yet signed off, so both actions are available.
  reviewer_id: 1,
  approver_id: 1,
  reviewed_by_id: null,
  reviewed_at: null,
  approved_by_id: null,
  approved_at: null,
  ...timestamps(),
}

export const docShell = {
  id: 11,
  doc_id: 'VCU-REQ-001',
  doc_type: 'REQ',
  title: 'The system shall boot within 2 seconds',
  status: 'Approved',
  visibility: 'internal' as const,
  priority: 'High',
  req_type: 'Functional',
  req_origin: 'Customer',
  project_id: 1,
  reviewer_id: null,
  incoming_links: 1,
  outgoing_links: 2,
  suspect_links: 0,
  last_execution_status: 'Passed',
  last_executed_at: NOW,
  last_bud_run_id: 77,
  ...timestamps(),
}

/** A test case shell, so the registry renders its execution column too. */
export const testCaseDocShell = {
  ...docShell,
  id: 21,
  doc_id: 'VCU-TC-001',
  doc_type: 'TC',
  title: 'Cold boot timing',
  req_type: null,
  req_origin: null,
}

export const docDetail = {
  ...docShell,
  description: 'Cold start to ready state.',
  content_json: null,
  content_html: '<p>Cold start to ready state.</p>',
}

/**
 * Shaped from `TestCampaign` in the API client. The count fields are
 * `total_items` / `passed` / `failed`, not the `item_count` / `passed_count`
 * an earlier version of this fixture invented - a campaign card reads
 * `total_items` to decide whether it has a scope at all, so the wrong names
 * made every card claim it was empty.
 */
export const campaign = {
  id: 31,
  project_id: 1,
  campaign_id: 'VCU-CMP-001',
  name: 'Release candidate sweep',
  description: 'Full regression before release.',
  // One of Planned | Scope | In Progress | Completed | Aborted, which is what
  // the app and the dashboard both count by; "Running" was not among them.
  status: 'In Progress',
  visibility: 'internal' as const,
  configuration_id: null,
  suite_id: null,
  bud_run_id: 77,
  bud_run_url: 'https://bud.example.com/runs/77',
  bud_run_status: 'Completed',
  started_at: null,
  completed_at: null,
  total_items: 1,
  passed: 1,
  failed: 0,
  blocked: 0,
  pending: 0,
  last_execution_status: 'Passed',
  last_executed_at: NOW,
  configuration: null,
  suite: null,
  suites: [] as { id: number; suite_id: string; name: string; status: string }[],
  ...timestamps(),
}

/** One scoped test case, as a campaign carries it. */
export const campaignItem = {
  id: 61,
  campaign_id: campaign.id,
  test_case_id: 21,
  status: 'Executed',
  result: 'Passed',
  comment: null,
  executed_at: NOW,
  created_at: NOW,
  test_case: null as { tc_id: string; title: string } | null,
}

/**
 * `TestCampaignDetail`, which is what `campaignsApi.get` returns - the list
 * shape plus the scopes that make up the whole body of the detail page. An
 * earlier version of this fixture omitted them, so the Suites section never
 * rendered under test at all.
 */
export const campaignDetail = {
  ...campaign,
  items: [campaignItem],
  configuration: null,
  suite_scopes: [] as { suite: Record<string, unknown>; items: (typeof campaignItem)[] }[],
  ad_hoc_items: [] as (typeof campaignItem)[],
  related_requirements: [] as unknown[],
  related_concepts: [] as unknown[],
}

export const testSuite = {
  // The campaign form counts a suite's test cases before it will scope one.
  total_items: 1,
  id: 41,
  project_id: 1,
  suite_id: 'VCU-TS-001',
  name: 'Smoke suite',
  description: 'Runs on every build.',
  status: 'Active',
  visibility: 'internal' as const,
  item_count: 1,
  ...timestamps(),
}

export const defect = {
  id: 51,
  project_id: 1,
  defect_id: 'VCU-DEF-001',
  title: 'Screen flickers on wake',
  description: 'Observed on cold mornings.',
  severity: 'High',
  status: 'Open',
  visibility: 'internal' as const,
  resolution_summary: null,
  external_tracker: null,
  external_issue_key: null,
  external_issue_url: null,
  external_status: null,
  external_synced_at: null,
  reported_by_id: 1,
  assigned_to_id: null,
  ...timestamps(),
}

export const design = {
  id: 61,
  project_id: 1,
  design_id: 'VCU-DES-001',
  title: 'Boot sequence',
  description: 'How the controller starts.',
  content_json: null,
  content_html: null,
  status: 'Approved',
  visibility: 'internal' as const,
  priority: 'Medium',
  design_type: 'Architecture',
  linked_requirement_id: null,
  ...timestamps(),
}

export const risk = {
  id: 71,
  project_id: 1,
  risk_id: 'VCU-RSK-001',
  title: 'Brown-out during boot',
  description: 'Low battery may interrupt startup.',
  content_json: null,
  content_html: null,
  status: 'Open',
  visibility: 'internal' as const,
  severity: 'High',
  probability: 'Medium',
  mitigation: 'Add a supply capacitor.',
  ...timestamps(),
}

export const change = {
  id: 81,
  project_id: 1,
  change_id: 'VCU-CHG-001',
  title: 'Raise the boot budget to 3s',
  description: 'Hardware revision is slower.',
  content_json: null,
  content_html: null,
  status: 'Under Review',
  visibility: 'internal' as const,
  priority: 'Medium',
  external_tracker: null,
  external_issue_key: null,
  external_issue_url: null,
  external_status: null,
  external_synced_at: null,
  ...timestamps(),
}

export const testConcept = {
  id: 91,
  project_id: 1,
  concept_id: 'VCU-CPT-001',
  name: 'Environmental testing concept',
  description: 'How we verify temperature range.',
  content_json: null,
  content_html: null,
  status: 'Approved',
  visibility: 'internal' as const,
  ...timestamps(),
}

export const baseline = {
  id: 101,
  project_id: 1,
  name: 'Release 1.0',
  description: 'Frozen for release.',
  status: 'Frozen',
  baseline_type: 'Release',
  snapshot: null,
  ...timestamps(),
}

export const projectMember = {
  id: 111,
  user_id: 2,
  email: 'external@example.com',
  full_name: 'Ext Ernal',
  role: 'external' as const,
  doc_types: ['REQ'],
  ...timestamps(),
}

export const projectVariable = {
  id: 121,
  project_id: 1,
  kind: 'parameter' as const,
  key: 'BOOT_BUDGET_MS',
  value: '2000',
  description: 'Time to ready',
  ...timestamps(),
}

export const link = {
  id: 131,
  project_id: 1,
  source_type: 'TC',
  source_id: 21,
  target_type: 'REQ',
  target_id: 11,
  role: 'verifies',
  created_at: NOW,
}

export const integrationSetting = {
  id: 141,
  project_id: 1,
  tracker: 'github',
  base_url: 'https://github.com/embedlabs/vcu',
  // The API reports only whether a credential exists; the secret itself is
  // encrypted at rest and never returned.
  has_token: true,
  has_webhook_secret: true,
  enabled: true,
  ...timestamps(),
}

export const serviceCredential = {
  id: 151,
  name: 'Bud result sync',
  token_prefix: 'blm_sync_abcd',
  scope: 'test-results:write' as const,
  expires_at: '2026-06-01T10:00:00Z',
  revoked_at: null,
  last_used_at: null,
  created_at: NOW,
}

export const attachment = {
  id: 155,
  document_id: 11,
  original_filename: 'verification-report.pdf',
  content_type: 'application/pdf',
  size_bytes: 1536,
  sha256: 'a'.repeat(64),
  source_ref: 'Bud run 77',
  uploaded_by_id: user.id,
  created_at: NOW,
}

export const notification = {
  id: 161,
  event_type: 'defect.created',
  title: 'A defect was raised',
  body: 'VCU-DEF-001',
  link_path: '/projects/VCU/defects/51',
  project_id: 1,
  read_at: null,
  created_at: NOW,
}

export const dashboardStats = {
  total_projects: 1,
  active_projects: 1,
  total_requirements: 3,
  total_test_cases: 2,
  total_campaigns: 1,
  active_campaigns: 1,
  coverage_percent: 33.3,
  uncovered_requirements: 2,
  requirement_status_distribution: { Draft: 1, Approved: 2 },
  test_case_status_distribution: { Draft: 1, Approved: 1 },
  campaign_result_distribution: { Passed: 1 },
  total_defects: 1,
  open_defects: 1,
  defect_severity_distribution: { High: 1 },
  defect_status_distribution: { Open: 1 },
  projects: [
    {
      id: 1,
      name: project.name,
      prefix: project.prefix,
      status: 'Active',
      requirement_count: 3,
      test_case_count: 2,
      campaign_count: 1,
      document_count: 4,
      coverage_percent: 33.3,
      uncovered_requirement_count: 2,
    },
  ],
}

export const coverageGaps = {
  project_id: 1,
  total_requirements: 3,
  covered: 1,
  partial: 1,
  uncovered: 1,
  coverage_percent: 33.3,
  gaps: [{ requirement, gap_type: 'no_test_cases' }],
}

export const traceabilityItem = {
  requirement,
  linked_test_cases: [testCase],
  linked_test_runs: [],
  coverage_status: 'Covered',
}

export const impactAnalysis = {
  root_requirement: requirement,
  upstream: [],
  downstream: [],
}

export const artefactRelated = {
  incoming: [],
  outgoing: [],
}

export const artefactComment = {
  id: 171,
  artefact_type: 'defect',
  artefact_id: 51,
  author_name: 'Ada Lovelace',
  body: 'Looks right to me.',
  created_at: NOW,
}

export const artefactActivity = {
  id: 181,
  artefact_type: 'defect',
  artefact_id: 51,
  event_type: 'status_changed',
  summary: 'Ada Lovelace moved this from Draft to Approved',
  created_at: NOW,
}

function page<T>(item: T) {
  return { items: [item], total: 1, skip: 0, limit: 50 }
}

/** `group.method -> response`, matching the client's declared return types. */
export const RESPONSES: Record<string, unknown> = {
  'authApi.getMe': user,
  'authApi.login': { access_token: 'tok', token_type: 'bearer', user },
  'authApi.refresh': { access_token: 'tok', token_type: 'bearer', user },
  'authApi.logout': undefined,
  'authApi.updateMe': user,
  'authApi.requestEmailChange': { message: 'ok' },
  'authApi.cancelEmailChange': { message: 'ok' },
  'authApi.confirmEmailChange': { message: 'ok' },
  'authApi.changePassword': user,
  'authApi.getInviteInfo': {
    email: user.email,
    full_name: user.full_name,
    valid: true,
    expired: false,
  },
  'authApi.acceptInvite': {
    requires_email_verification: false,
    email: user.email,
    message: 'Your account is ready.',
  },
  'authApi.verifyEmail': { message: 'ok' },
  'authApi.forgotPassword': { message: 'ok' },
  'authApi.resetPassword': { message: 'ok' },

  'serviceCredentialsApi.list': [serviceCredential],
  'serviceCredentialsApi.create': { ...serviceCredential, token: 'blm_sync_secret' },
  'serviceCredentialsApi.rotate': { ...serviceCredential, token: 'blm_sync_rotated' },
  'serviceCredentialsApi.revoke': undefined,

  'attachmentsApi.list': [attachment],
  'attachmentsApi.upload': attachment,
  'attachmentsApi.download': {
    blob: new Blob(['report'], { type: 'application/pdf' }),
    filename: attachment.original_filename,
  },
  'attachmentsApi.remove': undefined,

  'usersApi.list': [user],
  'usersApi.get': user,
  'usersApi.create': user,
  'usersApi.invite': { message: 'Invitation sent', user, invite_link: null },
  'usersApi.update': user,
  'usersApi.startEmailChange': user,
  'usersApi.approveEmailChange': user,
  'usersApi.rejectEmailChange': user,
  'usersApi.delete': undefined,

  'dashboardApi.getStats': dashboardStats,

  'projectsApi.list': [project],
  'projectsApi.get': project,
  'projectsApi.getByPrefix': project,
  'projectsApi.create': project,
  'projectsApi.update': project,
  'projectsApi.delete': undefined,

  'projectMembersApi.list': [projectMember],
  'projectMembersApi.create': projectMember,
  'projectMembersApi.update': projectMember,
  'projectMembersApi.remove': undefined,

  'docsApi.nextDocId': 'VCU-REQ-004',
  'docsApi.list': { items: [docShell, testCaseDocShell], total: 2, skip: 0, limit: 50 },
  // The per-type tally the topology and the project screen read. It agrees with
  // `docsApi.list` above: one REQ and one TC, neither carrying a suspect link.
  'docsApi.typeSummary': {
    types: [
      { doc_type: 'REQ', count: 1, suspect_links: 0 },
      { doc_type: 'TC', count: 1, suspect_links: 0 },
    ],
    total: 2,
  },
  'docsApi.get': docDetail,

  'requirementsApi.list': page(requirement),
  'requirementsApi.get': requirement,
  'requirementsApi.create': requirement,
  'requirementsApi.update': requirement,
  'requirementsApi.setReviewed': requirement,
  'requirementsApi.setApproved': requirement,
  'requirementsApi.delete': undefined,
  'requirementsApi.linkTestRun': undefined,
  'requirementsApi.getTestRuns': [],

  'testCasesApi.list': page(testCase),
  'testCasesApi.get': testCase,
  'testCasesApi.create': testCase,
  'testCasesApi.update': testCase,
  'testCasesApi.setReviewed': testCase,
  'testCasesApi.setApproved': testCase,
  'testCasesApi.delete': undefined,

  'traceabilityApi.getMatrix': [traceabilityItem],
  'traceabilityApi.getImpactAnalysis': impactAnalysis,
  'traceabilityApi.getCoverageGaps': coverageGaps,

  'documentsApi.list': page({ ...docShell, doc_type: 'RPT', section_count: 0, version: '1.0', description: null }),
  'documentsApi.get': { ...docDetail, version: '1.0', sections: [] },
  'documentsApi.create': { ...docDetail, version: '1.0', section_count: 0 },
  'documentsApi.update': { ...docDetail, version: '1.0', section_count: 0 },
  'documentsApi.delete': undefined,
  'documentsApi.addSection': { id: 1, document_id: 1, parent_section_id: null, order: 1, title: 'S', content: null, section_type: 'text', child_sections: [], created_at: NOW, updated_at: NOW },
  'documentsApi.updateSection': { id: 1, document_id: 1, parent_section_id: null, order: 1, title: 'S', content: null, section_type: 'text', child_sections: [], created_at: NOW, updated_at: NOW },
  'documentsApi.deleteSection': undefined,
  'documentsApi.reorderSections': undefined,

  'projectVariablesApi.list': [projectVariable],
  'projectVariablesApi.create': projectVariable,
  'projectVariablesApi.update': projectVariable,
  'projectVariablesApi.delete': undefined,

  'campaignsApi.list': page(campaign),
  'campaignsApi.get': campaignDetail,
  'campaignsApi.create': campaignDetail,
  'campaignsApi.update': campaign,
  'campaignsApi.delete': undefined,
  'campaignsApi.addItem': { id: 1, campaign_id: 31, test_case_id: 21, status: 'Not Run', comment: null },
  'campaignsApi.updateItem': { id: 1, campaign_id: 31, test_case_id: 21, status: 'Not Run', comment: null },
  'campaignsApi.removeItem': undefined,
  'campaignsApi.scopeLinks': [link],
  'campaignsApi.listConfigurations': [],
  'campaignsApi.createConfiguration': { id: 1, project_id: 1, name: 'Default', description: null, environment: null, parameters: {} },

  'testSuitesApi.list': page(testSuite),
  'testSuitesApi.get': { ...testSuite, items: [] },
  'testSuitesApi.create': testSuite,
  'testSuitesApi.update': testSuite,
  'testSuitesApi.delete': undefined,
  'testSuitesApi.addItem': { id: 1, suite_id: 41, test_case_id: 21, order: 1 },
  'testSuitesApi.removeItem': undefined,

  'linksApi.list': [link],
  'linksApi.create': link,
  'linksApi.delete': undefined,

  'designsApi.list': page(design),
  'designsApi.get': design,
  'designsApi.create': design,
  'designsApi.update': design,
  'designsApi.delete': undefined,

  'risksApi.list': page(risk),
  'risksApi.get': risk,
  'risksApi.create': risk,
  'risksApi.update': risk,
  'risksApi.delete': undefined,

  'changesApi.list': page(change),
  'changesApi.get': change,
  'changesApi.create': change,
  'changesApi.update': change,
  'changesApi.delete': undefined,

  'defectsApi.list': page(defect),
  'defectsApi.get': defect,
  'defectsApi.create': defect,
  'defectsApi.update': defect,
  'defectsApi.delete': undefined,

  'integrationsApi.listSettings': [integrationSetting],
  'integrationsApi.createSetting': integrationSetting,
  'integrationsApi.updateSetting': integrationSetting,
  'integrationsApi.deleteSetting': undefined,
  'integrationsApi.listSyncEvents': [],
  'integrationsApi.refreshExternal': defect,

  'baselinesApi.list': [baseline],
  'baselinesApi.get': baseline,
  'baselinesApi.create': baseline,
  'baselinesApi.update': baseline,
  'baselinesApi.delete': undefined,

  'testConceptsApi.list': page(testConcept),
  'testConceptsApi.get': testConcept,
  'testConceptsApi.create': testConcept,
  'testConceptsApi.update': testConcept,
  'testConceptsApi.delete': undefined,

  'importApi.import': { imported: 1, skipped: 0, new_ids: ['VCU-REQ-004'], errors: [] },
  'importApi.importReqif': {
    imported: 1,
    skipped: 0,
    links_created: 1,
    specifications: 1,
    new_ids: ['VCU-REQ-004'],
    errors: [],
  },

  'exportApi.download': undefined,

  'notificationsApi.list': { items: [notification], total: 1, unread: 1 },
  'notificationsApi.unreadCount': 1,
  'notificationsApi.markRead': { ...notification, read_at: NOW },
  'notificationsApi.markAllRead': undefined,

  'searchApi.global': { query: 'boot', total: 1, items: [] },

  'artefactsApi.listComments': [artefactComment],
  'artefactsApi.createComment': artefactComment,
  'artefactsApi.listActivity': [artefactActivity],
  'artefactsApi.getRelated': artefactRelated,
  'artefactsApi.transition': { status: 'Approved', allowed_transitions: ['Draft'] },
}

/**
 * Build a mocked `api/client` whose endpoints answer from `RESPONSES`.
 *
 * Pass this to `vi.mock('../api/client', ...)`; the returned module keeps every
 * non-endpoint export as it is and replaces each endpoint with a `vi.fn`.
 */
export function mockApiModule(
  actual: Record<string, unknown>,
  // Vitest's own `vi`; typed loosely so this helper does not depend on its
  // internal generics.
  vi: { fn: (impl: (...args: never[]) => unknown) => unknown },
): Record<string, unknown> {
  const mocked: Record<string, unknown> = { ...actual }
  for (const [groupName, group] of Object.entries(actual)) {
    if (!groupName.endsWith('Api') || typeof group !== 'object' || group === null) continue
    const replacement: Record<string, unknown> = {}
    for (const [method, value] of Object.entries(group)) {
      if (typeof value !== 'function') {
        replacement[method] = value
        continue
      }
      replacement[method] = vi.fn(defaultImplementation(`${groupName}.${method}`))
    }
    mocked[groupName] = replacement
  }
  return mocked
}

function defaultImplementation(key: string) {
  return async () => {
    if (!(key in RESPONSES)) throw new Error(`no fixture for ${key}`)
    return RESPONSES[key]
  }
}

/**
 * Put every endpoint back to answering from `RESPONSES`.
 *
 * `vi.clearAllMocks()` forgets the calls but keeps any implementation a test
 * installed with `mockResolvedValue`, so one test overriding an endpoint
 * silently changed it for every test after it. Call this in `beforeEach`.
 */
export function resetApiMocks(
  client: Record<string, unknown>,
  vi: { mocked: (fn: never) => { mockImplementation: (impl: never) => void } },
): void {
  for (const [groupName, group] of Object.entries(client)) {
    if (!groupName.endsWith('Api') || typeof group !== 'object' || group === null) continue
    for (const [method, value] of Object.entries(group as Record<string, unknown>)) {
      if (typeof value !== 'function' || !('mock' in (value as object))) continue
      vi.mocked(value as never).mockImplementation(
        defaultImplementation(`${groupName}.${method}`) as never,
      )
    }
  }
}
