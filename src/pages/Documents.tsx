import { useState, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams, Link, useNavigate, useSearchParams } from 'react-router-dom'
import { docsApi, type DocShell, usersApi } from '../api/client'
import { useProjectByPrefix } from '../hooks/useProjectByPrefix'
import { Plus, Search, BookOpen, ChevronDown, ChevronUp, ArrowUpDown, ArrowRightLeft, ShieldAlert } from 'lucide-react'
import { docUrl, docCreateUrl, normalizeDocTypeParam, type DocType } from '../types/doc'
import { format } from 'date-fns'

const TYPE_BADGES: Record<string, { label: string; color: string }> = {
  REQ: { label: 'Requirement', color: 'bg-amber-500/10 text-amber-700 dark:text-amber-400' },
  SPEC: { label: 'Specification', color: 'bg-indigo-500/10 text-indigo-700 dark:text-indigo-400' },
  TC: { label: 'Test Case', color: 'bg-cyan-500/10 text-cyan-700 dark:text-cyan-400' },
  DES: { label: 'Design', color: 'bg-violet-500/10 text-violet-700 dark:text-violet-400' },
  RSK: { label: 'Risk', color: 'bg-red-500/10 text-red-700 dark:text-red-400' },
  CHG: { label: 'Change', color: 'bg-blue-500/10 text-blue-700 dark:text-blue-400' },
  TCO: { label: 'Test Concept', color: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400' },
  PROT: { label: 'Protocol', color: 'bg-teal-500/10 text-teal-700 dark:text-teal-400' },
  RPT: { label: 'Report', color: 'bg-slate-500/10 text-slate-700 dark:text-slate-400' },
  STD: { label: 'Standard', color: 'bg-orange-500/10 text-orange-700 dark:text-orange-400' },
}

function TypeBadge({ type }: { type: string }) {
  const cfg = TYPE_BADGES[type] || { label: type, color: 'bg-muted text-muted-foreground' }
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

const DOC_TYPES = [
  { code: '', label: 'All Types' },
  { code: 'REQ', label: 'Requirements' },
  { code: 'SPEC', label: 'Specifications' },
  { code: 'TC', label: 'Test Cases' },
  { code: 'DES', label: 'Design' },
  { code: 'RSK', label: 'Risks' },
  { code: 'CHG', label: 'Changes' },
  { code: 'TCO', label: 'Test Concepts' },
  { code: 'PROT', label: 'Protocols' },
  { code: 'RPT', label: 'Reports' },
  { code: 'STD', label: 'Standards' },
]

const STATUS_OPTIONS = [
  { code: '', label: 'All Statuses' },
  { code: 'Draft', label: 'Draft' },
  { code: 'Review', label: 'Review' },
  { code: 'Approved', label: 'Approved' },
  { code: 'Rejected', label: 'Rejected' },
  { code: 'Obsolete', label: 'Obsolete' },
  { code: 'Open', label: 'Open' },
  { code: 'Mitigated', label: 'Mitigated' },
  { code: 'Submitted', label: 'Submitted' },
  { code: 'Implemented', label: 'Implemented' },
]

type SortField = 'updated_at' | 'doc_id' | 'doc_type' | 'status' | 'title'
type SortDir = 'asc' | 'desc'

export default function Documents() {
  const { prefix } = useParams<{ prefix: string }>()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const { data: project } = useProjectByPrefix(prefix)
  const [search, setSearch] = useState('')
  const typeFilter = normalizeDocTypeParam(searchParams.get('type')) || ''
  const statusFilter = searchParams.get('status') || ''
  const [sortField, setSortField] = useState<SortField>('updated_at')
  const [sortDir, setSortDir] = useState<SortDir>('desc')

  const { data: docs, isLoading } = useQuery({
    queryKey: ['all-docs', prefix, typeFilter, statusFilter],
    queryFn: () => docsApi.list(prefix!, {
      type: typeFilter ? [typeFilter] : undefined,
      status: statusFilter || undefined,
      q: undefined,
    }),
    enabled: !!prefix,
  })

  const { data: users } = useQuery({
    queryKey: ['users'],
    queryFn: usersApi.list,
  })

  const userMap = useMemo(() => {
    const m = new Map<number, string>()
    users?.forEach(u => m.set(u.id, u.full_name))
    return m
  }, [users])

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDir('asc')
    }
  }

  const filtered = useMemo(() => {
    let result = docs || []
    if (search) {
      const q = search.toLowerCase()
      result = result.filter(d =>
        d.title.toLowerCase().includes(q) ||
        d.doc_id.toLowerCase().includes(q) ||
        d.doc_type.toLowerCase().includes(q)
      )
    }
    return result
  }, [docs, search])

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      let cmp = 0
      switch (sortField) {
        case 'updated_at':
          cmp = new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime()
          break
        case 'doc_id':
          cmp = a.doc_id.localeCompare(b.doc_id)
          break
        case 'doc_type':
          cmp = a.doc_type.localeCompare(b.doc_type)
          break
        case 'status':
          cmp = a.status.localeCompare(b.status)
          break
        case 'title':
          cmp = a.title.localeCompare(b.title)
          break
      }
      return sortDir === 'asc' ? cmp : -cmp
    })
  }, [filtered, sortField, sortDir])

  const SortHeader = ({ field, children }: { field: SortField; children: React.ReactNode }) => (
    <th
      className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase cursor-pointer select-none hover:text-foreground transition-colors"
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

  const updateUrlFilters = (next: { type?: string; status?: string }) => {
    const params = new URLSearchParams(searchParams)
    const nextType = next.type ?? typeFilter
    const nextStatus = next.status ?? statusFilter

    if (nextType) {
      params.set('type', nextType)
    } else {
      params.delete('type')
    }

    if (nextStatus) {
      params.set('status', nextStatus)
    } else {
      params.delete('status')
    }

    setSearchParams(params, { replace: true })
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex justify-between items-center">
        <div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1">
            <Link to={`/projects/${prefix}`} className="hover:text-primary transition-colors">
              {project?.name || prefix}
            </Link>
            <span>/</span>
            <span className="text-foreground">Documents</span>
          </div>
          <h2 className="text-xl font-bold text-foreground">Documents</h2>
          <p className="text-sm text-muted-foreground mt-0.5">
            {sorted.length} controlled item{sorted.length !== 1 ? 's' : ''}
          </p>
        </div>
        <div className="relative">
          <button
            onClick={() => navigate(docCreateUrl(prefix!, (typeFilter as DocType) || 'REQ'))}
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-all"
          >
            <Plus className="h-4 w-4" />
            New Document
          </button>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search by ID, title, or type..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2.5 bg-card border border-border rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-ring transition-colors shadow-elegant"
          />
        </div>
        <select
          value={typeFilter}
          onChange={(e) => updateUrlFilters({ type: e.target.value })}
          className="px-3 py-2.5 bg-card border border-border rounded-lg text-sm"
        >
          {DOC_TYPES.map((t) => (
            <option key={t.code} value={t.code}>{t.label}</option>
          ))}
        </select>
        <select
          value={statusFilter}
          onChange={(e) => updateUrlFilters({ status: e.target.value })}
          className="px-3 py-2.5 bg-card border border-border rounded-lg text-sm"
        >
          {STATUS_OPTIONS.map((t) => (
            <option key={t.code} value={t.code}>{t.label}</option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <div className="bg-card rounded-lg border border-border shadow-elegant p-8 text-center text-muted-foreground">
          Loading...
        </div>
      ) : !sorted || sorted.length === 0 ? (
        <div className="bg-card rounded-lg border border-border shadow-elegant p-16 text-center">
          <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary/10 to-cyan-500/10 flex items-center justify-center mx-auto mb-5">
            <BookOpen className="h-10 w-10 text-primary/40" />
          </div>
          <h3 className="text-lg font-semibold text-foreground mb-2">
            {search || typeFilter || statusFilter ? 'No documents found' : 'No Documents Yet'}
          </h3>
          <p className="text-sm text-muted-foreground mb-5 max-w-md mx-auto">
            {search || typeFilter || statusFilter
              ? 'Try a different search or filter.'
              : 'Create your first controlled document to get started.'}
          </p>
        </div>
      ) : (
        <div className="bg-card rounded-lg shadow-elegant overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-border">
              <thead className="bg-muted/50">
                <tr>
                  <SortHeader field="doc_id">ID</SortHeader>
                  <SortHeader field="doc_type">Type</SortHeader>
                  <SortHeader field="title">Title</SortHeader>
                  <SortHeader field="status">Status</SortHeader>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Priority</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Links</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Reviewer</th>
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
                    <td className="px-6 py-3 max-w-xs truncate">
                      <Link to={docUrl(prefix!, doc.doc_type as DocType, doc.doc_id)} className="text-foreground hover:text-primary/80 font-medium">
                        {doc.title}
                      </Link>
                    </td>
                    <td className="px-6 py-3 whitespace-nowrap">
                      <StatusBadge status={doc.status} />
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-muted-foreground">
                      {doc.priority || '\u2014'}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="flex items-center gap-2 text-xs">
                        <span className="flex items-center gap-0.5 text-muted-foreground" title="Outgoing links">
                          <ArrowRightLeft className="h-3 w-3" />
                          {doc.outgoing_links}
                        </span>
                        <span className="flex items-center gap-0.5 text-muted-foreground" title="Incoming links">
                          {doc.incoming_links}
                        </span>
                        {doc.suspect_links > 0 && (
                          <span className="flex items-center gap-0.5 text-amber-600 dark:text-amber-400" title="Suspect links">
                            <ShieldAlert className="h-3 w-3" />
                            {doc.suspect_links}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap text-xs text-muted-foreground">
                      {doc.reviewer_id ? (userMap.get(doc.reviewer_id) || '\u2014') : '\u2014'}
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
