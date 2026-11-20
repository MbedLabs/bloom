export type TcsRowType = 'precondition' | 'step' | 'loop'

export interface TcsRow {
  id: string
  row_type: TcsRowType
  label: string
  description: string
  expected_result: string
  indent_level: number
  collapsed: boolean
}

export const TCS_ROW_TYPE_OPTIONS: { value: TcsRowType; label: string }[] = [
  { value: 'precondition', label: 'Pre-Condition' },
  { value: 'step', label: 'Step' },
  { value: 'loop', label: 'Loop' },
]

/** Returns a row id of the form `row-<epoch ms>-<14 base-36 characters from crypto.getRandomValues>`. */
function generateId(): string {
  const random = Array.from(crypto.getRandomValues(new Uint32Array(2)), (value) => value.toString(36).padStart(7, '0'))
  return `row-${Date.now()}-${random.join('')}`
}

function getDefaultTcsLabel(type: TcsRowType): string {
  return TCS_ROW_TYPE_OPTIONS.find((option) => option.value === type)?.label || type
}

export function createDefaultTcsRow(type: TcsRowType, indentLevel = 0): TcsRow {
  return {
    id: generateId(),
    row_type: type,
    label: getDefaultTcsLabel(type),
    description: '',
    expected_result: '',
    indent_level: indentLevel,
    collapsed: false,
  }
}

export function createDefaultTcRows(): TcsRow[] {
  return [
    createDefaultTcsRow('precondition'),
    createDefaultTcsRow('step'),
  ]
}

const ROW_TYPE_NAMES: Record<string, TcsRowType> = {
  precondition: 'precondition',
  'pre-condition': 'precondition',
  step: 'step',
  loop: 'loop',
}

/** The row type a `row_type` or `label` value names in any letter case, or null. */
function rowTypeOf(value: unknown): TcsRowType | null {
  return typeof value === 'string' ? ROW_TYPE_NAMES[value.trim().toLowerCase()] ?? null : null
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

/** The first of the keys holding non-empty text, else an empty string. */
function firstText(row: Record<string, unknown>, keys: string[]): string {
  for (const key of keys) {
    const value = row[key]
    if (typeof value === 'string' && value !== '') return value
    if (typeof value === 'number') return String(value)
  }
  return ''
}

function coerceTcsRow(row: Record<string, unknown>): TcsRow {
  const typed = typeof row.row_type === 'string' && row.row_type.trim() !== ''
  const rowType = (typed ? rowTypeOf(row.row_type) : rowTypeOf(row.label)) ?? 'step'
  const indentLevel = typeof row.indent_level === 'number' && Number.isFinite(row.indent_level)
    ? Math.max(0, row.indent_level)
    : 0

  return {
    id: typeof row.id === 'string' && row.id.trim() ? row.id : generateId(),
    row_type: rowType,
    label: typeof row.label === 'string' && row.label.trim() ? row.label : getDefaultTcsLabel(rowType),
    description: firstText(row, ['description', 'action', 'step']),
    expected_result: firstText(row, ['expected_result', 'expected']),
    indent_level: indentLevel,
    collapsed: Boolean(row.collapsed),
  }
}

export function migrateOldSteps(oldSteps: Array<{ step_number?: number; action?: string; expected_result?: string }>): TcsRow[] {
  return oldSteps.map((step) => ({
    id: generateId(),
    row_type: 'step',
    label: 'Step',
    description: step.action || '',
    expected_result: step.expected_result || '',
    indent_level: 0,
    collapsed: false,
  }))
}

/** The rows of a stored test case in the editor's form: every row is kept, a row without a type is a step. */
export function normalizeTcsRows(steps: unknown): TcsRow[] {
  const list = isRecord(steps) && !Array.isArray(steps) && Array.isArray(steps.steps) ? steps.steps : steps
  if (!Array.isArray(list) || list.length === 0) return []
  return list.map((row) => coerceTcsRow(isRecord(row) ? row : { description: String(row) }))
}
