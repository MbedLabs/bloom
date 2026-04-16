import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { docsApi, type DocShell } from '../api/client'
import { useProjectByPrefix } from '../hooks/useProjectByPrefix'
import { Plus, Search, BookOpen, ChevronDown } from 'lucide-react'

const TYPE_BADGES: Record<string, { label: string; color: string }> = {
  REQ: { label: 'Requirement', color: 'bg-blue-500/10 text-blue-700 dark:text-blue-400' },
  TC: { label: 'Test Case', color: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400' },
  DES: { label: 'Design', color: 'bg-violet-500/10 text-violet-700 dark:text-violet-400' },
  RSK: { label: 'Risk', color: 'bg-orange-500/10 text-orange-700 dark:text-orange-400' },
  CHG: { label: 'Change', color: 'bg-rose-500/10 text-rose-700 dark:text-rose-400' },
  TCO: { label: 'Test Concept', color: 'bg-cyan-500/10 text-cyan-700 dark:text-cyan-400' },
  DOC: { label: 'Document', color: 'bg-primary/10 text-primary' },
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
  }
  return <span className={`px-2 py-0.5 rounded-md text-[11px] font-semibold ${colors[status] || 'bg-muted text-muted-foreground'}`}>{status}</span>
}

const DOC_TYPES = [
  { code: '', label: 'All Types' },
  { code: 'REQ', label: 'Requirements' },
  { code: 'TC', label: 'Test Cases' },
  { code: 'DES', label: 'Design' },
  { code: 'RSK', label: 'Risks' },
  { code: 'CHG', label: 'Changes' },
  { code: 'TCO', label: 'Test Concepts' },
  { code: 'DOC', label: 'Documents' },
]

const NEW_DOC_TYPES = [
  { code: 'REQ', label: 'Requirement' },
  { code: 'TC', label: 'Test Case' },
  { code: 'DES', label: 'Design' },
  { code: 'RSK', label: 'Risk' },
  { code: 'CHG', label: 'Change Request' },
  { code: 'TCO', label: 'Test Concept' },
  { code: 'DOC', label: 'Document' },
]

export default function Documents() {
  const { prefix } = useParams<{ prefix: string }>()
  const navigate = useNavigate()
  const { data: project } = useProjectByPrefix(prefix)
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [newDocOpen, setNewDocOpen] = useState(false)

  const { data: docs, isLoading } = useQuery({
    queryKey: ['all-docs', prefix, typeFilter],
    queryFn: () => docsApi.list(prefix!, {
      type: typeFilter ? [typeFilter] : undefined,
      q: undefined,
    }),
    enabled: !!prefix,
  })

  const filtered = search
    ? docs?.filter(d =>
        d.title.toLowerCase().includes(search.toLowerCase()) ||
        d.doc_id.toLowerCase().includes(search.toLowerCase()) ||
        d.doc_type.toLowerCase().includes(search.toLowerCase())
      )
    : docs

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
            {filtered?.length || 0} document{(filtered?.length || 0) !== 1 ? 's' : ''}
          </p>
        </div>
        <div className="relative">
          <button
            onClick={() => setNewDocOpen(!newDocOpen)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-all"
          >
            <Plus className="h-4 w-4" />
            New Document
            <ChevronDown className="h-3 w-3" />
          </button>
          {newDocOpen && (
            <div className="absolute right-0 top-full mt-1 w-48 bg-card border border-border rounded-lg shadow-elegant overflow-hidden z-50">
              {NEW_DOC_TYPES.map((t) => (
                <button
                  key={t.code}
                  onClick={() => { setNewDocOpen(false); navigate(`/projects/${prefix}/docs/new?type=${t.code}`) }}
                  className="w-full text-left px-4 py-2.5 text-sm text-foreground hover:bg-accent transition-colors"
                >
                  {t.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            placeholder="Search documents..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-9 pr-4 py-2.5 bg-card border border-border rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:ring-2 focus:ring-ring focus:border-ring transition-colors shadow-elegant"
          />
        </div>
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="px-3 py-2.5 bg-card border border-border rounded-lg text-sm"
        >
          {DOC_TYPES.map((t) => (
            <option key={t.code} value={t.code}>{t.label}</option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <div className="bg-card rounded-lg border border-border shadow-elegant p-8 text-center text-muted-foreground">
          Loading...
        </div>
      ) : !filtered || filtered.length === 0 ? (
        <div className="bg-card rounded-lg border border-border shadow-elegant p-16 text-center">
          <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary/10 to-cyan-500/10 flex items-center justify-center mx-auto mb-5">
            <BookOpen className="h-10 w-10 text-primary/40" />
          </div>
          <h3 className="text-lg font-semibold text-foreground mb-2">
            {search || typeFilter ? 'No documents found' : 'No Documents Yet'}
          </h3>
          <p className="text-sm text-muted-foreground mb-5 max-w-md mx-auto">
            {search || typeFilter
              ? 'Try a different search or filter.'
              : 'Create your first document to get started.'}
          </p>
        </div>
      ) : (
        <div className="bg-card rounded-lg shadow-elegant overflow-hidden">
          <table className="min-w-full divide-y divide-border">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">ID</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Type</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Title</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-muted-foreground uppercase">Updated</th>
              </tr>
            </thead>
            <tbody className="bg-card divide-y divide-border">
              {filtered.map((doc: DocShell) => (
                <tr key={`${doc.doc_type}-${doc.id}`} className="hover:bg-accent/50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <Link to={`/projects/${prefix}/docs/${doc.doc_id}`} className="text-primary font-mono text-sm font-medium">
                      {doc.doc_id}
                    </Link>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <TypeBadge type={doc.doc_type} />
                  </td>
                  <td className="px-6 py-4">
                    <Link to={`/projects/${prefix}/docs/${doc.doc_id}`} className="text-foreground hover:text-primary/80 font-medium">
                      {doc.title}
                    </Link>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <StatusBadge status={doc.status} />
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-xs text-muted-foreground">
                    {new Date(doc.updated_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
