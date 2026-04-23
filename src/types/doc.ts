export type DocType = 'REQ' | 'SPEC' | 'TC' | 'DES' | 'RSK' | 'CHG' | 'TCO' | 'PROT' | 'RPT' | 'STD'

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
  TCO: {
    label: 'Test Concept',
    typeCode: 'TCO',
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
  PROT: {
    label: 'Protocol',
    typeCode: 'PROT',
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
  TCO: 'Test Concept',
  PROT: 'Protocol',
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
  TCO: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
  PROT: 'bg-teal-500/10 text-teal-700 dark:text-teal-400',
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
  TCO: 'test-concepts',
  PROT: 'protocols',
  RPT: 'reports',
  STD: 'standards',
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
  return `/projects/${prefix}/docs/new?type=${docType}`
}

export function kindSlugToType(slug: string): DocType | null {
  const entry = Object.entries(DOC_TYPE_SLUGS).find(([, v]) => v === slug)
  return entry ? (entry[0] as DocType) : null
}
