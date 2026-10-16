import SelectField from './SelectField'
import UserIdentity from './UserIdentity'
import { parameterKeyHref } from '../utils/parameters'
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
import MentionTextarea from './editor/MentionTextarea'
import type { MentionSuggestion } from './editor/MentionList'
import { MenuAction, RowMenu, type MenuPosition } from './RowMenu'

const ROW_TYPE_STYLES: Record<TcsRowType, { marker: string; chip: string; row: string; label: string }> = {
  precondition: {
    marker: 'bg-sky-500',
    chip: 'border-sky-200 bg-sky-50 text-sky-700 dark:border-sky-800 dark:bg-sky-950/30 dark:text-sky-300',
    row: 'bg-sky-500/2.5',
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
    row: 'bg-amber-500/6',
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
  mentionItems?: MentionSuggestion[]
  userMentionItems?: MentionSuggestion[]
  /** Where a `{{parameter}}` in a step should take the reader. */
  parameterHref?: string
  /** Parameter and variable values by key; a step shows the value of each reference. */
  parameterValues?: Record<string, string>
}

export function TcsArteTable({
  rows,
  onChange,
  editable = false,
  mentionItems = [],
  userMentionItems = [],
  parameterHref,
  parameterValues,
}: TcsArteTableProps) {
  if (editable) {
    return (
      <TcsArteTableEditor
        rows={rows}
        onChange={onChange}
        mentionItems={mentionItems}
        userMentionItems={userMentionItems}
      />
    )
  }
  return <TcsArteTableView people={userMentionItems} rows={rows} parameterHref={parameterHref} parameterValues={parameterValues} />
}

/**
 * Split a step's text so its `{{parameter}}` references come out as links.
 *
 * A step stores plain text, so a reference here is only a run of characters -
 * there is no node to hang a link on the way the rich editor has. Reading a
 * step, "{{BOOT_BUDGET_MS}}" says nothing about what the budget actually is,
 * so each reference becomes a link to the screen that owns the value.
 */
function withUserPictures(text: string, people: MentionSuggestion[]): ReactNode {
  const unique = people.filter(person => person.user?.profile_picture_url && people.filter(other => other.label === person.label).length === 1)
  const labels = unique.map(person => person.label).sort((a, b) => b.length - a.length)
  if (!labels.length || !text.includes('@')) return text
  const pattern = new RegExp(`@(${labels.map(label => label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})(?![\\w])`, 'g')
  const output: ReactNode[] = []
  let start = 0
  for (const match of text.matchAll(pattern)) {
    output.push(text.slice(start, match.index))
    const person = unique.find(candidate => candidate.label === match[1])
    output.push(<UserIdentity key={match.index} user={person!.user!} prefix="@" pictureClassName="w-5 h-5" />)
    start = match.index! + match[0].length
  }
  output.push(text.slice(start))
  return output
}

function withParameterLinks(text: string, href?: string, values?: Record<string, string>, people: MentionSuggestion[] = []): ReactNode {
  if (!text.includes('{{') || (!href && !values)) return withUserPictures(text, people)
  return text.split(/(\{\{[^{}\n]+\}\})/g).map((part, index) => {
    if (!/^\{\{[^{}\n]+\}\}$/.test(part)) return withUserPictures(part, people)
    const key = part.slice(2, -2)
    const shown = values?.[key] || part
    const title = values?.[key] ? part : `Open parameter ${key}`
    return href ? (
      <a key={index} href={parameterKeyHref(href, key)} className="mention" title={title}>
        {shown}
      </a>
    ) : (
      <span key={index} className="mention" title={title}>
        {shown}
      </span>
    )
  })
}

function TcsArteTableView({ rows, parameterHref, parameterValues, people }: Readonly<{ rows: TcsRow[]; parameterHref?: string; parameterValues?: Record<string, string>; people: MentionSuggestion[] }>) {
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
              <TcsViewRow key={row.id} row={row} people={people} parameterHref={parameterHref} parameterValues={parameterValues} hasChildren={hasChildRows(rows, rows.findIndex((candidate) => candidate.id === row.id))} />
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

function TcsViewRow({ row, hasChildren, parameterHref, parameterValues, people }: Readonly<{ row: TcsRow; hasChildren: boolean; parameterHref?: string; parameterValues?: Record<string, string>; people: MentionSuggestion[] }>) {
  const styles = ROW_TYPE_STYLES[row.row_type]
  const isLoop = row.row_type === 'loop'

  return (
    <div className={`grid grid-cols-[14rem_minmax(18rem,1fr)_minmax(18rem,1fr)] min-h-16 ${styles.row}`}>
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
        {row.description
          ? withParameterLinks(row.description, parameterHref, parameterValues, people)
          : <span className="text-muted-foreground">-</span>}
      </div>
      <div className="px-4 py-3 text-sm text-foreground whitespace-pre-wrap">
        {row.expected_result
          ? withParameterLinks(row.expected_result, parameterHref, parameterValues, people)
          : <span className="text-muted-foreground">-</span>}
      </div>
    </div>
  )
}

function TcsArteTableEditor({
  rows,
  onChange,
  mentionItems,
  userMentionItems,
}: {
  rows: TcsRow[]
  onChange: (rows: TcsRow[]) => void
  mentionItems: MentionSuggestion[]
  userMentionItems: MentionSuggestion[]
}) {
  const [dragIndex, setDragIndex] = useState<number | null>(null)
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null)
  const [actionMenu, setActionMenu] = useState<{ index: number; top: number; left: number } | null>(null)
  const [addMenu, setAddMenu] = useState<MenuPosition | null>(null)
  const visibleRows = getVisibleRows(rows)

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
                mentionItems={mentionItems}
                userMentionItems={userMentionItems}
                isDragTarget={dragOverIndex === index}
                menuOpen={actionMenu?.index === index}
                menuPosition={actionMenu?.index === index ? { top: actionMenu.top, left: actionMenu.left } : null}
                onUpdate={(updates) => updateRow(index, updates)}
                onIndent={(direction) => indentRow(index, direction)}
                onInsert={() => insertRow(index)}
                onDuplicate={() => duplicateRow(index)}
                onRemove={() => removeRow(index)}
                onToggleMenu={(position) => {
                  if (actionMenu?.index === index) {
                    setActionMenu(null)
                    return
                  }
                  setActionMenu({ index, ...position })
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
              onToggleMenu={(position) => {
                if (addMenu) {
                  setAddMenu(null)
                  return
                }
                setAddMenu(position)
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
  menuPosition: MenuPosition | null
  onToggleMenu: (position: MenuPosition) => void
  onAdd: (type: TcsRowType) => void
}) {
  return (
    <div className="grid grid-cols-[15rem_minmax(18rem,1fr)_minmax(18rem,1fr)_4rem] min-h-10 bg-muted/20">
      <div className="border-r border-border/70 px-3 py-1.5">
        <RowMenu
          icon={<Plus className="h-4 w-4" />}
          title="Add row"
          buttonClassName="flex h-7 w-7 items-center justify-center border border-border text-muted-foreground hover:border-primary/40 hover:bg-accent hover:text-foreground"
          menuHeight={124}
          open={menuOpen}
          position={menuPosition}
          onToggle={onToggleMenu}
        >
          {TCS_ROW_TYPE_OPTIONS.map((option) => (
            <MenuAction
              key={option.value}
              icon={<Plus className="h-3.5 w-3.5" />}
              label={ROW_TYPE_STYLES[option.value].label}
              onClick={() => onAdd(option.value)}
            />
          ))}
        </RowMenu>
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
  mentionItems,
  userMentionItems,
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
  mentionItems: MentionSuggestion[]
  userMentionItems: MentionSuggestion[]
  isDragTarget: boolean
  menuOpen: boolean
  menuPosition: MenuPosition | null
  onUpdate: (updates: Partial<TcsRow>) => void
  onIndent: (direction: 'increase' | 'decrease') => void
  onInsert: () => void
  onDuplicate: () => void
  onRemove: () => void
  onToggleMenu: (position: MenuPosition) => void
  onCloseMenu: () => void
  onDragStart: () => void
  onDragOver: () => void
  onDragLeave: () => void
  onDrop: () => void
}) {
  const styles = ROW_TYPE_STYLES[row.row_type]

  return (
    <div
      className={`group grid grid-cols-[15rem_minmax(18rem,1fr)_minmax(18rem,1fr)_4rem] min-h-21 ${styles.row} ${isDragTarget ? 'bg-primary/10' : ''}`}
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
            <SelectField
              value={row.row_type}
              onChange={(event) => {
                const rowType = event.target.value as TcsRowType
                onUpdate({
                  row_type: rowType,
                  label: TCS_ROW_TYPE_OPTIONS.find((option) => option.value === rowType)?.label || rowType,
                })
              }}
              className={`h-7 min-w-0 flex-1 border px-2 text-xs font-semibold outline-hidden focus:ring-1 focus:ring-ring ${styles.chip}`}
            >
              {TCS_ROW_TYPE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>{option.label}</option>
              ))}
            </SelectField>
          </div>
        </div>
      </div>

      <div className="border-r border-border/70 p-2">
        <MentionTextarea
          value={row.description}
          onChange={(description) => onUpdate({ description })}
          mentionItems={mentionItems}
          userMentionItems={userMentionItems}
          className="min-h-16 w-full resize-y border-0 bg-transparent px-2 py-1 text-sm text-foreground outline-hidden placeholder:text-muted-foreground/60 focus:bg-background focus:ring-1 focus:ring-ring"
          placeholder={row.row_type === 'loop' ? 'Loop condition or group intent' : 'Action / description'}
        />
      </div>

      <div className="border-r border-border/70 p-2">
        <MentionTextarea
          value={row.expected_result}
          onChange={(expected_result) => onUpdate({ expected_result })}
          mentionItems={mentionItems}
          userMentionItems={userMentionItems}
          className="min-h-16 w-full resize-y border-0 bg-transparent px-2 py-1 text-sm text-foreground outline-hidden placeholder:text-muted-foreground/60 focus:bg-background focus:ring-1 focus:ring-ring"
          placeholder="Expected result"
        />
      </div>

      <div className="px-2 py-3">
        <div className="relative flex justify-end">
          <RowMenu
            icon={<MoreHorizontal className="h-4 w-4" />}
            title="Row actions"
            buttonClassName="flex h-8 w-8 items-center justify-center border border-transparent text-muted-foreground hover:bg-accent hover:text-foreground"
            menuHeight={204}
            open={menuOpen}
            position={menuPosition}
            onToggle={onToggleMenu}
          >
            <MenuAction icon={<Plus className="h-3.5 w-3.5" />} label="Insert below" onClick={() => { onInsert(); onCloseMenu() }} />
            <MenuAction icon={<Copy className="h-3.5 w-3.5" />} label="Duplicate" onClick={() => { onDuplicate(); onCloseMenu() }} />
            <MenuAction icon={<Outdent className="h-3.5 w-3.5" />} label="Outdent" onClick={() => { onIndent('decrease'); onCloseMenu() }} />
            <MenuAction icon={<Indent className="h-3.5 w-3.5" />} label="Indent" onClick={() => { onIndent('increase'); onCloseMenu() }} />
            <MenuAction icon={<Trash2 className="h-3.5 w-3.5" />} label="Delete" destructive onClick={() => { onRemove(); onCloseMenu() }} />
          </RowMenu>
        </div>
      </div>
    </div>
  )
}
