import { useState } from 'react'
import type { ReactNode } from 'react'
import {
  ChevronDown,
  ChevronRight,
  Copy,
  GripVertical,
  Indent,
  MoreHorizontal,
  Outdent,
  Plus,
  Trash2,
} from 'lucide-react'
import {
  createDefaultTcsRow,
  TCS_ROW_TYPE_OPTIONS,
  type TcsRow,
  type TcsRowType,
} from '../utils/tcs'

const ROW_TYPE_STYLES: Record<TcsRowType, { marker: string; chip: string; row: string; label: string }> = {
  precondition: {
    marker: 'bg-sky-500',
    chip: 'border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-800 dark:bg-sky-950/30 dark:text-sky-300',
    row: 'bg-sky-500/[0.025]',
    label: 'Pre-Condition',
  },
  step: {
    marker: 'bg-emerald-500',
    chip: 'border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-300',
    row: '',
    label: 'Step',
  },
  loop: {
    marker: 'bg-amber-500',
    chip: 'border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-300',
    row: 'bg-amber-500/[0.06]',
    label: 'Loop',
  },
}

function getVisibleRows(rows: TcsRow[]) {
  let hiddenBelowIndent: number | null = null

  return rows
    .map((row, index) => {
      if (hiddenBelowIndent !== null) {
        if (row.indent_level > hiddenBelowIndent) return null
        hiddenBelowIndent = null
      }

      const visible = { row, index }
      if (row.row_type === 'loop' && row.collapsed) {
        hiddenBelowIndent = row.indent_level
      }
      return visible
    })
    .filter((item): item is { row: TcsRow; index: number } => item !== null)
}

function hasChildRows(rows: TcsRow[], index: number) {
  const row = rows[index]
  const nextRow = rows[index + 1]
  return row?.row_type === 'loop' && Boolean(nextRow && nextRow.indent_level > row.indent_level)
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
  const visibleRows = getVisibleRows(rows)

  return (
    <section className="border border-border bg-card shadow-elegant">
      <div className="overflow-x-auto">
        <div className="min-w-[840px]">
          <div className="grid grid-cols-[14rem_minmax(18rem,1fr)_minmax(18rem,1fr)] border-b border-border bg-muted/40 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            <div className="px-3 py-2">Type</div>
            <div className="px-3 py-2">Action / Description</div>
            <div className="px-3 py-2">Expected Result</div>
          </div>
          <div className="divide-y divide-border">
            {visibleRows.map(({ row }) => (
              <TcsViewRow key={row.id} row={row} hasChildren={hasChildRows(rows, rows.findIndex((candidate) => candidate.id === row.id))} />
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

function TcsViewRow({ row, hasChildren }: { row: TcsRow; hasChildren: boolean }) {
  const styles = ROW_TYPE_STYLES[row.row_type]
  const isLoop = row.row_type === 'loop'

  return (
    <div className={`grid grid-cols-[14rem_minmax(18rem,1fr)_minmax(18rem,1fr)] min-h-[4rem] ${styles.row}`}>
      <div className="border-r border-border/70 px-3 py-3">
        <div className="flex items-center gap-2" style={{ paddingLeft: `${row.indent_level * 18}px` }}>
          <span className={`h-6 w-1 rounded-full ${styles.marker}`} />
          {isLoop && hasChildren && (
            <span className="text-muted-foreground">
              {row.collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </span>
          )}
          <div className="min-w-0">
            <div className={`inline-flex min-h-6 items-center rounded border px-2 py-0.5 text-[11px] font-semibold ${styles.chip}`}>
              {styles.label}
            </div>
          </div>
        </div>
      </div>
      <div className={`border-r border-border/70 px-4 py-3 text-sm ${isLoop ? 'font-medium text-foreground' : 'text-foreground'} whitespace-pre-wrap`}>
        {row.description || <span className="text-muted-foreground">-</span>}
      </div>
      <div className="px-4 py-3 text-sm text-foreground whitespace-pre-wrap">
        {row.expected_result || <span className="text-muted-foreground">-</span>}
      </div>
    </div>
  )
}

function TcsArteTableEditor({ rows, onChange }: { rows: TcsRow[]; onChange: (rows: TcsRow[]) => void }) {
  const [dragIndex, setDragIndex] = useState<number | null>(null)
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null)
  const [actionMenu, setActionMenu] = useState<{ index: number; top: number; left: number } | null>(null)
  const [addMenu, setAddMenu] = useState<{ top: number; left: number } | null>(null)
  const visibleRows = getVisibleRows(rows)

  const getMenuPosition = (button: HTMLButtonElement, menuHeight: number) => {
    const rect = button.getBoundingClientRect()
    const menuWidth = 176
    const spaceBelow = window.innerHeight - rect.bottom
    const top = spaceBelow < menuHeight + 12
      ? Math.max(8, rect.top - menuHeight - 4)
      : rect.bottom + 4
    const left = Math.min(window.innerWidth - menuWidth - 8, Math.max(8, rect.right - menuWidth))
    return { top, left }
  }

  const updateRow = (index: number, updates: Partial<TcsRow>) => {
    const newRows = [...rows]
    newRows[index] = { ...newRows[index], ...updates }
    onChange(newRows)
  }

  const removeRow = (index: number) => {
    onChange(rows.filter((_, i) => i !== index))
  }

  const moveRow = (from: number, to: number) => {
    if (to < 0 || to >= rows.length) return
    const newRows = [...rows]
    const [moved] = newRows.splice(from, 1)
    newRows.splice(to, 0, moved)
    onChange(newRows)
    setDragIndex(null)
    setDragOverIndex(null)
    setActionMenu(null)
    setAddMenu(null)
  }

  const insertRow = (index: number, type: TcsRowType = 'step') => {
    const anchor = rows[index]
    const newRows = [...rows]
    newRows.splice(index + 1, 0, createDefaultTcsRow(type, anchor?.indent_level || 0))
    onChange(newRows)
  }

  const duplicateRow = (index: number) => {
    const source = rows[index]
    if (!source) return
    const newRows = [...rows]
    newRows.splice(index + 1, 0, { ...source, id: createDefaultTcsRow(source.row_type).id })
    onChange(newRows)
  }

  const indentRow = (index: number, direction: 'increase' | 'decrease') => {
    const row = rows[index]
    const delta = direction === 'increase' ? 1 : -1
    updateRow(index, { indent_level: Math.max(0, row.indent_level + delta) })
  }

  const addRow = (type: TcsRowType) => {
    onChange([...rows, createDefaultTcsRow(type)])
    setAddMenu(null)
  }

  return (
    <section className="border border-border bg-card shadow-elegant">
      <div className="overflow-x-auto">
        <div className="min-w-[860px]">
          <div className="grid grid-cols-[15rem_minmax(18rem,1fr)_minmax(18rem,1fr)_4rem] border-b border-border bg-muted/40 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            <div className="px-3 py-2">Type</div>
            <div className="px-3 py-2">Action</div>
            <div className="px-3 py-2">Expected Result</div>
            <div className="px-2 py-2 text-right">Actions</div>
          </div>
          <div className="divide-y divide-border">
            {visibleRows.map(({ row, index }) => (
              <TcsEditorRow
                key={row.id}
                row={row}
                hasChildren={hasChildRows(rows, index)}
                isDragTarget={dragOverIndex === index}
                menuOpen={actionMenu?.index === index}
                menuPosition={actionMenu?.index === index ? { top: actionMenu.top, left: actionMenu.left } : null}
                onUpdate={(updates) => updateRow(index, updates)}
                onIndent={(direction) => indentRow(index, direction)}
                onInsert={() => insertRow(index)}
                onDuplicate={() => duplicateRow(index)}
                onRemove={() => removeRow(index)}
                onToggleMenu={(button) => {
                  if (actionMenu?.index === index) {
                    setActionMenu(null)
                    return
                  }
                  setActionMenu({ index, ...getMenuPosition(button, 204) })
                  setAddMenu(null)
                }}
                onCloseMenu={() => setActionMenu(null)}
                onDragStart={() => setDragIndex(index)}
                onDragOver={() => setDragOverIndex(index)}
                onDragLeave={() => setDragOverIndex(null)}
                onDrop={() => {
                  if (dragIndex !== null) moveRow(dragIndex, index)
                }}
              />
            ))}
            <TcsAddRow
              menuOpen={Boolean(addMenu)}
              menuPosition={addMenu}
              onToggleMenu={(button) => {
                if (addMenu) {
                  setAddMenu(null)
                  return
                }
                setAddMenu(getMenuPosition(button, 124))
                setActionMenu(null)
              }}
              onAdd={addRow}
            />
          </div>
        </div>
      </div>
    </section>
  )
}

function TcsAddRow({
  menuOpen,
  menuPosition,
  onToggleMenu,
  onAdd,
}: {
  menuOpen: boolean
  menuPosition: { top: number; left: number } | null
  onToggleMenu: (button: HTMLButtonElement) => void
  onAdd: (type: TcsRowType) => void
}) {
  return (
    <div className="grid grid-cols-[15rem_minmax(18rem,1fr)_minmax(18rem,1fr)_4rem] min-h-[2.5rem] bg-muted/20">
      <div className="border-r border-border/70 px-3 py-1.5">
        <button
          type="button"
          onClick={(event) => onToggleMenu(event.currentTarget)}
          className="flex h-7 w-7 items-center justify-center border border-border text-muted-foreground hover:border-primary/40 hover:bg-accent hover:text-foreground"
          title="Add row"
        >
          <Plus className="h-4 w-4" />
        </button>
        {menuOpen && menuPosition && (
          <div className="fixed z-[100] w-44 border border-border bg-card shadow-elegant" style={{ top: menuPosition.top, left: menuPosition.left }}>
            {TCS_ROW_TYPE_OPTIONS.map((option) => (
              <MenuAction
                key={option.value}
                icon={<Plus className="h-3.5 w-3.5" />}
                label={ROW_TYPE_STYLES[option.value].label}
                onClick={() => onAdd(option.value)}
              />
            ))}
          </div>
        )}
      </div>
      <div className="border-r border-border/70" />
      <div className="border-r border-border/70" />
      <div />
    </div>
  )
}

function TcsEditorRow({
  row,
  hasChildren,
  isDragTarget,
  menuOpen,
  menuPosition,
  onUpdate,
  onIndent,
  onInsert,
  onDuplicate,
  onRemove,
  onToggleMenu,
  onCloseMenu,
  onDragStart,
  onDragOver,
  onDragLeave,
  onDrop,
}: {
  row: TcsRow
  hasChildren: boolean
  isDragTarget: boolean
  menuOpen: boolean
  menuPosition: { top: number; left: number } | null
  onUpdate: (updates: Partial<TcsRow>) => void
  onIndent: (direction: 'increase' | 'decrease') => void
  onInsert: () => void
  onDuplicate: () => void
  onRemove: () => void
  onToggleMenu: (button: HTMLButtonElement) => void
  onCloseMenu: () => void
  onDragStart: () => void
  onDragOver: () => void
  onDragLeave: () => void
  onDrop: () => void
}) {
  const styles = ROW_TYPE_STYLES[row.row_type]

  return (
    <div
      className={`group grid grid-cols-[15rem_minmax(18rem,1fr)_minmax(18rem,1fr)_4rem] min-h-[5.25rem] ${styles.row} ${isDragTarget ? 'bg-primary/10' : ''}`}
      draggable
      onDragStart={onDragStart}
      onDragOver={(event) => {
        event.preventDefault()
        onDragOver()
      }}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
    >
      <div className="border-r border-border/70 px-3 py-3">
        <div className="space-y-2" style={{ paddingLeft: `${row.indent_level * 18}px` }}>
          <div className="flex items-center gap-2">
            <GripVertical className="h-4 w-4 shrink-0 text-muted-foreground/50" />
            <span className={`h-7 w-1 rounded-full ${styles.marker}`} />
            {row.row_type === 'loop' && hasChildren && (
              <button
                type="button"
                onClick={() => onUpdate({ collapsed: !row.collapsed })}
                className="flex h-7 w-7 items-center justify-center text-muted-foreground hover:bg-accent"
                title={row.collapsed ? 'Expand loop' : 'Collapse loop'}
              >
                {row.collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </button>
            )}
            <select
              value={row.row_type}
              onChange={(event) => {
                const rowType = event.target.value as TcsRowType
                onUpdate({
                  row_type: rowType,
                  label: TCS_ROW_TYPE_OPTIONS.find((option) => option.value === rowType)?.label || rowType,
                })
              }}
              className={`h-7 min-w-0 flex-1 border px-2 text-xs font-semibold outline-none focus:ring-1 focus:ring-ring ${styles.chip}`}
            >
              {TCS_ROW_TYPE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="border-r border-border/70 p-2">
        <textarea
          value={row.description}
          onChange={(event) => onUpdate({ description: event.target.value })}
          className="min-h-[4rem] w-full resize-y border-0 bg-transparent px-2 py-1 text-sm text-foreground outline-none placeholder:text-muted-foreground/60 focus:bg-background focus:ring-1 focus:ring-ring"
          placeholder={row.row_type === 'loop' ? 'Loop condition or group intent' : 'Action / description'}
        />
      </div>

      <div className="border-r border-border/70 p-2">
        <textarea
          value={row.expected_result}
          onChange={(event) => onUpdate({ expected_result: event.target.value })}
          className="min-h-[4rem] w-full resize-y border-0 bg-transparent px-2 py-1 text-sm text-foreground outline-none placeholder:text-muted-foreground/60 focus:bg-background focus:ring-1 focus:ring-ring"
          placeholder="Expected result"
        />
      </div>

      <div className="px-2 py-3">
        <div className="relative flex justify-end">
          <button
            type="button"
            onClick={(event) => onToggleMenu(event.currentTarget)}
            className="flex h-8 w-8 items-center justify-center border border-transparent text-muted-foreground hover:bg-accent hover:text-foreground"
            title="Row actions"
          >
            <MoreHorizontal className="h-4 w-4" />
          </button>
          {menuOpen && menuPosition && (
            <div className="fixed z-[100] w-44 border border-border bg-card shadow-elegant" style={{ top: menuPosition.top, left: menuPosition.left }}>
              <MenuAction icon={<Plus className="h-3.5 w-3.5" />} label="Insert below" onClick={() => { onInsert(); onCloseMenu() }} />
              <MenuAction icon={<Copy className="h-3.5 w-3.5" />} label="Duplicate" onClick={() => { onDuplicate(); onCloseMenu() }} />
              <MenuAction icon={<Outdent className="h-3.5 w-3.5" />} label="Outdent" onClick={() => { onIndent('decrease'); onCloseMenu() }} />
              <MenuAction icon={<Indent className="h-3.5 w-3.5" />} label="Indent" onClick={() => { onIndent('increase'); onCloseMenu() }} />
              <MenuAction icon={<Trash2 className="h-3.5 w-3.5" />} label="Delete" destructive onClick={() => { onRemove(); onCloseMenu() }} />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function MenuAction({
  icon,
  label,
  destructive = false,
  onClick,
}: {
  icon: ReactNode
  label: string
  destructive?: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-accent ${destructive ? 'text-destructive' : 'text-foreground'}`}
    >
      {icon}
      {label}
    </button>
  )
}
