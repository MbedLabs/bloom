export type DocType = 'REQ' | 'TC' | 'DES' | 'RSK' | 'CHG' | 'TCO' | 'DOC'

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
      { key: 'req_type', label: 'Type', type: 'select', options: ['Functional', 'Non-Functional', 'Performance', 'Security', 'Usability'] },
      { key: 'req_origin', label: 'Origin', type: 'select', options: ['Internal', 'Customer', 'Compliance', 'Regulatory', 'Legal', 'Business', 'Technical'] },
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
      { key: 'design_type', label: 'Design Type', type: 'select', options: ['Architecture', 'Interface', 'Database', 'UI/UX', 'Algorithm'] },
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
      { key: 'risk_category', label: 'Category', type: 'select', options: ['Technical', 'Schedule', 'Cost', 'Quality', 'Resource'] },
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
      { key: 'change_type', label: 'Change Type', type: 'select', options: ['Enhancement', 'Bug Fix', 'Refactoring', 'New Feature'] },
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
  DOC: {
    label: 'Document',
    typeCode: 'DOC',
    apiBase: 'documents',
    idField: 'doc_id',
    titleField: 'title',
    descriptionField: 'description',
    statusOptions: ['Draft', 'Review', 'Approved'],
    fields: [
      { key: 'title', label: 'Title', type: 'text', required: true },
      { key: 'description', label: 'Description', type: 'textarea' },
      { key: 'doc_type', label: 'Document Type', type: 'select', options: ['Specification', 'Test Concept', 'Report', 'Other'] },
      { key: 'version', label: 'Version', type: 'text' },
    ],
  },
}

export const DOC_TYPE_LABELS: Record<DocType, string> = {
  REQ: 'Requirement',
  TC: 'Test Case',
  DES: 'Design',
  RSK: 'Risk',
  CHG: 'Change Request',
  TCO: 'Test Concept',
  DOC: 'Document',
}

export const DOC_TYPE_COLORS: Record<DocType, string> = {
  REQ: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
  TC: 'bg-cyan-500/10 text-cyan-700 dark:text-cyan-400',
  DES: 'bg-violet-500/10 text-violet-700 dark:text-violet-400',
  RSK: 'bg-red-500/10 text-red-700 dark:text-red-400',
  CHG: 'bg-blue-500/10 text-blue-700 dark:text-blue-400',
  TCO: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
  DOC: 'bg-primary/10 text-primary',
}
