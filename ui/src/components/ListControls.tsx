import type { Dispatch, ReactNode, SetStateAction } from 'react'
import { ArrowUpDown, ChevronDown, ChevronUp, Filter } from 'lucide-react'

interface SortableHeaderProps<F extends string> {
  field: F
  sortField: F
  sortDir: string
  onSort: (field: F) => void
  className: string
  children: ReactNode
}

/** A table header that sorts by its field on click and shows the current direction. */
export function SortableHeader<F extends string>({
  field,
  sortField,
  sortDir,
  onSort,
  className,
  children,
}: SortableHeaderProps<F>) {
  return (
    <th className={className} onClick={() => onSort(field)}>
      <div className="flex items-center gap-1">
        {children}
        {sortField === field ? (
          sortDir === 'asc' ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />
        ) : (
          <ArrowUpDown className="h-3 w-3 opacity-30" />
        )}
      </div>
    </th>
  )
}

interface PagerProps {
  page: number
  totalPages: number
  setPage: Dispatch<SetStateAction<number>>
}

/** Previous and next buttons around the current page number. */
export function Pager({ page, totalPages, setPage }: PagerProps) {
  return (
    <div className="flex items-center gap-2">
      <button
        disabled={page === 0}
        onClick={() => setPage((p) => p - 1)}
        className="px-3 py-1 border border-border rounded hover:bg-accent/50 disabled:opacity-30 disabled:cursor-not-allowed"
      >
        Prev
      </button>
      <span className="px-2 text-muted-foreground">
        {page + 1} / {totalPages || 1}
      </span>
      <button
        disabled={page >= totalPages - 1}
        onClick={() => setPage((p) => p + 1)}
        className="px-3 py-1 border border-border rounded hover:bg-accent/50 disabled:opacity-30 disabled:cursor-not-allowed"
      >
        Next
      </button>
    </div>
  )
}

interface FiltersToggleProps {
  open: boolean
  active: boolean
  onToggle: () => void
  controls: string
}

/** The button that opens the filter panel and marks when a filter is on. */
export function FiltersToggle({ open, active, onToggle, controls }: FiltersToggleProps) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className={`inline-flex items-center justify-center gap-2 rounded-md border px-2.5 py-1.5 text-sm font-medium transition-colors ${
        open || active
          ? 'border-primary bg-primary/10 text-primary'
          : 'border-input bg-background text-foreground hover:bg-accent'
      }`}
      aria-expanded={open}
      aria-controls={controls}
    >
      <Filter className="h-4 w-4" />
      Filters
      {active && (
        <span className="rounded bg-primary px-1.5 py-0.5 text-[10px] font-semibold text-primary-foreground">On</span>
      )}
    </button>
  )
}

/** One active filter, shown as a chip. */
export function FilterChip({ label, muted = false }: { label: string; muted?: boolean }) {
  return (
    <span className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs ${muted ? 'border-border text-muted-foreground' : 'border-primary/20 bg-primary/10 text-primary'}`}>
      {label}
    </span>
  )
}
