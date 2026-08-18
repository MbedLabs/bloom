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

function generateId(): string {
  return `row-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
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

function isTcsRowType(value: unknown): value is TcsRowType {
  return typeof value === 'string' && TCS_ROW_TYPE_OPTIONS.some((option) => option.value === value)
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function coerceTcsRow(row: Record<string, unknown>): TcsRow {
  const rowType = isTcsRowType(row.row_type) ? row.row_type : 'step'
  const indentLevel = typeof row.indent_level === 'number' && Number.isFinite(row.indent_level)
    ? Math.max(0, row.indent_level)
    : 0

  return {
    id: typeof row.id === 'string' && row.id.trim() ? row.id : generateId(),
    row_type: rowType,
    label: typeof row.label === 'string' && row.label.trim() ? row.label : getDefaultTcsLabel(rowType),
    description: typeof row.description === 'string' ? row.description : '',
    expected_result: typeof row.expected_result === 'string' ? row.expected_result : '',
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

export function normalizeTcsRows(steps: unknown): TcsRow[] {
  if (!Array.isArray(steps) || steps.length === 0) return []
  if (steps.every((row) => isRecord(row) && 'row_type' in row)) {
    return steps.map((row) => coerceTcsRow(row as Record<string, unknown>))
  }
  if (steps.every((row) => isRecord(row) && ('action' in row || 'step_number' in row))) {
    return migrateOldSteps(steps as Array<{ step_number?: number; action?: string; expected_result?: string }>)
  }
  return []
}
