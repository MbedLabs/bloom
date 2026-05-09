import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { format } from 'date-fns'
import {
  ArrowUpDown,
  BookOpen,
  Calendar,
  ChevronDown,
  ChevronUp,
  Filter,
  Plus,
  Search,
  Upload,
  X,
} from 'lucide-react'

import { docsApi, type DocShell, usersApi } from '../api/client'
import { useProjectByPrefix } from '../hooks/useProjectByPrefix'
import { docCreateUrl, docUrl, normalizeDocTypeParam, type DocType } from '../types/doc'
import { formatDateTime } from '../test/date-utils'

const TYPE_BADGES: Record<DocType, { label: string; color: string }> = {
  REQ: { label: 'Requirement', color: 'bg-amber-500/10 text-amber-700 dark:text-amber-400' },
  SPEC: { label: 'Specification', color: 'bg-indigo-500/10 text-indigo-700 dark:text-indigo-400' },
  TC: { label: 'Test Case', color: 'bg-cyan-500/10 text-cyan-700 dark:text-cyan-400' },
  DES: { label: 'Design', color: 'bg-violet-500/10 text-violet-700 dark:text-violet-400' },
  RSK: { label: 'Risk', color: 'bg-red-500/10 text-red-700 dark:text-red-400' },
  CHG: { label: 'Change Request', color: 'bg-blue-500/10 text-blue-700 dark:text-blue-400' },
  TCO: { label: 'Test Concept', color: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400' },
  DEF: { label: 'Defect', color: 'bg-rose-500/10 text-rose-700 dark:text-rose-400' },
  CMP: { label: 'Campaign', color: 'bg-sky-500/10 text-sky-700 dark:text-sky-400' },
  PROT: { label: 'Protocol', color: 'bg-teal-500/10 text-teal-700 dark:text-teal-400' },
  RPT: { label: 'Report', color: 'bg-slate-500/10 text-slate-700 dark:text-slate-400' },
  STD: { label: 'External Standard', color: 'bg-orange-500/10 text-orange-700 dark:text-orange-400' },
}

const DOC_TYPE_OPTIONS: { code: DocType; label: string }[] = [
  { code: 'REQ', label: 'Requirements' },
  { code: 'SPEC', label: 'Specifications' },
  { code: 'TC', label: 'Test Cases' },
  { code: 'TCO', label: 'Test Concepts' },
  { code: 'PROT', label: 'Protocols' },
  { code: 'DES', label: 'Design' },
  { code: 'RSK', label: 'Risks' },
  { code: 'CHG', label: 'Changes' },
  { code: 'RPT', label: 'Reports' },
  { code: 'STD', label: 'Standards' },
]

const TYPE_PAGE_TITLE: Record<DocType, string> = {
  REQ: 'Requirements',
  SPEC: 'Specifications',
  TC: 'Test Cases',
  TCO: 'Test Concepts',
  DEF: 'Defects',
  CMP: 'Campaigns',
  PROT: 'Protocols',
  DES: 'Design Items',
  RSK: 'Risks',
  CHG: 'Changes',
  RPT: 'Reports',
  STD: 'Standards',
}

const STATUS_OPTIONS = [
  'Draft',
  'Review',
  'Approved',
  'Rejected',
  'Obsolete',
  'Open',
  'Mitigated',
  'Submitted',
  'Implemented',
  'Active',
  'Final',
  'Superseded',
]

const PRIORITY_OPTIONS = ['Low', 'Medium', 'High', 'Critical']

const LINK_FILTER_OPTIONS = [
  { code: '', label: 'Any link state' },
  { code: 'linked', label: 'Has any links' },
  { code: 'unlinked', label: 'No links' },
  { code: 'incoming', label: 'Has incoming links' },
  { code: 'outgoing', label: 'Has outgoing links' },
  { code: 'suspect', label: 'Has suspect links' },
  { code: 'clean', label: 'No suspect links' },
] as const

type LinkFilter = typeof LINK_FILTER_OPTIONS[number]['code']
type SortField =
  | 'updated_at'
  | 'created_at'
  | 'doc_id'
  | 'doc_type'
  | 'status'
  | 'title'
  | 'priority'
  | 'reviewer'
type SortDir = 'asc' | 'desc'

const SORT_OPTIONS: { field: SortField; label: string }[] = [
  { field: 'updated_at', label: 'Updated Time' },
  { field: 'created_at', label: 'Created Time' },
  { field: 'doc_id', label: 'ID' },
  { field: 'doc_type', label: 'Kind' },
  { field: 'status', label: 'Status' },
  { field: 'title', label: 'Name / Title' },
  { field: 'priority', label: 'Priority' },
  { field: 'reviewer', label: 'Reviewer' },
]

function isDocType(value: string): value is DocType {
  return DOC_TYPE_OPTIONS.some((option) => option.code === value)
}

function isSortField(value: string | null): value is SortField {
  return SORT_OPTIONS.some((option) => option.field === value)
}

function isLinkFilter(value: string | null): value is LinkFilter {
  return LINK_FILTER_OPTIONS.some((option) => option.code === value)
}

function unique<T>(values: T[]): T[] {
  return Array.from(new Set(values))
}

function readListParam(params: URLSearchParams, key: string): string[] {
  return unique(
    params
      .getAll(key)
      .flatMap((value) => value.split(','))
      .map((value) => value.trim())
      .filter(Boolean)
  )
}

function writeListParam(params: URLSearchParams, key: string, values: string[]) {
  params.delete(key)
  values.forEach((value) => params.append(key, value))
}

function TypeBadge({ type }: { type: string }) {
  const cfg = isDocType(type) ? TYPE_BADGES[type] : { label: type, color: 'bg-muted text-muted-foreground' }
  return <span className={`px-2 py-0.5 rounded-md text-[11px] font-semibold ${cfg.color}`}>{cfg.label}</span>
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    Draft: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
    Review: 'bg-blue-500/10 text-blue-700 dark:text-blue-400',
    Approved: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
    Active: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
    Open: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
    Submitted: 'bg-blue-500/10 text-blue-700 dark:text-blue-400',
    Implemented: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
    Mitigated: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
    Final: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
    Obsolete: 'bg-muted text-muted-foreground',
    Rejected: 'bg-red-500/10 text-red-700 dark:text-red-400',
    Superseded: 'bg-muted text-muted-foreground',
  }
  return <span className={`px-2 py-0.5 rounded-md text-[11px] font-semibold ${colors[status] || 'bg-muted text-muted-foreground'}`}>{status}</span>
}

function ExecutionBadge({ status }: { status: string | null }) {
  if (!status) {
    return <span className="px-2 py-1 rounded-full text-xs font-medium bg-muted text-muted-foreground">Not executed</span>
  }
  const colors: Record<string, string> = {
    Passed: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
    Failed: 'bg-red-500/10 text-red-700 dark:text-red-400',
    Skipped: 'bg-slate-500/10 text-slate-700 dark:text-slate-400',
  }
  return <span className={`px-2 py-1 rounded-full text-xs font-medium ${colors[status] || 'bg-muted text-muted-foreground'}`}>{status}</span>
}

export default function Documents() {
  const { prefix } = useParams<{ prefix: string }>()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const { data: project } = useProjectByPrefix(prefix)
  const [createMenuOpen, setCreateMenuOpen] = useState(false)
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  useEffect(() => {
    const sortFromUrl = searchParams.get('sort')
    if (!searchParams.has('dir') && (!sortFromUrl || isSortField(sortFromUrl))) return
    const params = new URLSearchParams(searchParams)
    params.delete('dir')
    if (sortFromUrl && !isSortField(sortFromUrl)) params.delete('sort')
    setSearchParams(params, { replace: true })
  }, [searchParams, setSearchParams])

  const typeFilters = useMemo(
    () => unique(readListParam(searchParams, 'type').map((value) => normalizeDocTypeParam(value)).filter(Boolean) as DocType[]),
    [searchParams]
  )
  const statusFilters = useMemo(() => readListParam(searchParams, 'status'), [searchParams])
  const search = searchParams.get('q') || ''
  const priorityFilter = searchParams.get('priority') || ''
  const reviewerFilter = searchParams.get('reviewer') || ''
  const linkParam = searchParams.get('links')
  const linkFilter: LinkFilter = isLinkFilter(linkParam) ? linkParam : ''
  const createdFrom = searchParams.get('created_from') || ''
  const createdTo = searchParams.get('created_to') || ''
  const updatedFrom = searchParams.get('updated_from') || ''
  const updatedTo = searchParams.get('updated_to') || ''
  const sortParam = searchParams.get('sort')
  const sortField: SortField = isSortField(sortParam) ? sortParam : 'updated_at'
  const pageTitle = typeFilters.length === 1 ? TYPE_PAGE_TITLE[typeFilters[0]] : 'Documents'
  const showExecColumn = typeFilters.length === 0 || typeFilters.includes('TC')

  const { data: docs, isLoading } = useQuery({
    queryKey: ['all-docs', prefix, typeFilters],
    queryFn: () => docsApi.list(prefix!, {
      type: typeFilters.length > 0 ? typeFilters : undefined,
      includeLinkCounts: true,
    }),
    enabled: !!prefix,
  })

  const { data: users } = useQuery({
    queryKey: ['users'],
    queryFn: usersApi.list,
  })

  const userMap = useMemo(() => {
    const m = new Map<number, string>()
    users?.forEach((user) => m.set(user.id, user.full_name))
    return m
  }, [users])

  const updateRegistryParams = (next: {
    types?: DocType[]
    statuses?: string[]
    q?: string
    priority?: string
    reviewer?: string
    links?: LinkFilter
    createdFrom?: string
    createdTo?: string
    updatedFrom?: string
    updatedTo?: string
    sort?: SortField
  }) => {
    const params = new URLSearchParams(searchParams)
    const nextTypes = next.types ?? typeFilters
    const nextStatuses = next.statuses ?? statusFilters
    const nextQuery = next.q ?? search
    const nextPriority = next.priority ?? priorityFilter
    const nextReviewer = next.reviewer ?? reviewerFilter
    const nextLinks = next.links ?? linkFilter
    const nextCreatedFrom = next.createdFrom ?? createdFrom
    const nextCreatedTo = next.createdTo ?? createdTo
    const nextUpdatedFrom = next.updatedFrom ?? updatedFrom
    const nextUpdatedTo = next.updatedTo ?? updatedTo
    const nextSort = next.sort ?? sortField

    writeListParam(params, 'type', nextTypes)
    writeListParam(params, 'status', nextStatuses)

    if (nextQuery.trim()) params.set('q', nextQuery)
    else params.delete('q')

    if (nextPriority) params.set('priority', nextPriority)
    else params.delete('priority')

    if (nextReviewer) params.set('reviewer', nextReviewer)
    else params.delete('reviewer')

    if (nextLinks) params.set('links', nextLinks)
    else params.delete('links')

    if (nextCreatedFrom) params.set('created_from', nextCreatedFrom)
    else params.delete('created_from')

    if (nextCreatedTo) params.set('created_to', nextCreatedTo)
    else params.delete('created_to')

    if (nextUpdatedFrom) params.set('updated_from', nextUpdatedFrom)
    else params.delete('updated_from')

    if (nextUpdatedTo) params.set('updated_to', nextUpdatedTo)
    else params.delete('updated_to')

    if (nextSort !== 'updated_at') params.set('sort', nextSort)
    else params.delete('sort')

    params.delete('dir')

    setSearchParams(params, { replace: true })
  }

  const clearFilters = () => {
    const params = new URLSearchParams(searchParams)
    ;['type', 'status', 'q', 'priority', 'reviewer', 'links', 'created_from', 'created_to', 'updated_from', 'updated_to', 'sort', 'dir'].forEach((key) => params.delete(key))
    setSearchParams(params, { replace: true })
  }

  const toggleType = (type: DocType) => {
    updateRegistryParams({
      types: typeFilters.includes(type)
        ? typeFilters.filter((value) => value !== type)
        : [...typeFilters, type],
    })
  }

  const toggleStatus = (status: string) => {
    updateRegistryParams({
      statuses: statusFilters.includes(status)
        ? statusFilters.filter((value) => value !== status)
        : [...statusFilters, status],
    })
  }

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir((current) => current === 'asc' ? 'desc' : 'asc')
    } else {
      setSortDir(field === 'updated_at' || field === 'created_at' ? 'desc' : 'asc')
      updateRegistryParams({ sort: field })
    }
  }

  const filtered = useMemo(() => {
    let result = docs || []

    if (search.trim()) {
      const query = search.toLowerCase()
      result = result.filter((doc) => {
        const reviewerName = doc.reviewer_id ? userMap.get(doc.reviewer_id) || '' : ''
        const kindLabel = isDocType(doc.doc_type) ? TYPE_BADGES[doc.doc_type].label : doc.doc_type
        const searchable = [
          doc.doc_id,
          doc.title,
          doc.doc_type,
          kindLabel,
          doc.status,
          doc.priority || '',
          reviewerName,
          format(new Date(doc.created_at), 'yyyy-MM-dd MMM d yyyy'),
          format(new Date(doc.updated_at), 'yyyy-MM-dd MMM d yyyy'),
        ].join(' ').toLowerCase()
        return searchable.includes(query)
      })
    }

    if (statusFilters.length > 0) {
      result = result.filter((doc) => statusFilters.includes(doc.status))
    }

    if (priorityFilter) {
      result = result.filter((doc) => (doc.priority || '') === priorityFilter)
    }

    if (reviewerFilter === 'assigned') {
      result = result.filter((doc) => doc.reviewer_id !== null)
    } else if (reviewerFilter === 'unassigned') {
      result = result.filter((doc) => doc.reviewer_id === null)
    } else if (reviewerFilter) {
      result = result.filter((doc) => String(doc.reviewer_id || '') === reviewerFilter)
    }

    if (linkFilter === 'linked') {
      result = result.filter((doc) => doc.incoming_links + doc.outgoing_links > 0)
    } else if (linkFilter === 'unlinked') {
      result = result.filter((doc) => doc.incoming_links + doc.outgoing_links === 0)
    } else if (linkFilter === 'incoming') {
      result = result.filter((doc) => doc.incoming_links > 0)
    } else if (linkFilter === 'outgoing') {
      result = result.filter((doc) => doc.outgoing_links > 0)
    } else if (linkFilter === 'suspect') {
      result = result.filter((doc) => doc.suspect_links > 0)
    } else if (linkFilter === 'clean') {
      result = result.filter((doc) => doc.suspect_links === 0)
    }

    if (createdFrom) {
      const from = new Date(`${createdFrom}T00:00:00`).getTime()
      result = result.filter((doc) => new Date(doc.created_at).getTime() >= from)
    }

    if (createdTo) {
      const to = new Date(`${createdTo}T23:59:59`).getTime()
      result = result.filter((doc) => new Date(doc.created_at).getTime() <= to)
    }

    if (updatedFrom) {
      const from = new Date(`${updatedFrom}T00:00:00`).getTime()
      result = result.filter((doc) => new Date(doc.updated_at).getTime() >= from)
    }

    if (updatedTo) {
      const to = new Date(`${updatedTo}T23:59:59`).getTime()
      result = result.filter((doc) => new Date(doc.updated_at).getTime() <= to)
    }

    return result
  }, [createdFrom, createdTo, docs, linkFilter, priorityFilter, reviewerFilter, search, statusFilters, updatedFrom, updatedTo, userMap])

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      let cmp = 0
      switch (sortField) {
        case 'updated_at':
        case 'created_at':
          cmp = new Date(a[sortField]).getTime() - new Date(b[sortField]).getTime()
          break
        case 'doc_id':
        case 'doc_type':
        case 'status':
        case 'title':
          cmp = a[sortField].localeCompare(b[sortField], undefined, { numeric: true, sensitivity: 'base' })
          break
        case 'priority':
          cmp = (a.priority || '').localeCompare(b.priority || '', undefined, { sensitivity: 'base' })
          break
        case 'reviewer':
          cmp = (a.reviewer_id ? userMap.get(a.reviewer_id) || '' : '').localeCompare(
            b.reviewer_id ? userMap.get(b.reviewer_id) || '' : '',
            undefined,
            { sensitivity: 'base' }
          )
          break
      }
      return sortDir === 'asc' ? cmp : -cmp
    })
  }, [filtered, sortDir, sortField, userMap])

  const sortLabel = SORT_OPTIONS.find((option) => option.field === sortField)?.label || 'Updated'
  const hasActiveFilters = Boolean(
    typeFilters.length ||
    statusFilters.length ||
    search ||
    priorityFilter ||
    reviewerFilter ||
    linkFilter ||
    createdFrom ||
    createdTo ||
    updatedFrom ||
    updatedTo ||
    sortField !== 'updated_at'
  )
  const createTypes = typeFilters.length === 1 ? DOC_TYPE_OPTIONS.filter((type) => type.code === typeFilters[0]) : DOC_TYPE_OPTIONS
  const createButtonLabel = createTypes.length === 1 ? `New ${TYPE_BADGES[createTypes[0].code].label}` : 'New Document'
  const totalDocs = docs?.length ?? 0

  const SortHeader = ({ field, children, compact = false }: { field: SortField; children: React.ReactNode; compact?: boolean }) => (
    <th
      className={`${compact ? 'px-4' : 'px-6'} py-3 text-left text-xs font-medium text-muted-foreground uppercase cursor-pointer select-none hover:text-foreground transition-colors`}
      onClick={() => toggleSort(field)}
    >
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

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
            <Link to={`/projects/${prefix}`} className="hover:text-primary transition-colors">
              {project?.name || prefix}
            </Link>
            <span>/</span>
            <span className="text-foreground">{pageTitle}</span>
          </div>
          <h2 className="text-xl font-bold text-foreground">{pageTitle}</h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            {sorted.length} of {totalDocs} controlled item{totalDocs !== 1 ? 's' : ''} shown
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            to={`/projects/${prefix}/import`}
            className="inline-flex items-center gap-2 px-3 py-2 border border-input bg-background text-foreground rounded-md text-sm font-medium hover:bg-accent transition-colors"
          >
            <Upload className="h-4 w-4" />
            Import
          </Link>
          <div className="relative">
            <button
              onClick={() => setCreateMenuOpen((open) => !open)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-all"
            >
              <Plus className="h-4 w-4" />
              {createButtonLabel}
              <ChevronDown className={`h-4 w-4 transition-transform ${createMenuOpen ? 'rotate-180' : ''}`} />
            </button>
            {createMenuOpen && (
              <div className="absolute right-0 top-full z-20 mt-2 w-56 overflow-hidden rounded-lg border border-border bg-card shadow-elegant">
                {createTypes.map((type) => (
                  <button
                    key={type.code}
                    onClick={() => {
                      setCreateMenuOpen(false)
                      navigate(docCreateUrl(prefix!, type.code))
                    }}
                    className="flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm hover:bg-accent"
                  >
                    <span>New {TYPE_BADGES[type.code].label}</span>
                    <span className={`rounded px-1.5 py-0.5 text-[10px] font-semibold ${TYPE_BADGES[type.code].color}`}>{type.code}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <section className="rounded-lg border border-border bg-card">
        <div className="grid grid-cols-1 gap-3 border-b border-border p-4 xl:grid-cols-[minmax(260px,1fr)_220px_auto]">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              placeholder="Search name, ID, kind, status, reviewer, dates, links..."
              value={search}
              onChange={(event) => updateRegistryParams({ q: event.target.value })}
              className="w-full rounded-md border border-input bg-background py-2 pl-9 pr-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring"
            />
          </div>
          <select
            value={sortField}
            onChange={(event) => {
              const nextSort = event.target.value as SortField
              setSortDir(nextSort === 'updated_at' || nextSort === 'created_at' ? 'desc' : 'asc')
              updateRegistryParams({ sort: nextSort })
            }}
            className="rounded-md border border-input bg-background px-3 py-2 text-sm"
          >
            {SORT_OPTIONS.map((option) => (
              <option key={option.field} value={option.field}>Sort by {option.label}</option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => setFiltersOpen((open) => !open)}
            className={`inline-flex items-center justify-center gap-2 rounded-md border px-3 py-2 text-sm font-medium transition-colors ${
              filtersOpen || hasActiveFilters
                ? 'border-primary bg-primary/10 text-primary'
                : 'border-input bg-background text-foreground hover:bg-accent'
            }`}
            aria-expanded={filtersOpen}
            aria-controls="documents-filter-panel"
          >
            <Filter className="h-4 w-4" />
            Filters
            {hasActiveFilters && (
              <span className="rounded bg-primary px-1.5 py-0.5 text-[10px] font-semibold text-primary-foreground">On</span>
            )}
          </button>
        </div>

        {filtersOpen && (
        <div id="documents-filter-panel" className="space-y-4 p-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
            <Filter className="h-4 w-4 text-primary" />
            Filters
          </div>

          <div className="space-y-2">
            <div className="text-xs font-medium uppercase text-muted-foreground">Kind</div>
            <div className="flex flex-wrap gap-2">
              {DOC_TYPE_OPTIONS.map((type) => (
                <button
                  key={type.code}
                  onClick={() => toggleType(type.code)}
                  className={`rounded-md border px-2.5 py-1.5 text-xs font-medium transition-colors ${
                    typeFilters.includes(type.code)
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-border bg-background text-muted-foreground hover:text-foreground'
                  }`}
                >
                  {type.code}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <div className="text-xs font-medium uppercase text-muted-foreground">Status</div>
            <div className="flex flex-wrap gap-2">
              {STATUS_OPTIONS.map((status) => (
                <button
                  key={status}
                  onClick={() => toggleStatus(status)}
                  className={`rounded-md border px-2.5 py-1.5 text-xs font-medium transition-colors ${
                    statusFilters.includes(status)
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-border bg-background text-muted-foreground hover:text-foreground'
                  }`}
                >
                  {status}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
            <label className="space-y-1">
              <span className="text-xs font-medium uppercase text-muted-foreground">Priority / Severity</span>
              <select
                value={priorityFilter}
                onChange={(event) => updateRegistryParams({ priority: event.target.value })}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                <option value="">Any priority</option>
                {PRIORITY_OPTIONS.map((priority) => (
                  <option key={priority} value={priority}>{priority}</option>
                ))}
              </select>
            </label>

            <label className="space-y-1">
              <span className="text-xs font-medium uppercase text-muted-foreground">Reviewer</span>
              <select
                value={reviewerFilter}
                onChange={(event) => updateRegistryParams({ reviewer: event.target.value })}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                <option value="">Any reviewer</option>
                <option value="assigned">Any assigned</option>
                <option value="unassigned">Unassigned</option>
                {users?.map((user) => (
                  <option key={user.id} value={user.id}>{user.full_name}</option>
                ))}
              </select>
            </label>

            <label className="space-y-1">
              <span className="text-xs font-medium uppercase text-muted-foreground">Links</span>
              <select
                value={linkFilter}
                onChange={(event) => updateRegistryParams({ links: event.target.value as LinkFilter })}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
              >
                {LINK_FILTER_OPTIONS.map((option) => (
                  <option key={option.code} value={option.code}>{option.label}</option>
                ))}
              </select>
            </label>
          </div>

          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
            <DatePickerField
              label="Created From"
              value={createdFrom}
              emptyLabel="Any start date"
              onChange={(value) => updateRegistryParams({ createdFrom: value })}
            />

            <DatePickerField
              label="Created To"
              value={createdTo}
              emptyLabel="Any end date"
              onChange={(value) => updateRegistryParams({ createdTo: value })}
            />

            <DatePickerField
              label="Updated From"
              value={updatedFrom}
              emptyLabel="Any start date"
              onChange={(value) => updateRegistryParams({ updatedFrom: value })}
            />

            <DatePickerField
              label="Updated To"
              value={updatedTo}
              emptyLabel="Any end date"
              onChange={(value) => updateRegistryParams({ updatedTo: value })}
            />
          </div>

          <div className="flex flex-wrap items-center gap-2 border-t border-border pt-3">
            <FilterChip label={`Sort: ${sortLabel}`} muted={!hasActiveFilters} />
            {search && <FilterChip label={`Search: ${search}`} />}
            {typeFilters.map((type) => <FilterChip key={type} label={`Kind: ${type}`} />)}
            {statusFilters.map((status) => <FilterChip key={status} label={`Status: ${status}`} />)}
            {priorityFilter && <FilterChip label={`Priority: ${priorityFilter}`} />}
            {reviewerFilter && <FilterChip label={`Reviewer: ${reviewerFilter === 'assigned' ? 'assigned' : reviewerFilter === 'unassigned' ? 'unassigned' : userMap.get(Number(reviewerFilter)) || reviewerFilter}`} />}
            {linkFilter && <FilterChip label={`Links: ${LINK_FILTER_OPTIONS.find((option) => option.code === linkFilter)?.label}`} />}
            {createdFrom && <FilterChip label={`Created from: ${createdFrom}`} />}
            {createdTo && <FilterChip label={`Created to: ${createdTo}`} />}
            {updatedFrom && <FilterChip label={`Updated from: ${updatedFrom}`} />}
            {updatedTo && <FilterChip label={`Updated to: ${updatedTo}`} />}
            {hasActiveFilters && (
              <button onClick={clearFilters} className="inline-flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground">
                <X className="h-3.5 w-3.5" />
                Clear all
              </button>
            )}
          </div>
        </div>
        )}
      </section>

      {isLoading ? (
        <div className="bg-card rounded-lg border border-border shadow-elegant p-8 text-center text-muted-foreground">
          Loading...
        </div>
      ) : sorted.length === 0 ? (
        <div className="bg-card rounded-lg border border-border shadow-elegant p-16 text-center">
          <div className="w-20 h-20 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-5">
            <BookOpen className="h-10 w-10 text-primary/40" />
          </div>
          <h3 className="text-lg font-semibold text-foreground mb-2">
            {hasActiveFilters ? 'No documents found' : 'No Controlled Documents Yet'}
          </h3>
          <p className="text-sm text-muted-foreground mb-5 max-w-md mx-auto">
            {hasActiveFilters ? 'Try a different filter combination.' : 'Create a Requirement, Specification, Protocol, or Test Case to get started.'}
          </p>
        </div>
      ) : (
        <div className="bg-card rounded-lg shadow-elegant overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-border">
              <thead className="bg-muted/50">
                <tr>
                  <SortHeader field="doc_id">ID</SortHeader>
                  <SortHeader field="doc_type">Kind</SortHeader>
                  <SortHeader field="title">Name / Title</SortHeader>
                  <SortHeader field="status">Status</SortHeader>
                  {showExecColumn && <SortHeader field="updated_at">Execution</SortHeader>}
                  <SortHeader field="priority" compact>Priority</SortHeader>
                  <SortHeader field="reviewer" compact>Reviewer</SortHeader>
                  <SortHeader field="created_at">Created</SortHeader>
                  <SortHeader field="updated_at">Updated</SortHeader>
                </tr>
              </thead>
              <tbody className="bg-card divide-y divide-border">
                {sorted.map((doc: DocShell) => (
                  <tr key={`${doc.doc_type}-${doc.id}`} className="hover:bg-accent/50">
                    <td className="px-6 py-3 whitespace-nowrap">
                      <Link to={docUrl(prefix!, doc.doc_type as DocType, doc.doc_id)} className="text-primary font-mono text-sm font-medium">
                        {doc.doc_id}
                      </Link>
                    </td>
                    <td className="px-6 py-3 whitespace-nowrap">
                      <TypeBadge type={doc.doc_type} />
                    </td>
                    <td className="px-6 py-3 max-w-sm truncate">
                      <Link to={docUrl(prefix!, doc.doc_type as DocType, doc.doc_id)} className="text-foreground hover:text-primary/80 font-medium">
                        {doc.title}
                      </Link>
                    </td>
                    <td className="px-6 py-3 whitespace-nowrap">
                      <StatusBadge status={doc.status} />
                    </td>
                    {showExecColumn && (
                      <td className="px-6 py-3 whitespace-nowrap">
                        {doc.doc_type === 'TC' ? (
                          <div className="space-y-1">
                            <ExecutionBadge status={doc.last_execution_status} />
                            <div className="text-xs text-muted-foreground">
                              {doc.last_executed_at ? formatDateTime(doc.last_executed_at) : 'No execution yet'}
                            </div>
                          </div>
                        ) : (
                          <span className="text-xs text-muted-foreground">-</span>
                        )}
                      </td>
                    )}
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-muted-foreground">
                      {doc.priority || '-'}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-muted-foreground">
                      {doc.reviewer_id ? userMap.get(doc.reviewer_id) || '-' : '-'}
                    </td>
                    <td className="px-6 py-3 whitespace-nowrap text-xs text-muted-foreground">
                      {format(new Date(doc.created_at), 'MMM d, yyyy')}
                    </td>
                    <td className="px-6 py-3 whitespace-nowrap text-xs text-muted-foreground">
                      {format(new Date(doc.updated_at), 'MMM d, yyyy')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

function FilterChip({ label, muted = false }: { label: string; muted?: boolean }) {
  return (
    <span className={`inline-flex items-center rounded-md border px-2 py-1 text-xs ${muted ? 'border-border text-muted-foreground' : 'border-primary/20 bg-primary/10 text-primary'}`}>
      {label}
    </span>
  )
}

function DatePickerField({
  label,
  value,
  emptyLabel,
  onChange,
}: {
  label: string
  value: string
  emptyLabel: string
  onChange: (value: string) => void
}) {
  const displayValue = value ? format(new Date(`${value}T00:00:00`), 'MMM d, yyyy') : emptyLabel

  return (
    <label className="space-y-1">
      <span className="text-xs font-medium uppercase text-muted-foreground">{label}</span>
      <span className="relative flex w-full items-center gap-2 rounded-md border border-input bg-background px-3 py-2 text-sm text-foreground transition-colors hover:bg-accent/40 focus-within:border-ring focus-within:ring-2 focus-within:ring-ring">
        <Calendar className="h-4 w-4 shrink-0 text-muted-foreground" />
        <span className={value ? 'text-foreground' : 'text-muted-foreground'}>{displayValue}</span>
        <input
          type="date"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
          aria-label={label}
        />
      </span>
    </label>
  )
}
