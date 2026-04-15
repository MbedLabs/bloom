import { useState } from 'react'
import { Plus, Trash2, GripVertical, ChevronDown, ChevronRight } from 'lucide-react'

export type TcsRowType = 'precondition' | 'step' | 'loop' | 'postcondition'

export interface TcsRow {
  id: string
  row_type: TcsRowType
  label: string
  description: string
  expected_result: string
  indent_level: number
  collapsed: boolean
}

const ROW_TYPE_OPTIONS: { value: TcsRowType; label: string }[] = [
  { value: 'precondition', label: 'Pre-Condition' },
  { value: 'step', label: 'Step' },
  { value: 'loop', label: 'Loop' },
  { value: 'postcondition', label: 'Post-Condition' },
]

const ROW_TYPE_COLORS: Record<TcsRowType, string> = {
  precondition: 'bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-200 dark:border-blue-800',
  step: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800',
  loop: 'bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-200 dark:border-amber-800',
  postcondition: 'bg-purple-500/10 text-purple-700 dark:text-purple-400 border-purple-200 dark:border-purple-800',
}

const ROW_TYPE_INDICATOR: Record<TcsRowType, string> = {
  precondition: 'border-l-4 border-l-blue-400',
  step: 'border-l-4 border-l-emerald-400',
  loop: 'border-l-4 border-l-amber-400',
  postcondition: 'border-l-4 border-l-purple-400',
}

function generateId(): string {
  return `row-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}

function createDefaultRow(type: TcsRowType, index: number): TcsRow {
  const labels: Record<TcsRowType, (i: number) => string> = {
    precondition: () => 'Pre-Condition',
    step: (i) => `Step ${i}`,
    loop: (i) => `Loop ${i}`,
    postcondition: () => 'Post-Condition',
  }
  return {
    id: generateId(),
    row_type: type,
    label: labels[type](index),
    description: '',
    expected_result: '',
    indent_level: 0,
    collapsed: false,
  }
}

interface TcsArteTableProps {
  rows: TcsRow[]
  onChange: (rows: TcsRow[]) => void
  editable?: boolean
}

export function TcsArteTable({ rows, onChange, editable = false }: TcsArteTableProps) {
  if (editable) {
    return <TcsArteTableEditor rows={rows} onChange={onChange} />
  }
  return <TcsArteTableView rows={rows} />
}

function TcsArteTableView({ rows }: { rows: TcsRow[] }) {
  if (!rows || rows.length === 0) return null

  return (
    <div className="bg-card rounded-lg shadow-elegant overflow-hidden">
      <div className="px-6 py-4 border-b border-border">
        <h3 className="text-lg font-semibold">Test Case Specification</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-border">
          <thead className="bg-muted/50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase w-40">Step</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Description</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase w-72">Expected Result</th>
            </tr>
          </thead>
          <tbody className="bg-card divide-y divide-border">
            {rows.map((row) => (
              <tr key={row.id} className={`hover:bg-accent/50 ${ROW_TYPE_INDICATOR[row.row_type]}`}>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center" style={{ paddingLeft: `${row.indent_level * 20}px` }}>
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${ROW_TYPE_COLORS[row.row_type]}`}>
                      {row.label}
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4 text-sm text-foreground whitespace-pre-wrap">
                  {row.description || <span className="text-muted-foreground italic">—</span>}
                </td>
                <td className="px-6 py-4 text-sm text-foreground whitespace-pre-wrap">
                  {row.expected_result || <span className="text-muted-foreground italic">—</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function TcsArteTableEditor({ rows, onChange }: { rows: TcsRow[]; onChange: (rows: TcsRow[]) => void }) {
  const [dragIndex, setDragIndex] = useState<number | null>(null)
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null)
  const [addMenuOpen, setAddMenuOpen] = useState(false)

  const updateRow = (index: number, updates: Partial<TcsRow>) => {
    const newRows = [...rows]
    newRows[index] = { ...newRows[index], ...updates }
    onChange(newRows)
  }

  const addRow = (type: TcsRowType) => {
    const counts: Record<TcsRowType, number> = { precondition: 0, step: 0, loop: 0, postcondition: 0 }
    rows.forEach(r => { counts[r.row_type]++ })
    const newRow = createDefaultRow(type, counts[type] + 1)
    onChange([...rows, newRow])
    setAddMenuOpen(false)
  }

  const removeRow = (index: number) => {
    const newRows = rows.filter((_, i) => i !== index)
    onChange(newRows)
  }

  const moveRow = (from: number, to: number) => {
    if (to < 0 || to >= rows.length) return
    const newRows = [...rows]
    const [moved] = newRows.splice(from, 1)
    newRows.splice(to, 0, moved)
    onChange(newRows)
    setDragIndex(null)
    setDragOverIndex(null)
  }

  const indentRow = (index: number, direction: 'increase' | 'decrease') => {
    const newRows = [...rows]
    const row = newRows[index]
    const delta = direction === 'increase' ? 1 : -1
    newRows[index] = { ...row, indent_level: Math.max(0, row.indent_level + delta) }
    onChange(newRows)
  }

  return (
    <div className="space-y-3">
      <div className="bg-card rounded-lg shadow-elegant overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-border">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-3 py-3 text-left text-xs font-medium text-muted-foreground uppercase w-10"></th>
                <th className="px-3 py-3 text-left text-xs font-medium text-muted-foreground uppercase w-36">Step</th>
                <th className="px-3 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Description</th>
                <th className="px-3 py-3 text-left text-xs font-medium text-muted-foreground uppercase w-72">Expected Result</th>
                <th className="px-3 py-3 text-left text-xs font-medium text-muted-foreground uppercase w-24">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-card divide-y divide-border">
              {rows.map((row, index) => (
                <tr
                  key={row.id}
                  className={`${ROW_TYPE_INDICATOR[row.row_type]} ${dragOverIndex === index ? 'bg-accent/30' : 'hover:bg-accent/50'}`}
                  draggable
                  onDragStart={() => setDragIndex(index)}
                  onDragOver={(e) => { e.preventDefault(); setDragOverIndex(index) }}
                  onDragLeave={() => setDragOverIndex(null)}
                  onDrop={() => { if (dragIndex !== null) moveRow(dragIndex, index) }}
                >
                  <td className="px-3 py-3">
                    <div className="flex items-center space-x-1" style={{ paddingLeft: `${row.indent_level * 16}px` }}>
                      <GripVertical className="h-4 w-4 text-muted-foreground cursor-grab" />
                      {row.row_type === 'loop' && (
                        <button
                          type="button"
                          onClick={() => updateRow(index, { collapsed: !row.collapsed })}
                          className="p-0.5 hover:bg-accent/50 rounded"
                        >
                          {row.collapsed ? <ChevronRight className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                        </button>
                      )}
                    </div>
                  </td>
                  <td className="px-3 py-3">
                    <div className="flex items-center space-x-1">
                      <select
                        value={row.row_type}
                        onChange={(e) => {
                          const newType = e.target.value as TcsRowType
                          const counts: Record<TcsRowType, number> = { precondition: 0, step: 0, loop: 0, postcondition: 0 }
                          rows.forEach((r, i) => { if (i !== index) counts[r.row_type]++ })
                          updateRow(index, {
                            row_type: newType,
                            label: ROW_TYPE_OPTIONS.find(o => o.value === newType)?.label || newType,
                          })
                        }}
                        className="text-xs px-1 py-0.5 bg-background border border-input rounded focus:ring-1 focus:ring-ring"
                      >
                        {ROW_TYPE_OPTIONS.map(opt => (
                          <option key={opt.value} value={opt.value}>{opt.label}</option>
                        ))}
                      </select>
                      <input
                        type="text"
                        value={row.label}
                        onChange={(e) => updateRow(index, { label: e.target.value })}
                        className="text-xs px-1 py-0.5 bg-background border border-input rounded focus:ring-1 focus:ring-ring w-16"
                        placeholder="Label"
                      />
                    </div>
                  </td>
                  <td className="px-3 py-3">
                    <textarea
                      value={row.description}
                      onChange={(e) => updateRow(index, { description: e.target.value })}
                      className="w-full px-2 py-1 bg-background border border-input rounded text-sm focus:ring-1 focus:ring-ring focus:border-ring min-h-[32px] resize-y"
                      placeholder="Description..."
                      rows={1}
                    />
                  </td>
                  <td className="px-3 py-3">
                    <textarea
                      value={row.expected_result}
                      onChange={(e) => updateRow(index, { expected_result: e.target.value })}
                      className="w-full px-2 py-1 bg-background border border-input rounded text-sm focus:ring-1 focus:ring-ring focus:border-ring min-h-[32px] resize-y"
                      placeholder="Expected result..."
                      rows={1}
                    />
                  </td>
                  <td className="px-3 py-3">
                    <div className="flex items-center space-x-1">
                      <button
                        type="button"
                        onClick={() => indentRow(index, 'decrease')}
                        className="p-1 hover:bg-accent/50 rounded text-muted-foreground text-xs"
                        title="Outdent"
                      >
                        ←
                      </button>
                      <button
                        type="button"
                        onClick={() => indentRow(index, 'increase')}
                        className="p-1 hover:bg-accent/50 rounded text-muted-foreground text-xs"
                        title="Indent"
                      >
                        →
                      </button>
                      <button
                        type="button"
                        onClick={() => removeRow(index)}
                        className="p-1 hover:bg-destructive/10 rounded text-destructive"
                        title="Remove row"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-muted-foreground">
                    No rows yet. Add a row using the buttons below.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="flex items-center space-x-2">
        <div className="relative">
          <button
            type="button"
            onClick={() => setAddMenuOpen(!addMenuOpen)}
            className="inline-flex items-center px-3 py-1.5 bg-primary text-white rounded-md hover:bg-primary/90 text-sm"
          >
            <Plus className="h-4 w-4 mr-1" />
            Add Row
          </button>
          {addMenuOpen && (
            <div className="absolute left-0 mt-1 w-48 bg-card rounded-md shadow-lg border border-border z-10">
              {ROW_TYPE_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => addRow(opt.value)}
                  className="w-full text-left px-4 py-2 text-sm hover:bg-accent/50 flex items-center space-x-2"
                >
                  <span className={`inline-block w-2 h-2 rounded-full ${
                    opt.value === 'precondition' ? 'bg-blue-400' :
                    opt.value === 'step' ? 'bg-emerald-400' :
                    opt.value === 'loop' ? 'bg-amber-400' :
                    'bg-purple-400'
                  }`} />
                  <span>{opt.label}</span>
                </button>
              ))}
            </div>
          )}
        </div>
        <span className="text-xs text-muted-foreground">
          {rows.length} row{rows.length !== 1 ? 's' : ''}
          {rows.some(r => r.row_type === 'precondition') && ` | ${rows.filter(r => r.row_type === 'precondition').length} precondition(s)`}
          {rows.some(r => r.row_type === 'step') && ` | ${rows.filter(r => r.row_type === 'step').length} step(s)`}
          {rows.some(r => r.row_type === 'loop') && ` | ${rows.filter(r => r.row_type === 'loop').length} loop(s)`}
        </span>
      </div>
    </div>
  )
}

export function migrateOldSteps(oldSteps: Array<{ step_number: number; action: string; expected_result: string }>): TcsRow[] {
  return oldSteps.map((s) => ({
    id: generateId(),
    row_type: 'step' as TcsRowType,
    label: `Step ${s.step_number}`,
    description: s.action,
    expected_result: s.expected_result,
    indent_level: 0,
    collapsed: false,
  }))
}
