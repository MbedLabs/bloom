export type DocType = 'REQ' | 'SPEC' | 'TC' | 'DES' | 'RSK' | 'CHG' | 'CPT' | 'DEF' | 'CMP' | 'TS' | 'PRT' | 'RPT' | 'STD'
export type DocLinkRole =
  | 'derives_from'
  | 'refines'
  | 'satisfies'
  | 'implements'
  | 'verifies'
  | 'mitigates'
  | 'depends_on'
  | 'impacts'
  | 'blocks'
  | 'duplicates'
  | 'references'
  | 'relates_to'
  | 'covers'
  | 'contains'
export interface DocLinkOption {
  key: string
  label: string
  role: DocLinkRole
  sourceType: DocType
  targetType: DocType
  displayDirection: 'incoming' | 'outgoing'
}

export interface DocShell {
  id: number
  doc_id: string
  doc_type: DocType
  project_id: number
  title: string
  description: string | null
  content_json: Record<string, unknown> | null
  content_html: string | null
  status: string
  priority: string | null
  assigned_to: number | null
  reviewer_id: number | null
  source_ref: string | null
  source_project_id: number | null
  created_at: string
  updated_at: string
}

export interface DocConfig {
  label: string
  typeCode: string
  apiBase: string
  idField: string
  titleField: string
  descriptionField: string
  statusOptions: string[]
  priorityOptions?: string[]
  fields: DocFieldConfig[]
}

export interface DocFieldConfig {
  key: string
  label: string
  type: 'text' | 'textarea' | 'select' | 'number' | 'user'
  options?: string[]
  required?: boolean
  multiline?: boolean
}

export const DOC_CONFIGS: Record<DocType, DocConfig> = {
  REQ: {
    label: 'Requirement',
    typeCode: 'REQ',
    apiBase: 'requirements',
    idField: 'req_id',
    titleField: 'title',
    descriptionField: 'description',
    statusOptions: ['Draft', 'Review', 'Approved', 'Rejected', 'Obsolete'],
    priorityOptions: ['Low', 'Medium', 'High', 'Critical'],
    fields: [
      { key: 'title', label: 'Title', type: 'text', required: true },
      { key: 'description', label: 'Description', type: 'textarea' },
      { key: 'priority', label: 'Priority', type: 'select', options: ['Low', 'Medium', 'High', 'Critical'] },
       { key: 'req_type', label: 'Type', type: 'select', options: ['Functional', 'Non-functional', 'Safety', 'Security', 'Performance', 'Usability', 'Compliance'] },
       { key: 'req_origin', label: 'Origin', type: 'select', options: ['Internal', 'Customer', 'Compliance'] },
    ],
  },
  TC: {
    label: 'Test Case',
    typeCode: 'TC',
    apiBase: 'test-cases',
    idField: 'tc_id',
    titleField: 'title',
    descriptionField: 'description',
    statusOptions: ['Draft', 'Review', 'Approved', 'Rejected', 'Obsolete'],
    fields: [
      { key: 'title', label: 'Title', type: 'text', required: true },
      { key: 'description', label: 'Description', type: 'textarea' },
      { key: 'preconditions', label: 'Preconditions', type: 'textarea' },
    ],
  },
  DES: {
    label: 'Design',
    typeCode: 'DES',
    apiBase: 'designs',
    idField: 'design_id',
    titleField: 'title',
    descriptionField: 'description',
    statusOptions: ['Draft', 'Review', 'Approved'],
    priorityOptions: ['Low', 'Medium', 'High', 'Critical'],
    fields: [
      { key: 'title', label: 'Title', type: 'text', required: true },
      { key: 'description', label: 'Description', type: 'textarea' },
      { key: 'priority', label: 'Priority', type: 'select', options: ['Low', 'Medium', 'High', 'Critical'] },
       { key: 'design_type', label: 'Design Type', type: 'select', options: ['Architecture', 'Interface', 'Component', 'Data', 'Mechanical', 'Electrical', 'Firmware', 'Manufacturing', 'Verification Support'] },
    ],
  },
  RSK: {
    label: 'Risk',
    typeCode: 'RSK',
    apiBase: 'risks',
    idField: 'risk_id',
    titleField: 'title',
    descriptionField: 'description',
    statusOptions: ['Open', 'Mitigated', 'Accepted', 'Closed'],
    fields: [
      { key: 'title', label: 'Title', type: 'text', required: true },
      { key: 'description', label: 'Description', type: 'textarea' },
      { key: 'severity', label: 'Severity', type: 'select', options: ['Low', 'Medium', 'High', 'Critical'] },
      { key: 'probability', label: 'Probability', type: 'select', options: ['Low', 'Medium', 'High'] },
      { key: 'mitigation', label: 'Mitigation', type: 'textarea' },
       { key: 'risk_category', label: 'Category', type: 'select', options: ['Technical', 'Schedule', 'Cost', 'Quality', 'Resource', 'Safety', 'Security'] },
    ],
  },
  CHG: {
    label: 'Change Request',
    typeCode: 'CHG',
    apiBase: 'changes',
    idField: 'change_id',
    titleField: 'title',
    descriptionField: 'description',
    statusOptions: ['Submitted', 'Under Review', 'Approved', 'Rejected', 'Implemented'],
    priorityOptions: ['Low', 'Medium', 'High', 'Critical'],
    fields: [
      { key: 'title', label: 'Title', type: 'text', required: true },
      { key: 'description', label: 'Description', type: 'textarea' },
      { key: 'priority', label: 'Priority', type: 'select', options: ['Low', 'Medium', 'High', 'Critical'] },
       { key: 'change_type', label: 'Change Type', type: 'select', options: ['Enhancement', 'Bug Fix', 'Refactoring', 'New Feature', 'Compliance', 'Safety'] },
      { key: 'impact_assessment', label: 'Impact Assessment', type: 'textarea' },
      { key: 'justification', label: 'Justification', type: 'textarea' },
    ],
  },
  CPT: {
    label: 'Test Concept',
    typeCode: 'CPT',
    apiBase: 'test-concepts',
    idField: 'concept_id',
    titleField: 'name',
    descriptionField: 'description',
    statusOptions: ['Draft', 'Review', 'Approved'],
    fields: [
      { key: 'name', label: 'Name', type: 'text', required: true },
      { key: 'description', label: 'Description', type: 'textarea' },
      { key: 'coverage', label: 'Coverage %', type: 'number' },
    ],
  },
  DEF: {
    label: 'Defect',
    typeCode: 'DEF',
    apiBase: 'defects',
    idField: 'defect_id',
    titleField: 'title',
    descriptionField: 'description',
    statusOptions: ['Open', 'Triaged', 'In Progress', 'Resolved', 'Verified', 'Closed', 'Rejected', 'Duplicate'],
    priorityOptions: ['Low', 'Medium', 'High', 'Critical'],
    fields: [
      { key: 'title', label: 'Title', type: 'text', required: true },
      { key: 'description', label: 'Description', type: 'textarea' },
      { key: 'severity', label: 'Severity', type: 'select', options: ['Low', 'Medium', 'High', 'Critical'] },
      { key: 'priority', label: 'Priority', type: 'select', options: ['Low', 'Medium', 'High', 'Critical'] },
    ],
  },
  CMP: {
    label: 'Campaign',
    typeCode: 'CMP',
    apiBase: 'campaigns',
    idField: 'id',
    titleField: 'name',
    descriptionField: 'description',
    statusOptions: ['Planned', 'Running', 'Completed'],
    fields: [
      { key: 'name', label: 'Name', type: 'text', required: true },
      { key: 'description', label: 'Description', type: 'textarea' },
    ],
  },
  TS: {
    label: 'Test Suite',
    typeCode: 'TS',
    apiBase: 'test-suites',
    idField: 'suite_id',
    titleField: 'name',
    descriptionField: 'description',
    statusOptions: ['Draft', 'Review', 'Approved'],
    fields: [
      { key: 'name', label: 'Name', type: 'text', required: true },
      { key: 'description', label: 'Description', type: 'textarea' },
    ],
  },
  SPEC: {
    label: 'Specification',
    typeCode: 'SPEC',
    apiBase: 'documents',
    idField: 'doc_id',
    titleField: 'title',
    descriptionField: 'description',
    statusOptions: ['Draft', 'Review', 'Approved', 'Rejected', 'Obsolete'],
    priorityOptions: ['Low', 'Medium', 'High', 'Critical'],
    fields: [
      { key: 'title', label: 'Title', type: 'text', required: true },
      { key: 'description', label: 'Description', type: 'textarea' },
      { key: 'priority', label: 'Priority', type: 'select', options: ['Low', 'Medium', 'High', 'Critical'] },
      { key: 'spec_type', label: 'Specification Type', type: 'select', options: ['Product Specification', 'System Specification', 'Subsystem Specification', 'Interface Specification', 'Compliance Specification', 'Customer Specification', 'Supplier Specification'] },
    ],
  },
  PRT: {
    label: 'Protocol',
    typeCode: 'PRT',
    apiBase: 'documents',
    idField: 'doc_id',
    titleField: 'title',
    descriptionField: 'description',
    statusOptions: ['Draft', 'Review', 'Approved', 'Rejected', 'Obsolete'],
    fields: [
      { key: 'title', label: 'Title', type: 'text', required: true },
      { key: 'description', label: 'Description', type: 'textarea' },
      { key: 'protocol_type', label: 'Protocol Type', type: 'select', options: ['Verification Protocol', 'Validation Protocol', 'Compliance Protocol', 'Manufacturing Protocol', 'Service Protocol', 'Operational Protocol'] },
    ],
  },
  RPT: {
    label: 'Report',
    typeCode: 'RPT',
    apiBase: 'documents',
    idField: 'doc_id',
    titleField: 'title',
    descriptionField: 'description',
    statusOptions: ['Draft', 'Final', 'Approved'],
    fields: [
      { key: 'title', label: 'Title', type: 'text', required: true },
      { key: 'description', label: 'Description', type: 'textarea' },
      { key: 'report_type', label: 'Report Type', type: 'select', options: ['Verification Report', 'Validation Report', 'Traceability Report', 'Audit Report', 'Release Report', 'Change Impact Report'] },
    ],
  },
  STD: {
    label: 'External Standard',
    typeCode: 'STD',
    apiBase: 'documents',
    idField: 'doc_id',
    titleField: 'title',
    descriptionField: 'description',
    statusOptions: ['Draft', 'Active', 'Superseded'],
    fields: [
      { key: 'title', label: 'Title', type: 'text', required: true },
      { key: 'description', label: 'Description', type: 'textarea' },
      { key: 'standard_type', label: 'Standard Type', type: 'select', options: ['Customer Standard', 'Regulatory Standard', 'Industry Standard', 'Supplier Standard', 'Internal Standard'] },
    ],
  },
}

export const DOC_TYPE_LABELS: Record<DocType, string> = {
  REQ: 'Requirement',
  SPEC: 'Specification',
  TC: 'Test Case',
  DES: 'Design',
  RSK: 'Risk',
  CHG: 'Change Request',
  CPT: 'Test Concept',
  DEF: 'Defect',
  CMP: 'Campaign',
  TS: 'Test Suite',
  PRT: 'Protocol',
  RPT: 'Report',
  STD: 'External Standard',
}

export const DOC_TYPE_COLORS: Record<DocType, string> = {
  REQ: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
  SPEC: 'bg-indigo-500/10 text-indigo-700 dark:text-indigo-400',
  TC: 'bg-cyan-500/10 text-cyan-700 dark:text-cyan-400',
  DES: 'bg-violet-500/10 text-violet-700 dark:text-violet-400',
  RSK: 'bg-red-500/10 text-red-700 dark:text-red-400',
  CHG: 'bg-blue-500/10 text-blue-700 dark:text-blue-400',
  CPT: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
  DEF: 'bg-rose-500/10 text-rose-700 dark:text-rose-400',
  CMP: 'bg-sky-500/10 text-sky-700 dark:text-sky-400',
  TS: 'bg-lime-500/10 text-lime-700 dark:text-lime-400',
  PRT: 'bg-teal-500/10 text-teal-700 dark:text-teal-400',
  RPT: 'bg-slate-500/10 text-slate-700 dark:text-slate-400',
  STD: 'bg-orange-500/10 text-orange-700 dark:text-orange-400',
}

export const DOC_TYPE_SLUGS: Record<DocType, string> = {
  REQ: 'requirements',
  SPEC: 'specifications',
  TC: 'test-cases',
  DES: 'designs',
  RSK: 'risks',
  CHG: 'changes',
  CPT: 'test-concepts',
  DEF: 'defects',
  CMP: 'campaigns',
  TS: 'test-suites',
  PRT: 'protocols',
  RPT: 'reports',
  STD: 'standards',
}

const DOC_TYPE_CODES = Object.keys(DOC_TYPE_SLUGS) as DocType[]
const SLUG_TO_DOC_TYPE = Object.fromEntries(
  Object.entries(DOC_TYPE_SLUGS).map(([type, slug]) => [slug, type])
) as Record<string, DocType>

type DocLinkRuleRow = {
  sourceType: DocType
  targetType: DocType
  roles: DocLinkRole[]
}

const DOC_LINK_RULE_ROWS: DocLinkRuleRow[] = [
  { sourceType: 'REQ', targetType: 'REQ', roles: ['derives_from', 'refines', 'depends_on', 'duplicates', 'relates_to'] },
  { sourceType: 'REQ', targetType: 'SPEC', roles: ['derives_from', 'refines', 'references'] },
  { sourceType: 'REQ', targetType: 'STD', roles: ['references'] },
  { sourceType: 'REQ', targetType: 'TS', roles: ['references'] },
  { sourceType: 'REQ', targetType: 'CMP', roles: ['references'] },
  { sourceType: 'SPEC', targetType: 'SPEC', roles: ['derives_from', 'refines', 'depends_on', 'duplicates', 'relates_to'] },
  { sourceType: 'SPEC', targetType: 'STD', roles: ['references'] },
  { sourceType: 'STD', targetType: 'STD', roles: ['duplicates', 'relates_to', 'references'] },
  { sourceType: 'CPT', targetType: 'SPEC', roles: ['covers', 'verifies', 'references'] },
  { sourceType: 'CPT', targetType: 'REQ', roles: ['covers', 'verifies', 'references'] },
  { sourceType: 'CPT', targetType: 'TC', roles: ['implements'] },
  { sourceType: 'CPT', targetType: 'CPT', roles: ['derives_from', 'refines', 'relates_to'] },
  { sourceType: 'CPT', targetType: 'STD', roles: ['references'] },
  { sourceType: 'CPT', targetType: 'TS', roles: ['references'] },
  { sourceType: 'TC', targetType: 'REQ', roles: ['verifies'] },
  { sourceType: 'TC', targetType: 'SPEC', roles: ['verifies'] },
  { sourceType: 'TC', targetType: 'PRT', roles: ['implements', 'references'] },
  { sourceType: 'TC', targetType: 'TC', roles: ['depends_on', 'duplicates', 'relates_to'] },
  { sourceType: 'TC', targetType: 'STD', roles: ['references'] },
  { sourceType: 'TC', targetType: 'DEF', roles: ['references'] },
  { sourceType: 'TS', targetType: 'TC', roles: ['contains', 'references'] },
  { sourceType: 'TS', targetType: 'CPT', roles: ['contains', 'references'] },
  { sourceType: 'TS', targetType: 'SPEC', roles: ['covers', 'references'] },
  { sourceType: 'TS', targetType: 'REQ', roles: ['covers', 'references'] },
  { sourceType: 'TS', targetType: 'TS', roles: ['relates_to'] },
  { sourceType: 'TS', targetType: 'CMP', roles: ['relates_to'] },
  { sourceType: 'CMP', targetType: 'SPEC', roles: ['verifies', 'references'] },
  { sourceType: 'CMP', targetType: 'REQ', roles: ['covers', 'references'] },
  { sourceType: 'CMP', targetType: 'TC', roles: ['contains', 'references'] },
  { sourceType: 'CMP', targetType: 'CPT', roles: ['contains', 'references'] },
  { sourceType: 'CMP', targetType: 'TS', roles: ['relates_to'] },
  { sourceType: 'CMP', targetType: 'DEF', roles: ['references'] },
  { sourceType: 'CMP', targetType: 'CMP', roles: ['relates_to'] },
  { sourceType: 'PRT', targetType: 'REQ', roles: ['verifies', 'references'] },
  { sourceType: 'PRT', targetType: 'SPEC', roles: ['verifies', 'references'] },
  { sourceType: 'PRT', targetType: 'CPT', roles: ['implements'] },
  { sourceType: 'PRT', targetType: 'PRT', roles: ['derives_from', 'depends_on', 'duplicates', 'relates_to'] },
  { sourceType: 'PRT', targetType: 'STD', roles: ['references'] },
  { sourceType: 'RPT', targetType: 'REQ', roles: ['references'] },
  { sourceType: 'RPT', targetType: 'SPEC', roles: ['references'] },
  { sourceType: 'RPT', targetType: 'CPT', roles: ['references'] },
  { sourceType: 'RPT', targetType: 'TC', roles: ['references'] },
  { sourceType: 'RPT', targetType: 'TS', roles: ['references'] },
  { sourceType: 'RPT', targetType: 'CMP', roles: ['references'] },
  { sourceType: 'RPT', targetType: 'PRT', roles: ['references'] },
  { sourceType: 'RPT', targetType: 'DES', roles: ['references'] },
  { sourceType: 'RPT', targetType: 'RSK', roles: ['references'] },
  { sourceType: 'RPT', targetType: 'CHG', roles: ['references'] },
  { sourceType: 'RPT', targetType: 'STD', roles: ['references'] },
  { sourceType: 'RPT', targetType: 'DEF', roles: ['references'] },
  { sourceType: 'RPT', targetType: 'RPT', roles: ['duplicates', 'relates_to', 'references'] },
  { sourceType: 'DES', targetType: 'REQ', roles: ['satisfies', 'implements', 'references'] },
  { sourceType: 'DES', targetType: 'SPEC', roles: ['implements', 'references'] },
  { sourceType: 'DES', targetType: 'RSK', roles: ['mitigates'] },
  { sourceType: 'DES', targetType: 'DES', roles: ['depends_on', 'derives_from', 'duplicates', 'relates_to'] },
  { sourceType: 'DES', targetType: 'STD', roles: ['references'] },
  { sourceType: 'RSK', targetType: 'REQ', roles: ['impacts', 'mitigates', 'references'] },
  { sourceType: 'RSK', targetType: 'SPEC', roles: ['impacts', 'references'] },
  { sourceType: 'RSK', targetType: 'DES', roles: ['impacts', 'references'] },
  { sourceType: 'RSK', targetType: 'TC', roles: ['impacts', 'references'] },
  { sourceType: 'RSK', targetType: 'CPT', roles: ['impacts', 'references'] },
  { sourceType: 'RSK', targetType: 'PRT', roles: ['impacts', 'references'] },
  { sourceType: 'RSK', targetType: 'CHG', roles: ['impacts', 'references'] },
  { sourceType: 'RSK', targetType: 'RSK', roles: ['depends_on', 'duplicates', 'relates_to'] },
  { sourceType: 'RSK', targetType: 'STD', roles: ['references'] },
  { sourceType: 'RSK', targetType: 'DEF', roles: ['impacts', 'references'] },
  { sourceType: 'CHG', targetType: 'REQ', roles: ['impacts', 'implements', 'blocks', 'references'] },
  { sourceType: 'CHG', targetType: 'SPEC', roles: ['impacts', 'implements', 'blocks', 'references'] },
  { sourceType: 'CHG', targetType: 'DES', roles: ['impacts', 'implements', 'blocks', 'references'] },
  { sourceType: 'CHG', targetType: 'TC', roles: ['impacts', 'blocks', 'references'] },
  { sourceType: 'CHG', targetType: 'CPT', roles: ['impacts', 'blocks', 'references'] },
  { sourceType: 'CHG', targetType: 'PRT', roles: ['impacts', 'blocks', 'references'] },
  { sourceType: 'CHG', targetType: 'RSK', roles: ['mitigates', 'impacts', 'references'] },
  { sourceType: 'CHG', targetType: 'CHG', roles: ['depends_on', 'duplicates', 'blocks', 'relates_to'] },
  { sourceType: 'CHG', targetType: 'STD', roles: ['references'] },
  { sourceType: 'CHG', targetType: 'DEF', roles: ['implements', 'references'] },
  { sourceType: 'DEF', targetType: 'REQ', roles: ['impacts', 'references'] },
  { sourceType: 'DEF', targetType: 'SPEC', roles: ['impacts', 'references'] },
  { sourceType: 'DEF', targetType: 'TC', roles: ['references'] },
  { sourceType: 'DEF', targetType: 'CPT', roles: ['references'] },
  { sourceType: 'DEF', targetType: 'PRT', roles: ['references'] },
  { sourceType: 'DEF', targetType: 'CHG', roles: ['references'] },
  { sourceType: 'DEF', targetType: 'RPT', roles: ['references'] },
  { sourceType: 'DEF', targetType: 'DES', roles: ['impacts', 'references'] },
  { sourceType: 'DEF', targetType: 'RSK', roles: ['references'] },
  { sourceType: 'DEF', targetType: 'DEF', roles: ['duplicates', 'relates_to', 'depends_on'] },
  { sourceType: 'DEF', targetType: 'STD', roles: ['references'] },
  { sourceType: 'DEF', targetType: 'CMP', roles: ['references'] },
  { sourceType: 'CMP', targetType: 'DEF', roles: ['references'] },
]

const DOC_LINK_ROLE_LABELS: Record<DocLinkRole, [string, string]> = {
  derives_from: ['derives from', 'derived by'],
  refines: ['refines', 'refined by'],
  satisfies: ['satisfies', 'satisfied by'],
  implements: ['implements', 'implemented by'],
  verifies: ['verifies', 'verified by'],
  mitigates: ['mitigates', 'mitigated by'],
  depends_on: ['depends on', 'dependency of'],
  impacts: ['impacts', 'impacted by'],
  blocks: ['blocks', 'blocked by'],
  duplicates: ['duplicates', 'duplicated by'],
  references: ['references', 'referenced by'],
  relates_to: ['relates to', 'related to'],
  covers: ['covers', 'covered by'],
  contains: ['contains', 'contained by'],
}

export const DOC_LINK_ROLE_COLORS: Record<DocLinkRole, string> = {
  derives_from: 'bg-indigo-500/10 text-indigo-700 dark:text-indigo-400',
  refines: 'bg-cyan-500/10 text-cyan-700 dark:text-cyan-400',
  satisfies: 'bg-green-500/10 text-green-700 dark:text-green-400',
  implements: 'bg-teal-500/10 text-teal-700 dark:text-teal-400',
  verifies: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
  mitigates: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
  depends_on: 'bg-orange-500/10 text-orange-700 dark:text-orange-400',
  impacts: 'bg-red-500/10 text-red-700 dark:text-red-400',
  blocks: 'bg-rose-500/10 text-rose-700 dark:text-rose-400',
  duplicates: 'bg-gray-500/10 text-gray-700 dark:text-gray-400',
  references: 'bg-blue-500/10 text-blue-700 dark:text-blue-400',
  relates_to: 'bg-slate-500/10 text-slate-700 dark:text-slate-400',
  covers: 'bg-sky-500/10 text-sky-700 dark:text-sky-400',
  contains: 'bg-violet-500/10 text-violet-700 dark:text-violet-400',
}

export function docUrl(prefix: string | undefined, docType: DocType, docId: string | number): string {
  const slug = DOC_TYPE_SLUGS[docType]
  return `/projects/${prefix}/docs/${slug}/${docId}`
}

export function docEditUrl(prefix: string | undefined, docType: DocType, docId: string | number): string {
  const slug = DOC_TYPE_SLUGS[docType]
  return `/projects/${prefix}/docs/${slug}/${docId}/edit`
}

export function docCreateUrl(prefix: string | undefined, docType: DocType): string {
  const slug = DOC_TYPE_SLUGS[docType]
  return `/projects/${prefix}/docs/new?type=${slug}`
}

export function docListUrl(prefix: string | undefined, docType: DocType, extraSearch?: string): string {
  const slug = DOC_TYPE_SLUGS[docType]
  const base = `/projects/${prefix}/docs?type=${slug}`
  return extraSearch ? `${base}&${extraSearch}` : base
}

export function kindSlugToType(slug: string): DocType | null {
  return SLUG_TO_DOC_TYPE[slug] || null
}

const LEGACY_DOC_TYPE_ALIASES: Record<string, DocType> = {
  TCO: 'CPT',
  PROT: 'PRT',
}

export function normalizeDocTypeParam(value: string | null | undefined): DocType | null {
  if (!value) return null
  const upper = value.toUpperCase()
  const legacy = LEGACY_DOC_TYPE_ALIASES[upper]
  if (legacy) return legacy
  if (DOC_TYPE_CODES.includes(upper as DocType)) {
    return upper as DocType
  }
  return kindSlugToType(value)
}

export function getDocLinkRoleLabel(role: string, direction: 'incoming' | 'outgoing'): string {
  const pair = DOC_LINK_ROLE_LABELS[role as DocLinkRole]
  if (!pair) {
    return role.split('_').join(' ')
  }
  return direction === 'outgoing' ? pair[0] : pair[1]
}

function getCanonicalDocLinkRoles(sourceType: DocType, targetType: DocType): DocLinkRole[] {
  const matchedRow = DOC_LINK_RULE_ROWS.find((row) => (
    row.sourceType === sourceType &&
    row.targetType === targetType
  ))
  return matchedRow ? matchedRow.roles : []
}

export function getDocLinkOptions(sourceType: DocType, targetType: DocType): DocLinkOption[] {
  if (!DOC_TYPE_CODES.includes(sourceType) || !DOC_TYPE_CODES.includes(targetType)) {
    return []
  }

  const outgoingRoles = getCanonicalDocLinkRoles(sourceType, targetType)
  const incomingRoles = sourceType === targetType ? [] : getCanonicalDocLinkRoles(targetType, sourceType)

  const options: DocLinkOption[] = outgoingRoles.map((role) => ({
    key: `${sourceType}:${role}:${targetType}:outgoing`,
    label: getDocLinkRoleLabel(role, 'outgoing'),
    role,
    sourceType,
    targetType,
    displayDirection: 'outgoing',
  }))

  incomingRoles.forEach((role) => {
    options.push({
      key: `${targetType}:${role}:${sourceType}:incoming`,
      label: getDocLinkRoleLabel(role, 'incoming'),
      role,
      sourceType: targetType,
      targetType: sourceType,
      displayDirection: 'incoming',
    })
  })

  return options
}

export function getAllowedDocLinkRoles(sourceType: DocType, targetType: DocType): DocLinkRole[] {
  return Array.from(new Set(getDocLinkOptions(sourceType, targetType).map((option) => option.role)))
}
